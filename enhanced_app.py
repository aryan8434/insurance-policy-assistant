import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv
import tempfile
from typing import Optional

# Load environment variables
load_dotenv()

# Configure Streamlit page
st.set_page_config(
    page_title="Enhanced Document Q&A System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'document_info' not in st.session_state:
    st.session_state.document_info = None

# API Configuration
API_BASE_URL = "http://localhost:8001"  # Enhanced API runs on port 8001

def upload_document_to_api(file_content, filename):
    """Upload document to the enhanced API"""
    try:
        files = {'file': (filename, file_content, 'application/octet-stream')}
        response = requests.post(f"{API_BASE_URL}/upload-document", files=files)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Upload failed: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error uploading document: {str(e)}")
        return None

def ask_question_to_api(question, session_id):
    """Send question to the enhanced API"""
    try:
        payload = {
            "question": question,
            "session_id": session_id
        }
        response = requests.post(f"{API_BASE_URL}/ask-question", json=payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Question failed: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error asking question: {str(e)}")
        return None

def display_response(response_data):
    """Display API response in a structured format"""
    if not response_data:
        return
    
    # Main answer
    st.markdown("### 📝 Answer")
    st.markdown(f"**{response_data.get('answer', 'No answer provided')}**")
    
    # Confidence score
    confidence = response_data.get('confidence_score', 0)
    st.markdown(f"**Confidence:** {confidence:.1%}")
    
    # Progress bar for confidence
    st.progress(confidence)
    
    # Reason (if provided)
    if response_data.get('reason'):
        st.markdown("### 🔍 Reasoning")
        st.info(response_data['reason'])
    
    # Clause reference
    if response_data.get('clause'):
        st.markdown("### 📋 Source Reference")
        st.code(response_data['clause'])
    
    # Document references
    if response_data.get('document_references'):
        st.markdown("### 📚 Document Sources")
        for ref in response_data['document_references']:
            st.markdown(f"- {ref}")

# Main App Layout
st.title("🔍 Enhanced Document Q&A System")
st.markdown("**Supports:** PDFs, Word Documents (.docx), and Email files (.eml, .txt)")

# Sidebar for document upload
with st.sidebar:
    st.header("📁 Document Upload")
    
    uploaded_file = st.file_uploader(
        "Choose a document",
        type=['pdf', 'docx', 'doc', 'eml', 'msg', 'txt'],
        help="Upload PDF, Word document, or email file"
    )
    
    if uploaded_file is not None:
        if st.button("🚀 Process Document", type="primary"):
            with st.spinner("Processing document..."):
                file_content = uploaded_file.read()
                
                result = upload_document_to_api(file_content, uploaded_file.name)
                
                if result:
                    st.session_state.session_id = result['session_id']
                    st.session_state.document_info = {
                        'filename': uploaded_file.name,
                        'document_type': result['document_type'],
                        'pages_processed': result['pages_processed']
                    }
                    st.success(f"✅ {result['message']}")
                    st.rerun()
    
    # Display current document info
    if st.session_state.document_info:
        st.markdown("---")
        st.markdown("### 📄 Current Document")
        info = st.session_state.document_info
        st.markdown(f"**File:** {info['filename']}")
        st.markdown(f"**Type:** {info['document_type']}")
        st.markdown(f"**Sections:** {info['pages_processed']}")
        
        if st.button("🗑️ Clear Document"):
            st.session_state.session_id = None
            st.session_state.document_info = None
            st.session_state.chat_history = []
            st.rerun()

# Main content area
if st.session_state.session_id:
    st.markdown("---")
    
    # Query examples
    with st.expander("💡 Example Questions", expanded=False):
        st.markdown("""
        **Insurance Policy Questions:**
        - "Can I get surgery coverage for my knee?"
        - "What's the waiting period for pre-existing conditions?"
        - "Am I covered for maternity expenses?"
        - "What are the claim limits?"
        
        **General Document Questions:**
        - "What are the key terms mentioned?"
        - "Any exclusions I should know about?"
        - "What documentation is required?"
        - "Tell me about premium payments"
        """)
    
    # Chat interface
    st.markdown("### 💬 Ask Questions About Your Document")
    
    # Display chat history
    for i, chat in enumerate(st.session_state.chat_history):
        # User question
        with st.chat_message("user"):
            st.markdown(chat['question'])
        
        # Assistant response
        with st.chat_message("assistant"):
            display_response(chat['response'])
    
    # Question input
    user_question = st.chat_input("Ask anything about your document...")
    
    if user_question:
        # Add user question to chat
        with st.chat_message("user"):
            st.markdown(user_question)
        
        # Get response from API
        with st.chat_message("assistant"):
            with st.spinner("Analyzing document..."):
                response = ask_question_to_api(user_question, st.session_state.session_id)
                
                if response:
                    display_response(response)
                    
                    # Add to chat history
                    st.session_state.chat_history.append({
                        'question': user_question,
                        'response': response
                    })
                else:
                    st.error("Failed to get response. Please try again.")

else:
    # Welcome screen
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        ## 🎯 How to Use
        
        1. **📁 Upload** your document using the sidebar
           - PDF files (insurance policies, contracts)
           - Word documents (.docx)
           - Email files (.eml, .txt)
        
        2. **❓ Ask Questions** in plain English
           - "Can I claim for surgery?"
           - "What's the waiting period?"
           - "Am I covered for this condition?"
        
        3. **📋 Get Detailed Answers** with:
           - Clear yes/no responses
           - Exact clause references
           - Confidence scores
           - Source document locations
        
        ### ✨ Features
        - **Smart Query Processing**: Understands vague or incomplete questions
        - **Exact References**: Points to specific clauses and page numbers
        - **Multiple Formats**: Works with PDFs, Word docs, and emails
        - **Audit Trail**: Tracks all sources for compliance
        """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Enhanced Document Q&A System v2.0 | Supports PDFs, Word Documents & Emails"
    "</div>", 
    unsafe_allow_html=True
)
