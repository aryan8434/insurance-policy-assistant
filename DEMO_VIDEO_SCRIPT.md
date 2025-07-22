# 🎥 Demo Video Script for Hackathon

## Video Length: 2-3 minutes

### Scene 1: Introduction (30 seconds)
"Hi! I'm presenting Smart Document Assistant - an AI-powered API that lets you upload any PDF and ask intelligent questions about it using Google's Gemini AI."

**Show**: Your project title slide

### Scene 2: Problem Statement (30 seconds)
"Ever struggled to find specific information in long documents? Insurance policies, legal contracts, research papers - they're all time-consuming to analyze manually."

**Show**: Examples of complex PDFs

### Scene 3: Solution Demo (90 seconds)
"Here's how my API solves this:

1. **Upload PDF**: I'll upload an insurance policy document
   **Show**: http://localhost:8000/docs → POST /upload-pdf
   
2. **Get Session ID**: The API processes it and gives me a session ID
   **Show**: Response with session_id
   
3. **Ask Questions**: Now I can ask specific questions
   **Show**: POST /ask-question with sample questions:
   - "Is knee surgery covered for a 46-year-old male?"
   - "What's the waiting period for dental treatment?"
   
4. **Structured Responses**: Get precise answers with reasons and clause references
   **Show**: JSON response with answer, reason, clause

### Scene 4: Technical Highlights (30 seconds)
"Built with FastAPI for the backend, Google Gemini AI for intelligence, FAISS for semantic search, and deployed on Railway for free hosting. The API is production-ready with interactive documentation."

**Show**: 
- Code structure
- Tech stack diagram
- Live deployment URL

### Scene 5: Use Cases & Future (20 seconds)
"This can be used for insurance verification, legal document review, academic research, or any domain requiring document analysis. Future plans include multi-format support and real-time collaboration."

**Show**: Use case examples

## 📝 Recording Tips:
1. **Screen Recording**: Use OBS Studio (free)
2. **Audio**: Clear microphone, no background noise
3. **Resolution**: 1080p minimum
4. **Upload**: YouTube (unlisted) or Loom
5. **Include**: GitHub repo link in description
