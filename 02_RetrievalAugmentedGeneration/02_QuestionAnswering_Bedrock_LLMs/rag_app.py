# Import libraries
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain_postgres import PGVector
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_aws import BedrockEmbeddings
from langchain_aws import ChatBedrock
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.memory import BaseMemory
from langchain.chains import ConversationalRetrievalChain
import streamlit as st
import boto3
from PIL import Image
import os
import traceback
from typing import Dict, Any, List
from htmlTemplates import css

class SimpleChatMemory(BaseMemory):
    """A simple chat memory implementation that doesn't require token counting."""
    chat_history: List = []
    
    def clear(self):
        """Clear memory contents."""
        self.chat_history = []
    
    @property
    def memory_variables(self) -> List[str]:
        """Return memory variables."""
        return ["chat_history"]
    
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Load memory variables."""
        return {"chat_history": self.chat_history}
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """Save context from this conversation to buffer."""
        if inputs.get("question") and outputs.get("answer"):
            self.chat_history.append(HumanMessage(content=inputs["question"]))
            self.chat_history.append(AIMessage(content=outputs["answer"]))

# TODO: This function takes a list of PDF documents as input and extracts the text from them using PdfReader. 
# It concatenates the extracted text and returns it.



# TODO: Given the extracted text, this function splits it into smaller chunks using the RecursiveCharacterTextSplitter module. 
# The chunk size, overlap, and other parameters are configured to optimize processing efficiency.



# TODO: This function takes the text chunks as input and creates a vector store using Bedrock Embeddings (Titan) and pgvector. 
# The vector store stores the vector representations of the text chunks, enabling efficient retrieval based on semantic similarity.



# TODO: In this function, a conversation chain is created using the conversational AI model (Anthropic's Claude v2), vector store (created in the previous function), and conversation memory (ConversationSummaryBufferMemory). 
# This chain allows the Gen AI app to engage in conversational interactions.



# This function is responsible for processing the user's input question and generating a response from the chatbot
def handle_userinput(user_question):
    """Process user input and generate response."""
    if not user_question.strip():
        st.warning("Please enter a question.")
        return
        
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    try:
        with st.spinner("Thinking..."):
            response = st.session_state.conversation({'question': user_question})
            
            # Update chat history
            st.session_state.chat_history = response.get('chat_history', [])
            
            # Display messages with improved formatting
            for message in st.session_state.chat_history:
                if isinstance(message, HumanMessage):
                    st.success(message.content, icon="🤔")
                else:
                    st.markdown(message.content)
                    
    except Exception as e:
        st.error("I encountered an error processing your question. Please try rephrasing it or uploading your documents again.")
        print(f"Error: {str(e)}")
        print(traceback.format_exc())

# Streamlit components
def main():
    # Page configuration
    st.set_page_config(
        page_title="Gen AI Q&A - Powered by Claude 3 Haiku",
        layout="wide",
        page_icon="🤖"
    )
    st.write(css, unsafe_allow_html=True)

    with st.sidebar:
        logo_url = "static/Powered-By_logo-stack_RGB_REV.png"
        st.image(logo_url, width=150)
        
        st.markdown("""
        ### Quick Start Guide
        1. 📄 Upload your PDF files
        2. 🔄 Click 'Process'
        3. 💬 Ask questions about your documents
        """)

    # Initialize session state
    if "conversation" not in st.session_state:
        st.session_state.conversation = get_conversation_chain(get_vectorstore(None))
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None

    # Main content
    st.header("🤖 Generative AI Q&A powered by Claude 3 Haiku")
    st.markdown(
        '<p style="font-size: 16px;">Leveraging '
        '<a href="https://aws.amazon.com/bedrock/">Amazon Bedrock</a> and '
        '<a href="https://github.com/pgvector/pgvector">pgvector</a> '
        'for intelligent document analysis</p>',
        unsafe_allow_html=True
    )

    # Display architecture diagram
    image = Image.open("static/RAG_APG.png")
    st.image(image, caption='Architecture Overview')

    # Input section
    user_question = st.text_input(
        "Ask about your documents:",
        placeholder="What would you like to know?",
        key="question_input"
    )
    
    col1, col2 = st.columns([1, 5])
    with col1:
        go_button = st.button("🔍 Search", type="primary")

    if go_button or user_question:
        handle_userinput(user_question)

    # Sidebar document upload section
    with st.sidebar:
        st.subheader("📁 Document Upload")
        pdf_docs = st.file_uploader(
            "Upload PDFs and click 'Process'",
            type="pdf",
            accept_multiple_files=True
        )
        
        if st.button("🔄 Process", type="primary"):
            with st.spinner("Processing documents..."):
                raw_text = get_pdf_text(pdf_docs)
                if raw_text:
                    text_chunks = get_text_chunks(raw_text)
                    if text_chunks:
                        vectorstore = get_vectorstore(text_chunks)
                        if vectorstore:
                            st.session_state.conversation = get_conversation_chain(vectorstore)
                            st.success('Documents processed successfully!', icon="✅")
                        else:
                            st.error("Error creating vector store")
                    else:
                        st.error("Error creating text chunks")
                else:
                    st.error("Error processing PDFs")

        st.divider()
        
        # Sample questions
        st.markdown("""
        ### 💡 Sample Questions
        1. What are pgvector's capabilities in Aurora PostgreSQL?
        2. Explain Optimized Reads
        3. How do Aurora Optimized Reads improve performance?
        4. What are Bedrock agents?
        5. How does Knowledge Bases handle document chunking?
        6. Which vector databases work with Knowledge Bases?
        """)

if __name__ == '__main__':
    try:
        load_dotenv()
        
        # Initialize AWS Bedrock client
        BEDROCK_CLIENT = boto3.client("bedrock-runtime", 'us-west-2')
        
        # Database connection string
        connection = f"postgresql+psycopg://{os.getenv('PGUSER')}:{os.getenv('PGPASSWORD')}@{os.getenv('PGHOST')}:{os.getenv('PGPORT')}/{os.getenv('PGDATABASE')}"
        
        main()
    except Exception as e:
        st.error(f"Application initialization error: {str(e)}")
