import requests
import json
import os

# API Base URL (change this to your Railway URL after deployment)
BASE_URL = "http://localhost:8000"

def test_api():
    print("🧪 Testing PDF Q&A API")
    print("=" * 50)
    
    # Test health check
    print("1. Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✅ Health check: {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return
    
    # Test PDF upload (you need to have a PDF file)
    pdf_file_path = input("Enter path to a PDF file to test (or press Enter to skip): ").strip()
    
    if not pdf_file_path or not os.path.exists(pdf_file_path):
        print("⚠️ No valid PDF file provided. Skipping upload test.")
        return
    
    print(f"\n2. Uploading PDF: {pdf_file_path}")
    try:
        with open(pdf_file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{BASE_URL}/upload-pdf", files=files)
        
        if response.status_code == 200:
            upload_result = response.json()
            session_id = upload_result['session_id']
            print(f"✅ Upload successful!")
            print(f"📋 Session ID: {session_id}")
            
            # Test asking a question
            print(f"\n3. Testing question answering...")
            question = input("Enter a question about the PDF: ").strip()
            
            if question:
                question_data = {
                    "question": question,
                    "session_id": session_id
                }
                
                response = requests.post(
                    f"{BASE_URL}/ask-question",
                    json=question_data
                )
                
                if response.status_code == 200:
                    answer = response.json()
                    print(f"✅ Question answered!")
                    print(f"💬 Answer: {answer['answer']}")
                    print(f"📝 Reason: {answer['reason']}")
                    print(f"📄 Clause: {answer['clause']}")
                else:
                    print(f"❌ Question failed: {response.text}")
            else:
                print("⚠️ No question provided.")
                
        else:
            print(f"❌ Upload failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error during upload: {e}")

def demo_javascript_code():
    print("\n" + "=" * 50)
    print("📱 JavaScript Example for Web Developers:")
    print("=" * 50)
    
    js_code = """
// Example usage in JavaScript/Web application
async function uploadPDFAndAsk(pdfFile, question) {
    const API_URL = 'https://your-app-name.up.railway.app';
    
    // 1. Upload PDF
    const formData = new FormData();
    formData.append('file', pdfFile);
    
    const uploadResponse = await fetch(`${API_URL}/upload-pdf`, {
        method: 'POST',
        body: formData
    });
    
    const uploadResult = await uploadResponse.json();
    const sessionId = uploadResult.session_id;
    console.log('PDF uploaded, session:', sessionId);
    
    // 2. Ask question
    const questionResponse = await fetch(`${API_URL}/ask-question`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            question: question,
            session_id: sessionId
        })
    });
    
    const answer = await questionResponse.json();
    console.log('Answer:', answer);
    return answer;
}

// Usage:
// const pdfFile = document.getElementById('pdfInput').files[0];
// uploadPDFAndAsk(pdfFile, 'Is knee surgery covered?');
    """
    print(js_code)

if __name__ == "__main__":
    test_api()
    demo_javascript_code()
    
    print("\n" + "=" * 50)
    print("🎉 API Testing Complete!")
    print("📖 Check API_DOCUMENTATION.md for full documentation")
    print("🚀 Check DEPLOYMENT_GUIDE.md for hosting instructions")
    print("=" * 50)
