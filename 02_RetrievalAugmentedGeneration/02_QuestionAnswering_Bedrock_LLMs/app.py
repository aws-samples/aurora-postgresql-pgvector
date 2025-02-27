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
import json
import time
import logging
import traceback
from typing import Dict, Any, List, Optional
from htmlTemplates import css

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
DEFAULT_REGION = "us-east-1"
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_RETRIEVAL_K = 3
TITLE = "Generative AI Q&A powered by Amazon Bedrock"
ICON = "🤖"

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

def get_pdf_text(pdf_docs) -> Optional[str]:
    """
    Extract text from uploaded PDF documents.
    
    Args:
        pdf_docs: List of uploaded PDF files
        
    Returns:
        Extracted text or None if processing fails
    """
    if not pdf_docs:
        return None
        
    text = ""
    try:
        for pdf in pdf_docs:
            with st.spinner(f"Processing {pdf.name}..."):
                pdf_reader = PdfReader(pdf)
                for page in pdf_reader.pages:
                    text += page.extract_text()
        return text
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        st.error(f"Error processing PDF: {str(e)}")
        return None

def get_text_chunks(text: Optional[str]) -> Optional[List[str]]:
    """
    Split text into smaller chunks for processing.
    
    Args:
        text: Text to be split into chunks
        
    Returns:
        List of text chunks or None if processing fails
    """
    if not text:
        return None
        
    try:
        # Optimized chunk size for LLMs
        text_splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ".", " "],
            chunk_size=DEFAULT_CHUNK_SIZE,
            chunk_overlap=DEFAULT_CHUNK_OVERLAP,
            length_function=len
        )
        chunks = text_splitter.split_text(text)
        logger.info(f"Split text into {len(chunks)} chunks")
        return chunks
    except Exception as e:
        logger.error(f"Error creating text chunks: {str(e)}")
        st.error(f"Error creating text chunks: {str(e)}")
        return None

def get_vectorstore(text_chunks: Optional[List[str]]):
    """
    Create vector store using Bedrock Embeddings and pgvector.
    
    Args:
        text_chunks: List of text chunks to be stored in vector database
        
    Returns:
        Vector store instance or None if creation fails
    """
    try:
        embeddings = BedrockEmbeddings(
            model_id="amazon.titan-embed-text-v2:0",
            client=BEDROCK_CLIENT,
            region_name=os.getenv('AWS_REGION', DEFAULT_REGION)
        )
        
        if text_chunks is None:
            return PGVector(
                connection=connection,
                embeddings=embeddings,
                use_jsonb=True
            )
            
        chunks_with_metadata = []
        for i, chunk in enumerate(text_chunks):
            chunks_with_metadata.append((chunk, {"chunk_id": i}))
            
        return PGVector.from_texts(
            texts=[text for text, _ in chunks_with_metadata],
            embedding=embeddings,
            metadatas=[metadata for _, metadata in chunks_with_metadata],
            connection=connection
        )
    except Exception as e:
        logger.error(f"Error creating vector store: {str(e)}")
        st.error(f"Error creating vector store: {str(e)}")
        return None

# Custom handler for Amazon Nova models
class NovaLLM:
    """Handler for Amazon Nova models using the converse API"""
    
    def __init__(self, model_id: str, client, max_tokens: int = 1000):
        self.model_id = model_id
        self.client = client
        self.max_tokens = max_tokens
    
    def invoke(self, prompt: str) -> str:
        """
        Invoke the Nova model using the converse API
        
        Args:
            prompt: The prompt text to send to the model
            
        Returns:
            Generated text response from the model
        """
        try:
            # Format messages for Nova models using converse method
            messages = [
                {"role": "user", "content": [{"text": prompt}]}
            ]
            
            # Use the converse method
            response = self.client.converse(
                modelId=self.model_id,
                messages=messages,
                inferenceConfig={
                    "maxTokens": self.max_tokens
                }
            )
            
            # Extract text from response following the exact path
            return response["output"]["message"]["content"][0]["text"]
        except Exception as e:
            logger.error(f"Error invoking Nova model: {str(e)}")
            return f"Error generating response: {str(e)}"

def get_conversation_chain(vectorstore, model_selection: str):
    """
    Create conversation chain using selected model.
    
    Args:
        vectorstore: Vector store for document retrieval
        model_selection: Selected model name
        
    Returns:
        Conversation chain function or None if creation fails
    """
    if not vectorstore:
        logger.error("Cannot create conversation chain: Vector store is None")
        return None
        
    try:
        # Model configurations based on selection
        model_config = {
            "Anthropic Claude 3 Sonnet": {
                "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
                "use_claude": True,
                "model_kwargs": {
                    "temperature": 0.5,
                    "max_tokens": 8192,
                    "top_p": 0.9,
                    "top_k": 250
                }
            },
            "Amazon Nova Micro": {
                "model_id": "us.amazon.nova-micro-v1:0",
                "use_claude": False,
                "max_tokens": 1000
            },
            "Amazon Nova Lite": {
                "model_id": "us.amazon.nova-lite-v1:0",
                "use_claude": False,
                "max_tokens": 1000
            },
            "Amazon Nova Pro": {
                "model_id": "us.amazon.nova-pro-v1:0",
                "use_claude": False,
                "max_tokens": 1000
            }
        }
        
        if model_selection not in model_config:
            logger.error(f"Unknown model selection: {model_selection}")
            st.error(f"Unknown model: {model_selection}")
            return None
            
        selected_config = model_config[model_selection]
        
        # Shared prompt template for all models
        prompt_template = """Human: You are a helpful AI assistant. Your role is to provide clear, concise answers using only the information from the context below.

        Guidelines for your responses:
        - Use English and maintain a professional yet conversational tone
        - Start responses with "Based on the provided context: "
        - Answer questions directly using only relevant details from the context
        - If the context doesn't contain the answer, say "I apologize, but I don't find information about that in the provided context. Could you rephrase your question?"
        - Use bullet points for clarity when appropriate
        - Provide a brief summary at the end
        
        Context: {context}

        Question: {question}
        
        Assistant: """
        
        PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )
        
        memory = SimpleChatMemory()
        
        # For Claude model
        if selected_config["use_claude"]:
            llm = ChatBedrock(
                model_id=selected_config["model_id"],
                client=BEDROCK_CLIENT,
                model_kwargs=selected_config["model_kwargs"]
            )
            
            conversation_chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                chain_type="stuff",
                return_source_documents=True,
                retriever=vectorstore.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": DEFAULT_RETRIEVAL_K, "include_metadata": True}
                ),
                get_chat_history=lambda h: h,
                memory=memory,
                combine_docs_chain_kwargs={'prompt': PROMPT}
            )
            return conversation_chain.invoke
        
        # For Amazon Nova models
        else:
            llm = NovaLLM(
                model_id=selected_config["model_id"],
                client=BEDROCK_CLIENT,
                max_tokens=selected_config["max_tokens"]
            )
            
            # Custom retrieval chain for Nova models
            def nova_retrieval_chain(query_dict):
                try:
                    question = query_dict["question"]
                    docs = vectorstore.as_retriever(
                        search_type="similarity",
                        search_kwargs={"k": DEFAULT_RETRIEVAL_K, "include_metadata": True}
                    ).invoke(question)
                    
                    # Format the context from documents
                    context = "\n\n".join([doc.page_content for doc in docs])
                    
                    # Log debug info
                    logger.info(f"Retrieved {len(docs)} documents for query: {question[:50]}...")
                    
                    # Replace the variables in the prompt template
                    formatted_prompt = PROMPT.format(context=context, question=question)
                    
                    # Get response from the model
                    answer = llm.invoke(formatted_prompt)
                    
                    # Save to memory
                    memory.save_context({"question": question}, {"answer": answer})
                    
                    # Return in the format expected by the app
                    return {
                        "question": question,
                        "answer": answer,
                        "source_documents": docs,
                        "chat_history": memory.chat_history
                    }
                except Exception as e:
                    logger.error(f"Error in nova_retrieval_chain: {str(e)}")
                    logger.error(traceback.format_exc())
                    return {
                        "question": query_dict["question"],
                        "answer": f"I encountered an error processing your question: {str(e)}",
                        "source_documents": [],
                        "chat_history": memory.chat_history
                    }
            
            return nova_retrieval_chain
        
    except Exception as e:
        logger.error(f"Error creating conversation chain: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"Error creating conversation chain: {str(e)}")
        return None

def handle_userinput(user_question: str):
    """
    Process user input and generate response.
    
    Args:
        user_question: User's question text
    """
    if not user_question.strip():
        st.warning("Please enter a question.")
        return
        
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    try:
        with st.spinner("Thinking..."):
            # Track processing time for metrics
            start_time = time.time()
            
            # Get conversation response
            response = st.session_state.conversation({'question': user_question})
            
            # Calculate processing time
            processing_time = time.time() - start_time
            logger.info(f"Processing time: {processing_time:.2f} seconds")
            
            # Update chat history
            if 'chat_history' in response:
                st.session_state.chat_history = response.get('chat_history', [])
            elif 'answer' in response:
                # Direct response without chat history, create chat history
                if not st.session_state.chat_history:
                    st.session_state.chat_history = []
                st.session_state.chat_history.append(HumanMessage(content=user_question))
                st.session_state.chat_history.append(AIMessage(content=response['answer']))
            
            # Display messages with improved formatting
            messages_container = st.container()
            with messages_container:
                for i, message in enumerate(st.session_state.chat_history):
                    if isinstance(message, HumanMessage):
                        st.chat_message("user", avatar="🧑‍💻").write(message.content)
                    else:
                        with st.chat_message("assistant", avatar=ICON):
                            st.write(message.content)
                            
                            # Show source documents (only for the most recent AI message)
                            if i == len(st.session_state.chat_history) - 1 and 'source_documents' in response:
                                with st.expander("View sources"):
                                    for j, doc in enumerate(response['source_documents']):
                                        st.markdown(f"**Source {j+1}:**")
                                        st.markdown(f"```\n{doc.page_content[:300]}...\n```")
                
            # Show processing time as a small note
            st.caption(f"Response generated in {processing_time:.2f} seconds")
                    
    except Exception as e:
        logger.error(f"Error in handle_userinput: {str(e)}")
        logger.error(traceback.format_exc())
        st.error("I encountered an error processing your question. Please try rephrasing it or uploading your documents again.")

def reset_chat():
    """Reset the chat history and refresh the UI."""
    if "chat_history" in st.session_state:
        st.session_state.chat_history = []
    
    # Re-initialize conversation with existing vectorstore
    if "vectorstore" in st.session_state and st.session_state.vectorstore:
        st.session_state.conversation = get_conversation_chain(
            st.session_state.vectorstore, 
            st.session_state.model_selection
        )
    
    # This triggers a rerun to refresh the page and clear displayed messages
    st.rerun()

def init_session_state():
    """Initialize session state variables"""
    # Check and initialize session state variables
    if "model_selection" not in st.session_state:
        st.session_state.model_selection = "Anthropic Claude 3 Sonnet"
        
    if "vectorstore" not in st.session_state:
        st.session_state.vectorstore = get_vectorstore(None)
        
    if "conversation" not in st.session_state:
        st.session_state.conversation = get_conversation_chain(
            st.session_state.vectorstore,
            st.session_state.model_selection
        )
        
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

def display_sidebar():
    """Display and handle sidebar elements"""
    with st.sidebar:
        # Logo and title
        logo_url = "static/Powered-By_logo-stack_RGB_REV.png"
        st.image(logo_url, width=150)
        
        # Quick start guide
        with st.expander("📖 Quick Start Guide", expanded=True):
            st.markdown("""
            1. 📄 Upload your PDF files
            2. 🔄 Click 'Process'
            3. 💬 Ask questions about your documents
            """)
        
        # Warning for region setting
        if os.getenv('AWS_REGION') not in [None, DEFAULT_REGION]:
            st.warning(f"""
            ⚠️ Amazon Nova models require {DEFAULT_REGION} region.
            Current region setting may not work with Nova models.
            """, icon="⚠️")
        
        # Model selection dropdown
        st.subheader("🤖 Model Selection")
        model_options = [
            "Anthropic Claude 3 Sonnet",
            "Amazon Nova Micro", 
            "Amazon Nova Lite", 
            "Amazon Nova Pro"
        ]
        
        selected_model = st.selectbox(
            "Choose a model:",
            model_options,
            index=model_options.index(st.session_state.model_selection) if st.session_state.model_selection in model_options else 0,
            key="model_selector"
        )
        
        # Update the model if changed
        if selected_model != st.session_state.model_selection:
            with st.spinner(f"Switching to {selected_model}..."):
                st.session_state.model_selection = selected_model
                # Reinitialize the conversation with the new model
                if "vectorstore" in st.session_state and st.session_state.vectorstore:
                    st.session_state.conversation = get_conversation_chain(
                        st.session_state.vectorstore, 
                        st.session_state.model_selection
                    )
                    st.success(f"Switched to {selected_model}!", icon="✅")
        
        # Document upload section
        st.subheader("📁 Document Upload")
        pdf_docs = st.file_uploader(
            "Upload PDFs and click 'Process'",
            type="pdf",
            accept_multiple_files=True,
            help="Upload your PDF documents to ask questions about them"
        )
        
        # Document processing and reset buttons
        col1, col2 = st.columns(2)
        with col1:
            process_button = st.button(
                "🔄 Process", 
                type="primary",
                help="Process the uploaded documents",
                key="process_docs"
            )
        
        with col2:
            # Reset chat button
            reset_button = st.button(
                "🗑️ Reset Chat", 
                type="secondary",
                help="Clear the current conversation",
                key="reset_chat"
            )
            if reset_button:
                reset_chat()
        
        # Process documents when button is clicked
        if process_button and pdf_docs:
            with st.spinner("Processing documents..."):
                # Show a progress bar
                progress_bar = st.progress(0)
                
                # Processing steps
                progress_bar.progress(10, text="Reading PDF text...")
                raw_text = get_pdf_text(pdf_docs)
                
                if raw_text:
                    progress_bar.progress(40, text="Creating text chunks...")
                    text_chunks = get_text_chunks(raw_text)
                    
                    if text_chunks:
                        progress_bar.progress(70, text="Building vector database...")
                        vectorstore = get_vectorstore(text_chunks)
                        
                        if vectorstore:
                            progress_bar.progress(90, text="Initializing conversation chain...")
                            st.session_state.vectorstore = vectorstore
                            st.session_state.conversation = get_conversation_chain(
                                vectorstore, 
                                st.session_state.model_selection
                            )
                            
                            progress_bar.progress(100, text="Done!")
                            st.success('Documents processed successfully!', icon="✅")
                        else:
                            st.error("Error creating vector store")
                    else:
                        st.error("Error creating text chunks")
                else:
                    st.error("Error processing PDFs")
        
        # Show an error if process is clicked without documents
        elif process_button and not pdf_docs:
            st.error("Please upload at least one PDF document")
            
        st.divider()
        
        # Sample questions
        with st.expander("💡 Sample Questions", expanded=True):
            st.markdown("""
            1. What are pgvector's capabilities in Aurora PostgreSQL?
            2. Explain Optimized Reads
            3. How do Aurora Optimized Reads improve performance?
            4. What are Bedrock agents?
            5. How does Knowledge Bases handle document chunking?
            6. Which vector databases work with Knowledge Bases?
            """)
            
        # About section
        with st.expander("ℹ️ About", expanded=False):
            st.markdown("""
            This application demonstrates Retrieval Augmented Generation (RAG) using:
            - Amazon Bedrock for LLM and embedding models
            - Aurora PostgreSQL with pgvector for vector storage
            - LangChain for the retrieval pipeline
            
            Source: [GitHub Repository](https://github.com/aws-samples/aurora-postgresql-pgvector)
            """)

def main():
    """Main application function"""
    # Page configuration
    st.set_page_config(
        page_title=TITLE,
        layout="wide",
        page_icon=ICON,
        initial_sidebar_state="expanded"
    )
    
    # Apply custom CSS
    st.write(css, unsafe_allow_html=True)
    
    # Initialize session state
    init_session_state()
    
    # Display sidebar
    display_sidebar()

    # Main content
    st.header(f"{ICON} {TITLE}")
    
    # Subheader with model info
    st.subheader(f"Currently using: {st.session_state.model_selection}", divider="rainbow")
    
    # Introductory text
    st.markdown(
        '<p style="font-size: 16px;">Leveraging '
        '<a href="https://aws.amazon.com/bedrock/">Amazon Bedrock</a> and '
        '<a href="https://github.com/pgvector/pgvector">pgvector</a> '
        'for intelligent document analysis</p>',
        unsafe_allow_html=True
    )

    # Display architecture diagram in expander
    with st.expander("View Architecture Diagram", expanded=False):
        image = Image.open("static/RAG_APG.png")
        st.image(image, caption='Architecture Overview')

    # Chat interface
    st.divider()
    st.subheader("💬 Chat with your documents")
    
    # Input section
    user_question = st.text_input(
        "Ask about your documents:",
        placeholder="What would you like to know?",
        key="question_input",
        on_change=None  # Explicitly set no callback
    )
    
    # Search button
    col1, col2 = st.columns([1, 5])
    with col1:
        go_button = st.button(
            "🔍 Search", 
            type="primary", 
            key="search_button",
            help="Search your documents with this question"
        )

    if go_button or user_question and st.session_state.get("_clicked_search_last_time") != user_question:
        # Track that we've processed this question
        st.session_state["_clicked_search_last_time"] = user_question
        handle_userinput(user_question)

if __name__ == '__main__':
    try:
        # Load environment variables
        load_dotenv()
        
        # Initialize AWS Bedrock client
        aws_region = os.getenv('AWS_REGION', DEFAULT_REGION)
        BEDROCK_CLIENT = boto3.client("bedrock-runtime", aws_region)
        logger.info(f"Initialized Bedrock client in region: {aws_region}")
        
        # Database connection string
        connection = f"postgresql+psycopg://{os.getenv('PGUSER')}:{os.getenv('PGPASSWORD')}@{os.getenv('PGHOST')}:{os.getenv('PGPORT')}/{os.getenv('PGDATABASE')}"
        
        main()
    except Exception as e:
        logger.error(f"Application initialization error: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"Application initialization error: {str(e)}")
