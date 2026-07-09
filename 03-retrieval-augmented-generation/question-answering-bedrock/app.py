# Import libraries
from dotenv import load_dotenv
import sys
import os
# rag_shared lives one directory up from this app
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from rag_shared import get_pdf_text as _get_pdf_text_core, get_text_chunks, build_pg_connection_string
from htmlTemplates import css
from langchain_postgres import PGVector
from langchain_aws import BedrockEmbeddings, ChatBedrockConverse
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_history_aware_retriever
import streamlit as st
import boto3
from PIL import Image
import time
import logging
import traceback
from typing import List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
DEFAULT_REGION = "us-west-2"
DEFAULT_RETRIEVAL_K = 3
TITLE = "Generative AI Q&A powered by Amazon Bedrock"
ICON = "🤖"


def get_pdf_text(pdf_docs) -> Optional[str]:
    """
    Extract text from uploaded PDF documents.
    Wraps rag_shared.get_pdf_text with Streamlit spinner/error handling.

    Args:
        pdf_docs: List of uploaded PDF files

    Returns:
        Extracted text or None if processing fails
    """
    if not pdf_docs:
        return None
    try:
        with st.spinner("Extracting text from PDFs..."):
            text = _get_pdf_text_core(pdf_docs)
        return text if text else None
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        st.error(f"Error processing PDF: {str(e)}")
        return None


def _get_text_chunks(text: Optional[str]) -> Optional[List[str]]:
    """
    Split text into smaller chunks for processing.
    Wraps rag_shared.get_text_chunks with error handling.

    Args:
        text: Text to be split into chunks

    Returns:
        List of text chunks or None if processing fails
    """
    if not text:
        return None
    try:
        chunks = get_text_chunks(text)
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


def get_conversation_chain(vectorstore, model_selection: str):
    """
    Build an LCEL retrieval chain using ChatBedrockConverse for all models
    (Claude and Amazon Nova share one code path; only model_id differs).

    Args:
        vectorstore: Vector store for document retrieval
        model_selection: Selected model name

    Returns:
        Callable that accepts {"question": str, "chat_history": list} and returns
        {"answer": str, "source_documents": list, "chat_history": list}
        or None if creation fails.
    """
    if not vectorstore:
        logger.error("Cannot create conversation chain: Vector store is None")
        return None

    try:
        # Model configurations — ChatBedrockConverse works for both Claude and Nova
        model_config = {
            "Claude Sonnet 5": {
                "model_id": os.environ.get("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-5"),
                "temperature": 0.5,
                "max_tokens": 8192,
            },
            "Amazon Nova Micro": {
                "model_id": "us.amazon.nova-micro-v1:0",
                "temperature": 0.5,
                "max_tokens": 1000,
            },
            "Amazon Nova Lite": {
                "model_id": "us.amazon.nova-lite-v1:0",
                "temperature": 0.5,
                "max_tokens": 1000,
            },
            "Amazon Nova Pro": {
                "model_id": "us.amazon.nova-pro-v1:0",
                "temperature": 0.5,
                "max_tokens": 1000,
            },
        }

        if model_selection not in model_config:
            logger.error(f"Unknown model selection: {model_selection}")
            st.error(f"Unknown model: {model_selection}")
            return None

        cfg = model_config[model_selection]

        # Single LLM class for all Bedrock models (Claude + Nova)
        llm = ChatBedrockConverse(
            model=cfg["model_id"],
            client=BEDROCK_CLIENT,
            temperature=cfg["temperature"],
            max_tokens=cfg["max_tokens"],
        )

        retriever = vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": DEFAULT_RETRIEVAL_K, "include_metadata": True},
        )

        # --- history-aware retriever ---
        # Rewrites the user question given prior chat history so standalone
        # retrieval works even in a multi-turn conversation.
        condense_prompt = ChatPromptTemplate.from_messages([
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            ("human",
             "Given the conversation above, generate a standalone search query "
             "that captures the user's intent. Return only the query, no explanation."),
        ])
        history_aware_retriever = create_history_aware_retriever(
            llm, retriever, condense_prompt
        )

        # --- answer chain ---
        answer_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a helpful AI assistant. Your role is to provide clear, "
             "concise answers using only the information from the context below.\n\n"
             "Guidelines for your responses:\n"
             "- Use English and maintain a professional yet conversational tone\n"
             "- Start responses with 'Based on the provided context: '\n"
             "- Answer questions directly using only relevant details from the context\n"
             "- If the context doesn't contain the answer, say 'I apologize, but I don't "
             "find information about that in the provided context. Could you rephrase your question?'\n"
             "- Use bullet points for clarity when appropriate\n"
             "- Provide a brief summary at the end\n\n"
             "Context:\n{context}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
        ])
        docs_chain = create_stuff_documents_chain(llm, answer_prompt)

        # Full retrieval chain
        rag_chain = create_retrieval_chain(history_aware_retriever, docs_chain)

        # Wrap into the dict shape the rest of the app expects:
        # input:  {"question": str}   (chat_history injected from session_state)
        # output: {"answer": str, "source_documents": list, "chat_history": list}
        def chain_callable(query_dict: dict) -> dict:
            question = query_dict["question"]
            chat_history: list = query_dict.get("chat_history", [])
            try:
                result = rag_chain.invoke({
                    "input": question,
                    "chat_history": chat_history,
                })
                answer = result.get("answer", "")
                source_docs = result.get("context", [])
                new_history = list(chat_history) + [
                    HumanMessage(content=question),
                    AIMessage(content=answer),
                ]
                return {
                    "question": question,
                    "answer": answer,
                    "source_documents": source_docs,
                    "chat_history": new_history,
                }
            except Exception as exc:
                logger.error(f"Error in chain_callable: {exc}")
                logger.error(traceback.format_exc())
                return {
                    "question": question,
                    "answer": f"I encountered an error processing your question: {exc}",
                    "source_documents": [],
                    "chat_history": list(chat_history) + [
                        HumanMessage(content=question),
                        AIMessage(content=f"Error: {exc}"),
                    ],
                }

        return chain_callable

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

            # Get conversation response — pass current chat history so the
            # history-aware retriever can condense the question if needed.
            response = st.session_state.conversation({
                "question": user_question,
                "chat_history": st.session_state.chat_history,
            })

            # Calculate processing time
            processing_time = time.time() - start_time
            logger.info(f"Processing time: {processing_time:.2f} seconds")

            # Update chat history from response
            st.session_state.chat_history = response.get("chat_history", [])

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
        st.session_state.model_selection = "Claude Sonnet 5"

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

        # Model selection dropdown
        st.subheader("🤖 Model Selection")
        model_options = [
            "Claude Sonnet 5",
            "Amazon Nova Micro",
            "Amazon Nova Lite",
            "Amazon Nova Pro",
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
                    text_chunks = _get_text_chunks(raw_text)

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

        # Database connection string (psycopg3)
        connection = build_pg_connection_string()

        main()
    except Exception as e:
        logger.error(f"Application initialization error: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"Application initialization error: {str(e)}")
