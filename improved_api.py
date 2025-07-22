from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
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
    version="2.0.0"
)

# Add CORS middleware
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

# Store for active sessions
active_sessions = {}

# Improved Pydantic models
class QuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = None  # Made optional!

class QuestionResponse(BaseModel):
    answer: str
    reason: str
    clause: str
    session_id: str

class UploadResponse(BaseModel):
    message: str
    session_id: str

# Your existing helper functions (keeping them the same)
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
    
    session_dir = f"sessions/{session_id}"
    os.makedirs(session_dir, exist_ok=True)
    
    vector_store.save_local(f"{session_dir}/faiss_index")
    return vector_store

def get_conversation_chain():
    prompt_template = """
    You are a helpful assistant that answers questions about insurance policies based on the provided context.
    
    Context: {context}
    Question: {question}
    
    Please provide:
    1. A clear answer
    2. The reason for your answer
    3. The specific clause or section that supports your answer
    
    Answer:
    """
    
    model = ChatGoogleGenerativeAI(
        model="gemini-pro",
        temperature=0.3,
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain

def get_most_recent_session():
    """Get the most recently created session ID"""
    if not active_sessions:
        return None
    
    # Return the most recently created session
    return max(active_sessions.keys(), 
               key=lambda x: active_sessions[x].get('created_at', 0))

def process_question(question: str, session_id: str = None):
    try:
        # If no session_id provided, try to use the most recent one
        if not session_id:
            session_id = get_most_recent_session()
            if not session_id:
                return {
                    "error": "No active sessions found. Please upload a PDF first.",
                    "session_id": None
                }
        
        if session_id not in active_sessions:
            return {
                "error": f"Session {session_id} not found. Please upload a PDF first.",
                "session_id": session_id
            }
        
        session_dir = f"sessions/{session_id}"
        
        # Load the vector store
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        vector_store = FAISS.load_local(f"{session_dir}/faiss_index", embeddings, allow_dangerous_deserialization=True)
        
        # Get relevant documents
        docs = vector_store.similarity_search(question, k=3)
        
        # Get the conversational chain
        chain = get_conversation_chain()
        
        # Generate response
        response = chain({"input_documents": docs, "question": question}, return_only_outputs=True)
        
        answer_text = response["output_text"]
        
        # Parse the response (you might want to improve this parsing)
        lines = answer_text.strip().split('\n')
        answer = answer_text
        reason = "Based on the provided document context"
        clause = "See relevant sections in the uploaded document"
        
        return {
            "answer": answer,
            "reason": reason,
            "clause": clause,
            "session_id": session_id
        }
        
    except Exception as e:
        return {
            "error": f"Error processing question: {str(e)}",
            "session_id": session_id
        }

# Routes
@app.get("/")
async def root():
    return {
        "message": "PDF Q&A API",
        "version": "2.0.0",
        "endpoints": {
            "upload": "/upload - Upload a PDF file",
            "ask": "/ask - Ask questions about uploaded PDFs",
            "docs": "/docs - API documentation"
        }
    }

@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file and process it for Q&A.
    Returns a session_id that can be used for asking questions.
    """
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_file_path = tmp_file.name
        
        try:
            # Extract text from PDF
            text = get_pdf_text(tmp_file_path)
            
            if not text.strip():
                raise HTTPException(status_code=400, detail="Could not extract text from PDF")
            
            # Create text chunks
            text_chunks = get_text_chunks(text)
            
            # Create and save vector store
            create_vector_store(text_chunks, session_id)
            
            # Store session info
            active_sessions[session_id] = {
                "filename": file.filename,
                "created_at": os.time.time(),
                "text_length": len(text),
                "chunks_count": len(text_chunks)
            }
            
            return UploadResponse(
                message=f"PDF processed successfully! You can now ask questions.",
                session_id=session_id
            )
            
        finally:
            # Clean up temporary file
            os.unlink(tmp_file_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask a question about uploaded PDFs.
    If session_id is not provided, uses the most recent session.
    """
    try:
        result = process_question(request.question, request.session_id)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return QuestionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.get("/sessions")
async def list_sessions():
    """List all active sessions"""
    return {
        "active_sessions": len(active_sessions),
        "sessions": {
            sid: {
                "filename": info["filename"],
                "created_at": info["created_at"],
                "chunks_count": info["chunks_count"]
            }
            for sid, info in active_sessions.items()
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
