"""
Quick API Test Script
Run this to test your PDF Q&A API
"""
import requests
import json

# API base URL
BASE_URL = "http://localhost:8000"

def test_api():
    print("🚀 Testing PDF Q&A API...")
    print("-" * 50)
    
    # Step 1: Check if API is running
    try:
        response = requests.get(f"{BASE_URL}/")
        print("✅ API is running!")
        print(f"Response: {response.json()}")
    except requests.exceptions.ConnectionError:
        print("❌ API is not running. Please start it with: uvicorn api:app --reload")
        return
    
    print("\n" + "-" * 50)
    print("📄 To test with a PDF:")
    print("1. Go to: http://localhost:8000/docs")
    print("2. Click on 'POST /upload-pdf'")
    print("3. Click 'Try it out'")
    print("4. Choose a PDF file")
    print("5. Click 'Execute'")
    print("6. Copy the session_id from the response")
    print("7. Use that session_id to ask questions!")
    
    print("\n" + "-" * 50)
    print("💡 Example question format:")
    print("""
    {
        "session_id": "your-session-id-here",
        "question": "What is this document about?"
    }
    """)
    
    print("\n" + "-" * 50)
    print("🌐 Interactive API Documentation: http://localhost:8000/docs")

if __name__ == "__main__":
    test_api()
