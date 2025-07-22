from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import uuid
import tempfile
from typing import Dict, Any
from pathlib import Path

# Simple imports that work
try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Simple PDF Q&A API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuestionRequest(BaseModel):
    question: str
    session_id: str

class UploadResponse(BaseModel):
    session_id: str
    message: str

class AnswerResponse(BaseModel):
    answer: str
    reason: str
    clause: str
    session_id: str

# Simple session storage
sessions = {}

# Get environment variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY required")

def extract_text_from_pdf(file_path: str) -> str:
    """Simple PDF text extraction"""
    text = ""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + " "
    except Exception:
        text = "Error reading PDF"
    return text

def create_chunks(text: str):
    """Create text chunks"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    return splitter.split_text(text)

def create_embeddings_store(chunks, session_id: str):
    """Create FAISS store"""
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=GOOGLE_API_KEY
    )
    
    store = FAISS.from_texts(chunks, embeddings)
    
    # Save to session directory
    os.makedirs("sessions", exist_ok=True)
    store.save_local(f"sessions/{session_id}")
    
    return store

def get_answer(question: str, session_id: str):
    """Get answer from stored documents"""
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=GOOGLE_API_KEY
        )
        
        # Load store
        store = FAISS.load_local(
            f"sessions/{session_id}", 
            embeddings, 
            allow_dangerous_deserialization=True
        )
        
        # Get relevant docs
        docs = store.similarity_search(question, k=3)
        
        # Create prompt
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

Answer:"""
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )
        
        # Create chain
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=GOOGLE_API_KEY,
            temperature=0.1
        )
        
        chain = load_qa_chain(llm, prompt=prompt, chain_type="stuff")
        
        # Get response
        response = chain.invoke({
            "input_documents": docs,
            "question": question
        })
        
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
        return {
            "answer": f"Error: {str(e)}",
            "reason": "",
            "clause": "",
            "session_id": session_id
        }

@app.get("/")
async def root():
    return {"message": "Simple PDF Q&A API", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/upload-pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process PDF"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    
    session_id = str(uuid.uuid4())
    
    try:
        # Save uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Extract text
        text = extract_text_from_pdf(temp_path)
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="No text found in PDF")
        
        # Create chunks
        chunks = create_chunks(text)
        
        # Create embeddings
        create_embeddings_store(chunks, session_id)
        
        # Store session
        sessions[session_id] = {"filename": file.filename}
        
        # Cleanup
        os.unlink(temp_path)
        
        return UploadResponse(
            session_id=session_id,
            message="PDF processed successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask-question", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    """Ask question about uploaded PDF"""
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    result = get_answer(request.question, request.session_id)
    return AnswerResponse(**result)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
