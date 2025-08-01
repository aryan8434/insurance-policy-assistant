from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import tempfile
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain.prompts import PromptTemplate

from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="Enhanced Document Q&A API", version="2.0")

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
    document_type: str
    pages_processed: int

class AnswerResponse(BaseModel):
    answer: str
    confidence_score: float
    reason: Optional[str] = None
    clause: Optional[str] = None
    document_references: Optional[List[str]] = None

sessions: Dict[str, Dict[str, Any]] = {}
SESSIONS_DIR = "sessions"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

os.makedirs(SESSIONS_DIR, exist_ok=True)

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is required")

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=GOOGLE_API_KEY
)

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=GOOGLE_API_KEY,
    temperature=0.1
)

def process_pdf_document_safe(file_path: str) -> List[str]:
    """Process PDF document safely with UTF-8 handling"""
    try:
        from pypdf import PdfReader
        
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    extracted = page.extract_text()
                    if extracted:
                        # Ensure UTF-8 compatibility
                        clean_text = extracted.encode('utf-8', errors='ignore').decode('utf-8')
                        text += clean_text + "\n"
                except Exception as e:
                    # Log error but continue processing
                    text += f"\n[Error reading page {page_num + 1}: Unable to extract text]\n"
        
        if not text.strip():
            raise Exception("No readable text found in PDF")
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        chunks = text_splitter.split_text(text)
        print(f"PDF processed successfully. Created {len(chunks)} text chunks.")
        return chunks
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

def process_text_document_safe(file_path: str) -> List[str]:
    """Process text document safely with UTF-8 handling"""
    try:
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        text = ""
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    text = f.read()
                print(f"Text file read successfully with {encoding} encoding.")
                break
            except UnicodeDecodeError:
                continue
        
        if not text.strip():
            raise Exception("No readable text found in file")
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        chunks = text_splitter.split_text(text)
        print(f"Text file processed successfully. Created {len(chunks)} text chunks.")
        return chunks
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing text file: {str(e)}")

def create_vector_store(texts: List[str], session_id: str) -> FAISS:
    """Create FAISS vector store from text chunks"""
    try:
        # Clean texts to ensure UTF-8 compatibility
        clean_texts = []
        for text in texts:
            clean_text = text.encode('utf-8', errors='ignore').decode('utf-8')
            clean_texts.append(clean_text)
        
        vector_store = FAISS.from_texts(clean_texts, embeddings)
        
        vector_store_path = os.path.join(SESSIONS_DIR, f"{session_id}_vectorstore")
        vector_store.save_local(vector_store_path)
        
        print(f"Vector store created successfully for session {session_id}")
        return vector_store
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating vector store: {str(e)}")

def load_vector_store(session_id: str) -> FAISS:
    """Load existing vector store"""
    try:
        vector_store_path = os.path.join(SESSIONS_DIR, f"{session_id}_vectorstore")
        vector_store = FAISS.load_local(vector_store_path, embeddings, allow_dangerous_deserialization=True)
        return vector_store
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading vector store: {str(e)}")

def get_document_answer(question: str, vector_store: FAISS) -> Dict[str, Any]:
    """Get answer from document using LangChain with UTF-8 safe processing"""
    
    prompt_template = """
You are an expert document analyzer. Based on the provided context, answer the question with a short, direct response.

Context: {context}

Question: {question}

Instructions:
1. Provide a very short answer (preferably Yes/No if applicable)
2. If the information is not in the document, say "Information not found in document"
3. Be concise and direct
4. Include the most relevant clause or section if applicable

Answer in JSON format:
{{
    "answer": "Short direct answer here",
    "confidence_score": 0.8,
    "reason": "Brief explanation",
    "clause": "Relevant text from document if applicable"
}}
"""

    PROMPT = PromptTemplate(
        template=prompt_template,
        input_variables=["context", "question"]
    )
    
    try:
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vector_store.as_retriever(search_kwargs={"k": 3}),
            chain_type_kwargs={"prompt": PROMPT},
            return_source_documents=True
        )
        
        result = qa_chain({"query": question})
        
        # Safely handle the response with UTF-8 encoding
        response_text = result["result"]
        clean_response = response_text.encode('utf-8', errors='ignore').decode('utf-8')
        
        try:
            answer_data = json.loads(clean_response)
        except json.JSONDecodeError:
            answer_data = {
                "answer": clean_response[:200],
                "confidence_score": 0.5,
                "reason": "Direct response from model",
                "clause": None
            }
        
        # Clean source documents
        if result["source_documents"]:
            clean_refs = []
            for i, doc in enumerate(result["source_documents"][:2]):
                clean_content = doc.page_content.encode('utf-8', errors='ignore').decode('utf-8')
                clean_refs.append(f"Source {i+1}: ...{clean_content[:100]}...")
            answer_data["document_references"] = clean_refs
        
        print("Question processed successfully.")
        return answer_data
    
    except Exception as e:
        print(f"Error in question processing: {str(e)}")
        return {
            "answer": "Error processing question",
            "confidence_score": 0.0,
            "reason": "System error occurred",
            "clause": None
        }

@app.post("/upload-document", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a document with UTF-8 safe handling"""
    
    session_id = str(uuid.uuid4())
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension == '.pdf':
            texts = process_pdf_document_safe(temp_file_path)
            document_type = "PDF"
        elif file_extension in ['.txt', '.eml']:
            texts = process_text_document_safe(temp_file_path)
            document_type = "Text/Email"
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")
        
        vector_store = create_vector_store(texts, session_id)
        
        sessions[session_id] = {
            "filename": file.filename,
            "document_type": document_type,
            "pages_processed": len(texts),
            "created_at": datetime.now().isoformat(),
            "vector_store_path": os.path.join(SESSIONS_DIR, f"{session_id}_vectorstore")
        }
        
        os.unlink(temp_file_path)
        
        print(f"Document uploaded successfully: {file.filename}")
        
        return UploadResponse(
            session_id=session_id,
            message=f"Document processed successfully. {len(texts)} sections extracted.",
            document_type=document_type,
            pages_processed=len(texts)
        )
    
    except Exception as e:
        if 'temp_file_path' in locals():
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
        print(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.post("/ask-question", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    """Ask a question about the uploaded document with UTF-8 safe handling"""
    
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found. Please upload a document first.")
    
    try:
        vector_store = load_vector_store(request.session_id)
        
        answer_data = get_document_answer(request.question, vector_store)
        
        return AnswerResponse(**answer_data)
    
    except Exception as e:
        print(f"Error processing question: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.get("/")
async def root():
    return {
        "message": "Enhanced Document Q&A API v2.0",
        "status": "running",
        "supported_formats": ["PDF", "TXT", "EML"],
        "endpoints": ["/upload-document", "/ask-question"]
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
