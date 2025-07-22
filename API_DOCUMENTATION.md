# PDF Q&A API

A REST API that allows users to upload PDF files and ask questions about their content using Google's Gemini AI.

## 🚀 Live API

Your API is running at: `http://localhost:8000`

**Interactive Documentation**: http://localhost:8000/docs

## 📋 API Endpoints

### 1. Upload PDF
```http
POST /upload-pdf
Content-Type: multipart/form-data
```

**Body**: PDF file (form-data with key "file")

**Response**:
```json
{
  "message": "PDF 'filename.pdf' processed successfully",
  "session_id": "uuid-string"
}
```

### 2. Ask Question
```http
POST /ask-question
Content-Type: application/json
```

**Body**:
```json
{
  "question": "Is knee surgery covered?",
  "session_id": "uuid-from-upload"
}
```

**Response**:
```json
{
  "answer": "Yes, knee surgery is covered under the policy.",
  "reason": "",
  "clause": "Refer to page 53 and line no 40.",
  "session_id": "uuid-string"
}
```

### 3. Health Check
```http
GET /health
```

## 🧪 Testing with cURL

### Upload PDF:
```bash
curl -X POST "http://localhost:8000/upload-pdf" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your-file.pdf"
```

### Ask Question:
```bash
curl -X POST "http://localhost:8000/ask-question" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Is knee surgery covered?",
    "session_id": "your-session-id-here"
  }'
```

## 🌐 For Other Developers

### Python Example:
```python
import requests

# Upload PDF
with open('policy.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/upload-pdf',
        files={'file': f}
    )
    session_id = response.json()['session_id']

# Ask question
question_response = requests.post(
    'http://localhost:8000/ask-question',
    json={
        'question': 'Is knee surgery covered?',
        'session_id': session_id
    }
)
print(question_response.json())
```

### JavaScript Example:
```javascript
// Upload PDF
const formData = new FormData();
formData.append('file', pdfFile);

const uploadResponse = await fetch('http://localhost:8000/upload-pdf', {
    method: 'POST',
    body: formData
});
const { session_id } = await uploadResponse.json();

// Ask question
const questionResponse = await fetch('http://localhost:8000/ask-question', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        question: 'Is knee surgery covered?',
        session_id: session_id
    })
});
const answer = await questionResponse.json();
console.log(answer);
```

## 🔒 Environment Variables

Create a `.env` file:
```
GOOGLE_API_KEY=your_google_api_key_here
```

## 🚀 Deployment on Railway (Free)

1. **Create Railway Account**: Go to [railway.app](https://railway.app)
2. **Connect GitHub**: Link your repository
3. **Deploy**: Railway will auto-detect and deploy
4. **Add Environment Variables**: Add your `GOOGLE_API_KEY` in Railway dashboard

## 📝 Features

- ✅ Upload PDF files
- ✅ Extract and process text
- ✅ Create vector embeddings
- ✅ Ask questions in natural language
- ✅ Get structured JSON responses
- ✅ Session management
- ✅ CORS enabled for web apps
- ✅ Interactive API documentation

## 🔧 Response Format

All question responses follow this structure:
```json
{
  "answer": "Yes/No with brief explanation",
  "reason": "Detailed reason if rejected/not covered", 
  "clause": "Reference to specific policy section",
  "session_id": "unique-session-identifier"
}
```
