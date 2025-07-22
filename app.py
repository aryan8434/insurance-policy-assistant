import streamlit as st
from PyPDF2 import PdfReader
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
import google.generativeai as genai
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAI
from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    st.error("GOOGLE_API_KEY not found in environment variables!")
    st.stop()

genai.configure(api_key=api_key)
# Also set it as environment variable for langchain_google_genai
os.environ["GOOGLE_API_KEY"] = api_key

def get_pdf_text(pdf_docs):
    text = ""
    if pdf_docs is not None:
        if isinstance(pdf_docs, list):
            for pdf in pdf_docs:
                pdf_reader = PdfReader(pdf)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        else:
            # Handle Streamlit file upload (UploadedFile object)
            pdf_reader = PdfReader(pdf_docs)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    return text

def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    return text_splitter.split_text(text)

def get_vector_store(text_chunks):
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")
    # Set session state to indicate processing is complete
    st.session_state.pdf_processed = True
   
def get_conversation_chain():
    prompt_template="""
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
    But if the question is not related to the policy, then have a casual chat, 
    Return a valid JSON response with the following format:
    {{
        "answer": "",
        "reason": "",
        "clause": ""
    }}
    
    Context: {context}
    Question: {question}
    
    Answer:
    """
    model=ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.3,
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    prompt=PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain=load_qa_chain(model, prompt=prompt, chain_type="stuff")
    return chain

def user_input(user_question):
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
        docs = new_db.similarity_search(user_question)
        chain = get_conversation_chain()
        
        # Use the newer invoke method instead of __call__
        response = chain.invoke(
            {"input_documents": docs, "question": user_question}
        )
        
        print(response)
        
        # Extract the response text
        response_text = ""
        if 'output_text' in response:
            response_text = response['output_text']
        else:
            response_text = response.get('text', 'No response generated')
        
        try:
            # Try to parse as JSON
            import json
            json_response = json.loads(response_text)
            
            # Display formatted JSON response
            st.write("**Answer:**", json_response.get("answer", ""))
            st.write("**Reason:**", json_response.get("reason", ""))
            st.write("**Clause:**", json_response.get("clause", ""))
            
        except json.JSONDecodeError:
            # If not valid JSON, display as plain text
            st.write("Reply: ", response_text)
            
    except FileNotFoundError:
        st.error("Please upload and process a PDF first before asking questions.")
        print("Error: FAISS index not found. Please process a PDF first.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        print(f"Error: {e}")
    
def main():
    st.set_page_config("Ask your query")
    st.header("Ask your query")
    
    # Initialize session state
    if 'pdf_processed' not in st.session_state:
        st.session_state.pdf_processed = False
    
    user_question = st.text_input("Enter your question:")
    
    if user_question:
        if st.session_state.pdf_processed:
            user_input(user_question)
        else:
            st.warning("Please upload and process a PDF file first using the sidebar.")
    
    with st.sidebar:
        st.title("Menu")
        pdf_docs = st.file_uploader("Upload your pdf", type="pdf")
        
        # Show current status
        if st.session_state.pdf_processed:
            st.success("✅ PDF processed! You can now ask questions.")
            if st.button("Reset/Upload New PDF"):
                st.session_state.pdf_processed = False
                # Clean up old index files
                import shutil
                if os.path.exists("faiss_index"):
                    shutil.rmtree("faiss_index")
                st.rerun()
        else:
            st.info("📄 Please upload and process a PDF to start asking questions.")
            
        if st.button("Process"):
            if pdf_docs is not None:
                with st.spinner("Processing..."):
                    try:
                        raw_text = get_pdf_text(pdf_docs)
                        if raw_text.strip():
                            text_chunks = get_text_chunks(raw_text)
                            get_vector_store(text_chunks)
                            st.success("Processing complete! You can now ask questions about your PDF.")
                            st.rerun()  # Refresh the app to update the status
                        else:
                            st.error("Could not extract text from the PDF. Please try a different file.")
                    except Exception as e:
                        st.error(f"Error processing PDF: {str(e)}")
            else:
                st.error("Please upload a PDF file first.")
                
if __name__ == "__main__":
    main()
    