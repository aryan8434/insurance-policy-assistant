# API Usage Guide

## Your PDF Q&A API Endpoints

### Base URL: `http://localhost:8000`

---

## 1. **Root Endpoint**
**GET /** 
- **Purpose**: Check if API is running
- **Response**: Welcome message

**Example:**
```bash
curl http://localhost:8000/
```

---

## 2. **Upload PDF**
**POST /upload-pdf**
- **Purpose**: Upload a PDF file for processing
- **Input**: PDF file (multipart/form-data)
- **Output**: Session ID for asking questions

**Example Response:**
```json
{
  "message": "PDF uploaded and processed successfully",
  "session_id": "abc123-def456-ghi789",
  "pages_processed": 25
}
```

---

## 3. **Ask Questions**
**POST /ask-question**
- **Purpose**: Ask questions about uploaded PDF
- **Input**: JSON with session_id and question
- **Output**: Structured answer with reason and clause

**Request Format:**
```json
{
  "session_id": "abc123-def456-ghi789",
  "question": "Is dental treatment covered?"
}
```

**Response Format:**
```json
{
  "answer": "Yes, dental treatment is covered",
  "reason": "",
  "clause": "Refer to page 15 and line no 23"
}
```

---

## Sample Questions for Insurance PDF:
- "Is knee surgery covered for a 46-year-old male?"
- "What is the waiting period for dental treatment?"
- "Are pre-existing conditions covered?"
- "What is the claim process?"

---

## Interactive Testing:
Visit: http://localhost:8000/docs for live testing interface!
