from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import uuid
import shutil
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import tempfile
from typing import Dict, Any
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="PDF Q&A API",
    description="Upload PDFs and ask questions about their content",
    version="1.0.0"
)

# Add CORS middleware to allow web requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Google AI
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise Exception("GOOGLE_API_KEY not found in environment variables!")

genai.configure(api_key=api_key)
os.environ["GOOGLE_API_KEY"] = api_key

# Store for active sessions (in production, use a database)
active_sessions = {}

# Pydantic models for request/response
class QuestionRequest(BaseModel):
    question: str
    session_id: str

class QuestionResponse(BaseModel):
    answer: str
    reason: str
    clause: str
    session_id: str

class UploadResponse(BaseModel):
    message: str
    session_id: str

# Helper functions (adapted from your original code)
def get_pdf_text(pdf_file_path: str) -> str:
    text = ""
    with open(pdf_file_path, 'rb') as file:
        pdf_reader = PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
    return text

def get_text_chunks(text: str):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    return text_splitter.split_text(text)

def create_vector_store(text_chunks, session_id: str):
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    
    # Create session-specific directory
    session_dir = f"sessions/{session_id}"
    os.makedirs(session_dir, exist_ok=True)
    
    vector_store.save_local(f"{session_dir}/faiss_index")
    return vector_store

def get_conversation_chain():
    prompt_template = """
    You are a helpful assistant that answers questions about insurance policies based on the provided context.
    
    Sample Query: "46M, knee surgery, Pune, 3-month policy"
    
    Sample Response: 
    {{
        "answer": "Yes, knee surgery is covered under the policy.",
        "reason": "",
        "clause": "Refer to page 53 and line no 40."
    }}
    
    Please answer in the exact JSON format shown above based on the PDF text and the question asked. 
    Also consider the time frame and whether any waiting periods have been completed.
    If there is no waiting period, you can directly answer the question. yes or no 
    Also keep answers very short  
    give reason only if it is rejected or not covered by stating 
    "reason": "4-month waiting period not completed" or "It is not covered under the policy"
    Also give clauses like "Refer to page 53 and line no 40." everytime 
    Return a valid JSON response with the following format:
    {{
        "answer": "",
        "reason": "",
        "clause": ""
    }}
    
    Context: {context}
    Question: {question}
    
    Answer:
    """
    model = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.3,
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, prompt=prompt, chain_type="stuff")
    return chain

def process_question(question: str, session_id: str):
    try:
        # Check if session exists
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found. Please upload a PDF first.")
        
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        
        # Load the session-specific FAISS index
        session_dir = f"sessions/{session_id}"
        new_db = FAISS.load_local(f"{session_dir}/faiss_index", embeddings, allow_dangerous_deserialization=True)
        
        # Search for relevant documents
        docs = new_db.similarity_search(question)
        
        # Get response from conversation chain
        chain = get_conversation_chain()
        response = chain.invoke(
            {"input_documents": docs, "question": question}
        )
        
        # Extract response text
        response_text = ""
        if 'output_text' in response:
            response_text = response['output_text']
        else:
            response_text = response.get('text', 'No response generated')
        
        # Parse JSON response
        try:
            json_response = json.loads(response_text)
            return {
                "answer": json_response.get("answer", ""),
                "reason": json_response.get("reason", ""),
                "clause": json_response.get("clause", ""),
                "session_id": session_id
            }
        except json.JSONDecodeError:
            return {
                "answer": response_text,
                "reason": "",
                "clause": "",
                "session_id": session_id
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

# API Endpoints
@app.get("/")
async def root():
    return {
        "message": "PDF Q&A API",
        "endpoints": {
            "upload": "POST /upload-pdf",
            "ask": "POST /ask-question",
            "health": "GET /health"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running"}

@app.post("/upload-pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file and process it for question answering.
    Returns a session_id that should be used for asking questions.
    """
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Create temporary file to save uploaded PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Extract text from PDF
            raw_text = get_pdf_text(temp_file_path)
            
            if not raw_text.strip():
                raise HTTPException(status_code=400, detail="Could not extract text from PDF")
            
            # Create text chunks
            text_chunks = get_text_chunks(raw_text)
            
            # Create and save vector store
            create_vector_store(text_chunks, session_id)
            
            # Store session info
            active_sessions[session_id] = {
                "filename": file.filename,
                "created_at": "now",  # In production, use proper timestamp
                "processed": True
            }
            
            return UploadResponse(
                message=f"PDF '{file.filename}' processed successfully",
                session_id=session_id
            )
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/ask-question", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask a question about the uploaded PDF content.
    Requires a valid session_id from the upload-pdf endpoint.
    """
    try:
        result = process_question(request.question, request.session_id)
        return QuestionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """
    Get information about a specific session.
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "info": active_sessions[session_id]
    }

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session and clean up associated files.
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Clean up session files
        session_dir = f"sessions/{session_id}"
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
        
        # Remove from active sessions
        del active_sessions[session_id]
        
        return {"message": f"Session {session_id} deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
