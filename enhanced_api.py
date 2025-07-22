from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import uuid
import shutil
import email
import re
from typing import List, Dict, Any, Optional
from PyPDF2 import PdfReader
from docx import Document
import tempfile
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Enhanced Document Q&A API",
    description="Upload PDFs, Word files, or emails and ask questions about their content",
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

# Pydantic models
class QuestionRequest(BaseModel):
    question: str
    session_id: str

class QuestionResponse(BaseModel):
    answer: str
    reason: str
    clause: str
    confidence_score: float
    document_references: List[str]
    session_id: str

class UploadResponse(BaseModel):
    message: str
    session_id: str
    document_type: str
    pages_processed: int

class DocumentChunk(BaseModel):
    content: str
    source: str
    page_number: Optional[int] = None
    paragraph_number: Optional[int] = None

# Enhanced document processing functions
def extract_pdf_text(file_path: str) -> List[DocumentChunk]:
    """Extract text from PDF with page tracking"""
    chunks = []
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            for page_num, page in enumerate(pdf_reader.pages, 1):
                text = page.extract_text()
                if text.strip():
                    chunks.append(DocumentChunk(
                        content=text,
                        source=f"PDF_Page_{page_num}",
                        page_number=page_num
                    ))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading PDF: {str(e)}")
    return chunks

def extract_docx_text(file_path: str) -> List[DocumentChunk]:
    """Extract text from Word document with paragraph tracking"""
    chunks = []
    try:
        doc = Document(file_path)
        for para_num, paragraph in enumerate(doc.paragraphs, 1):
            text = paragraph.text.strip()
            if text:
                chunks.append(DocumentChunk(
                    content=text,
                    source=f"DOCX_Paragraph_{para_num}",
                    paragraph_number=para_num
                ))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading Word document: {str(e)}")
    return chunks

def extract_email_text(file_path: str) -> List[DocumentChunk]:
    """Extract text from email file"""
    chunks = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            
        # Try to parse as email
        try:
            msg = email.message_from_string(content)
            
            # Extract headers
            headers = f"From: {msg.get('From', 'Unknown')}\n"
            headers += f"To: {msg.get('To', 'Unknown')}\n"
            headers += f"Subject: {msg.get('Subject', 'No Subject')}\n"
            headers += f"Date: {msg.get('Date', 'Unknown')}\n\n"
            
            chunks.append(DocumentChunk(
                content=headers,
                source="Email_Headers",
                paragraph_number=1
            ))
            
            # Extract body
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True)
                        if body:
                            chunks.append(DocumentChunk(
                                content=body.decode('utf-8', errors='ignore'),
                                source="Email_Body",
                                paragraph_number=2
                            ))
            else:
                body = msg.get_payload(decode=True)
                if body:
                    chunks.append(DocumentChunk(
                        content=body.decode('utf-8', errors='ignore'),
                        source="Email_Body",
                        paragraph_number=2
                    ))
        except:
            # If email parsing fails, treat as plain text
            chunks.append(DocumentChunk(
                content=content,
                source="Text_File",
                paragraph_number=1
            ))
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading email/text file: {str(e)}")
    return chunks

def process_document(file_path: str, filename: str) -> tuple[List[DocumentChunk], str]:
    """Process document based on file extension"""
    file_ext = filename.lower().split('.')[-1]
    
    if file_ext == 'pdf':
        chunks = extract_pdf_text(file_path)
        doc_type = "PDF"
    elif file_ext in ['docx', 'doc']:
        chunks = extract_docx_text(file_path)
        doc_type = "Word Document"
    elif file_ext in ['eml', 'msg', 'txt']:
        chunks = extract_email_text(file_path)
        doc_type = "Email/Text"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}")
    
    if not chunks:
        raise HTTPException(status_code=400, detail="No text content found in document")
    
    return chunks, doc_type

def create_enhanced_text_chunks(document_chunks: List[DocumentChunk]) -> List[str]:
    """Create text chunks with metadata preservation"""
    enhanced_chunks = []
    
    for chunk in document_chunks:
        # Add metadata to chunk for better tracking
        metadata_prefix = f"[Source: {chunk.source}"
        if chunk.page_number:
            metadata_prefix += f", Page: {chunk.page_number}"
        if chunk.paragraph_number:
            metadata_prefix += f", Paragraph: {chunk.paragraph_number}"
        metadata_prefix += "]\n\n"
        
        enhanced_content = metadata_prefix + chunk.content
        
        # Split long chunks while preserving metadata
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=8000, 
            chunk_overlap=1000,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        sub_chunks = text_splitter.split_text(enhanced_content)
        enhanced_chunks.extend(sub_chunks)
    
    return enhanced_chunks

def create_vector_store(text_chunks: List[str], session_id: str):
    """Create FAISS vector store with enhanced embeddings"""
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    
    # Create session directory
    session_dir = f"sessions/{session_id}"
    os.makedirs(session_dir, exist_ok=True)
    
    vector_store.save_local(f"{session_dir}/faiss_index")
    return vector_store

def get_enhanced_conversation_chain():
    """Enhanced conversation chain with concise responses"""
    prompt_template = """
    You are a helpful assistant that answers questions about insurance policies based on the provided context.
    
    Sample Query: "46M, knee surgery, Pune, 3-month policy"
    
    Sample Response: 
    {{
        "answer": "Yes, knee surgery is covered under the policy.",
        "reason": "",
        "clause": "Refer to page 53 and line no 40.",
        "confidence_score": 0.0,
        "document_references": ["PDF_Page_53"]
    }}
    
    INSTRUCTIONS:
    1. Keep answers VERY SHORT - just "Yes" or "No" or brief specific answer
    2. Give reason ONLY if it is rejected or not covered
    3. Always provide clause references with page numbers
    4. Handle vague queries by interpreting them correctly
    5. Work with PDFs, Word docs, and email files
    
    ANSWER RULES:
    - Answer format: "Yes" / "No" / "Partial coverage" / specific amount
    - Reason only for rejections: "4-month waiting period not completed" or "It is not covered under the policy"
    - Always give clauses like "Refer to page 53 and line no 40" or "See paragraph 5 of email"
    - Confidence score between 0.0 to 1.0
    
    Return a valid JSON response with the following format:
    {{
        "answer": "",
        "reason": "",
        "clause": "",
        "confidence_score": 0.8,
        "document_references": []
    }}
    
    Context: {context}
    Question: {question}
    
    Answer:
    """
    
    model = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.2,  # Lower temperature for more consistent responses
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, prompt=prompt, chain_type="stuff")
    return chain

def process_enhanced_question(question: str, session_id: str) -> Dict[str, Any]:
    """Enhanced question processing with better context retrieval"""
    try:
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found. Please upload a document first.")
        
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        
        # Load vector store
        session_dir = f"sessions/{session_id}"
        vector_store = FAISS.load_local(f"{session_dir}/faiss_index", embeddings, allow_dangerous_deserialization=True)
        
        # Enhanced similarity search with more results
        docs = vector_store.similarity_search(question, k=6)  # Get more context
        
        # Get conversation chain and process
        chain = get_enhanced_conversation_chain()
        response = chain.invoke({"input_documents": docs, "question": question})
        
        # Extract response text
        response_text = response.get('output_text', response.get('text', 'No response generated'))
        
        # Parse JSON response
        try:
            json_response = json.loads(response_text)
            
            # Validate and enhance response
            result = {
                "answer": json_response.get("answer", ""),
                "reason": json_response.get("reason", ""),
                "clause": json_response.get("clause", ""),
                "confidence_score": float(json_response.get("confidence_score", 0.8)),
                "document_references": json_response.get("document_references", []),
                "session_id": session_id
            }
            
            return result
            
        except json.JSONDecodeError:
            # Fallback response structure
            return {
                "answer": response_text,
                "reason": "System could not parse structured response",
                "clause": "Please refer to uploaded documents",
                "confidence_score": 0.5,
                "document_references": ["Unknown"],
                "session_id": session_id
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

# API Endpoints
@app.get("/")
async def root():
    return {
        "message": "Enhanced Document Q&A API v2.0",
        "supported_formats": ["PDF", "DOCX", "DOC", "EML", "MSG", "TXT"],
        "capabilities": [
            "Multi-format document processing",
            "Vague query interpretation", 
            "Exact clause referencing",
            "Confidence scoring",
            "Audit trail support"
        ],
        "endpoints": {
            "upload": "POST /upload-document",
            "ask": "POST /ask-question",
            "health": "GET /health"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Enhanced API is running"}

@app.post("/upload-document", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process documents (PDF, Word, Email/Text files)
    Returns session_id for subsequent queries
    """
    try:
        # Validate file type
        allowed_extensions = ['pdf', 'docx', 'doc', 'eml', 'msg', 'txt']
        file_ext = file.filename.lower().split('.')[-1]
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Process document based on type
            document_chunks, doc_type = process_document(temp_file_path, file.filename)
            
            # Create enhanced text chunks
            text_chunks = create_enhanced_text_chunks(document_chunks)
            
            # Create vector store
            create_vector_store(text_chunks, session_id)
            
            # Store session info
            active_sessions[session_id] = {
                "filename": file.filename,
                "document_type": doc_type,
                "chunks_count": len(document_chunks),
                "processed_chunks": len(text_chunks),
                "created_at": "now",
                "processed": True
            }
            
            return UploadResponse(
                message=f"{doc_type} '{file.filename}' processed successfully",
                session_id=session_id,
                document_type=doc_type,
                pages_processed=len(document_chunks)
            )
            
        finally:
            # Clean up temp file
            os.unlink(temp_file_path)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.post("/ask-question", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask questions about uploaded documents
    Handles vague queries and provides detailed explanations
    """
    try:
        result = process_enhanced_question(request.question, request.session_id)
        return QuestionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """Get detailed session information"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "info": active_sessions[session_id]
    }

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete session and cleanup files"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        session_dir = f"sessions/{session_id}"
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
        
        del active_sessions[session_id]
        return {"message": f"Session {session_id} deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
