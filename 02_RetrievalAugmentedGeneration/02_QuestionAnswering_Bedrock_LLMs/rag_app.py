# Import libraries
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain_postgres import PGVector
from langchain_postgres.vectorstores import PGVector
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
import json
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
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    try:
        response = st.session_state.conversation({'question': user_question})
        
        # Update chat history
        st.session_state.chat_history = response.get('chat_history', [])
        
        # Display messages
        for message in st.session_state.chat_history:
            if isinstance(message, HumanMessage):
                st.success(message.content, icon="🤔")
            else:
                st.write(message.content)
                
    except Exception as e:
        st.write("Sorry, I encountered an error processing your question. Could you try rephrasing it?")
        print(f"Error: {str(e)}")
        print(traceback.format_exc())

# Streamlit components
def main():
    # Set the page configuration for the Streamlit application, including the page title and icon.
    st.set_page_config(page_title="Generative AI Q&A with Amazon Bedrock, Aurora PostgreSQL and pgvector",
                       layout="wide",
                       page_icon=":books::parrot:")
    st.write(css, unsafe_allow_html=True)

    logo_url = "static/Powered-By_logo-stack_RGB_REV.png"
    st.sidebar.image(logo_url, width=150)

    st.sidebar.markdown(
    """
    ### Instructions:
    1. Browse and upload PDF files
    2. Click Process
    3. Type your question in the search bar to get more insights
    """
    )
    
    # Check if the conversation and chat history are not present in the session state and initialize them to None.
    if "conversation" not in st.session_state:
        st.session_state.conversation = get_conversation_chain(get_vectorstore(None))
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None
    
    # A header with the text appears at the top of the Streamlit application.
    st.header("Generative AI Q&A with Amazon Bedrock, Aurora PostgreSQL and pgvector :books::parrot:")
    subheader = '<p style="font-family:Calibri (Body); color:Grey; font-size: 16px;">Leverage Foundational Models from <a href="https://aws.amazon.com/bedrock/">Amazon Bedrock</a> and <a href="https://github.com/pgvector/pgvector">pgvector</a> as Vector Engine</p>'
    
    # Write the CSS style to the Streamlit application, allowing you to customize the appearance.
    st.markdown(subheader, unsafe_allow_html=True)
    image = Image.open("static/RAG_APG.png")
    st.image(image, caption='Generative AI Q&A with Amazon Bedrock, Aurora PostgreSQL and pgvector')
    
    # Create a text input box where you can ask questions about your documents.
    user_question = st.text_input("Ask a question about your documents:", placeholder="What is Amazon Aurora?")
    
    # Define a Go button for user action
    go_button = st.button("Submit", type="secondary")
    
    # If the go button is pressed or the user enters a question, it calls the handle_userinput() function to process the user's input.
    if go_button or user_question:
        with st.spinner("Processing..."):
            handle_userinput(user_question)

    with st.sidebar:
        st.subheader("Your documents")
        pdf_docs = st.file_uploader(
            "Upload your PDFs here and click on 'Process'", type="pdf", accept_multiple_files=True)
        
        # If the user clicks the "Process" button, the following code is executed:
        # i. raw_text = get_pdf_text(pdf_docs): retrieves the text content from the uploaded PDF documents.
        # ii. text_chunks = get_text_chunks(raw_text): splits the text content into smaller chunks for efficient processing.
        # iii. vectorstore = get_vectorstore(text_chunks): creates a vector store that stores the vector representations of the text chunks.
        if st.button("Process"):
            with st.spinner("Processing"):
                # get pdf text
                raw_text = get_pdf_text(pdf_docs)

                # get the text chunks
                text_chunks = get_text_chunks(raw_text)

                # create vector store
                vectorstore = get_vectorstore(text_chunks)

                # create conversation chain
                st.session_state.conversation = get_conversation_chain(vectorstore)

                st.success('PDF uploaded successfully!', icon="✅")
    
    with st.sidebar:
        st.divider()

    st.sidebar.markdown(
    """
    ### Sample questions to get started:
    1. What capabilities does pgvector enable for Aurora PostgreSQL?
    2. What is Optimized Reads?
    3. How do Amazon Aurora Optimized Reads for Aurora PostgreSQL improve query performance?
    4. What are agents for Amazon Bedrock?
    5. How does Knowledge Bases for Amazon Bedrock chunk the documents before converting those chunks to embeddings?
    6. Which vector databases are supported by Knowledge Bases for Amazon Bedrock?
    """
)

if __name__ == '__main__':
    # This function loads the environment variables from a .env file.
    load_dotenv()
    
    # Define the Bedrock client.
    BEDROCK_CLIENT = boto3.client("bedrock-runtime", 'us-west-2')
    
    # Create the connection string for pgvector. Ref: https://github.com/langchain-ai/langchain-postgres/blob/main/examples/vectorstore.ipynb
    db_user = os.getenv('PGUSER')
    db_password = os.getenv('PGPASSWORD')
    db_host = os.getenv('PGHOST')
    db_port = os.getenv('PGPORT')
    db_name = os.getenv('PGDATABASE')
    connection = f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    main()
