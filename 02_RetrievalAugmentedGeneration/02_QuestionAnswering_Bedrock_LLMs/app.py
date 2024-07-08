# Import libraries
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain_postgres import PGVector
from langchain_postgres.vectorstores import PGVector
from langchain.memory import ConversationSummaryBufferMemory
from langchain.chains import ConversationalRetrievalChain
from htmlTemplates import css
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import BedrockEmbeddings
from langchain_aws import ChatBedrock
from langchain_core.prompts import PromptTemplate
import streamlit as st
import boto3
from PIL import Image
import os
import traceback

# This function takes a list of PDF documents as input and extracts the text from them using PdfReader. 
# It concatenates the extracted text and returns it.
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

# Given the extracted text, this function splits it into smaller chunks using the RecursiveCharacterTextSplitter module. 
# The chunk size, overlap, and other parameters are configured to optimize processing efficiency.
def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ".", " "],
        chunk_size=1000, 
        chunk_overlap=200, 
        length_function=len
     )

    chunks = text_splitter.split_text(text)
    return chunks

# This function takes the text chunks as input and creates a vector store using Bedrock Embeddings (Titan) and pgvector. 
# The vector store stores the vector representations of the text chunks, enabling efficient retrieval based on semantic similarity.
def get_vectorstore(text_chunks):
    # Create the Titan embeddings
    embeddings = BedrockEmbeddings(model_id= "amazon.titan-embed-text-v2:0", client=BEDROCK_CLIENT)
    if text_chunks is None:
        return PGVector(
            connection=connection,
            embeddings=embeddings,
            use_jsonb=True
        )
    return PGVector.from_texts(texts=text_chunks, embedding=embeddings, connection=connection)
        
# Here, a conversation chain is created using the conversational AI model (Anthropic's Claude v2), vector store (created in the previous function), and conversation memory (ConversationSummaryBufferMemory). 
# This chain allows the Gen AI app to engage in conversational interactions.
def get_conversation_chain(vectorstore):
    # Define model_id, client and model keyword arguments for Anthropic Claude v3
    llm = ChatBedrock(model_id="anthropic.claude-3-sonnet-20240229-v1:0", client=BEDROCK_CLIENT)
    llm.model_kwargs = {"temperature": 0.5, "max_tokens": 8191}
    
    # The text that you give Claude is designed to elicit, or "prompt", a relevant output. A prompt is usually in the form of a question or instructions. When prompting Claude through the API, it is very important to use the correct `\n\nHuman:` and `\n\nAssistant:` formatting.
    # Claude was trained as a conversational agent using these special tokens to mark who is speaking. The `\n\nHuman:` (you) asks a question or gives instructions, and the`\n\nAssistant:` (Claude) responds.
    prompt_template = """Human: You are a helpful assistant that answers questions directly and only using the information provided in the context below. 
    Guidance for answers:
        - Always use English as the language in your responses.
        - In your answers, always use a professional tone.
        - Begin your answers with "Based on the context provided: "
        - Simply answer the question clearly and with lots of detail using only the relevant details from the information below. If the context does not contain the answer, say "Sorry, I didn't understand that. Could you rephrase your question?"
        - Use bullet-points and provide as much detail as possible in your answer. 
        - Always provide a summary at the end of your answer.
        
    Now read this context below and answer the question at the bottom.
    
    Context: {context}

    Question: {question}
    
    Assistant:"""

    PROMPT = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )
    
    memory = ConversationSummaryBufferMemory(
        llm=llm,
        memory_key='chat_history',
        return_messages=True,
        ai_prefix="Assistant",
        output_key='answer')
    
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        chain_type="stuff",
        return_source_documents=True,
        retriever=vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3, "include_metadata": True}),
        get_chat_history=lambda h : h,
        memory=memory,
        combine_docs_chain_kwargs={'prompt': PROMPT}
    )
    
    return conversation_chain.invoke

# This function is responsible for processing the user's input question and generating a response from the chatbot
def handle_userinput(user_question):
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    try:
        response = st.session_state.conversation({'question': user_question})
        
    except ValueError:
        st.write("Sorry, I didn't understand that. Could you rephrase your question?")
        print(traceback.format_exc())
        return

    st.session_state.chat_history = response['chat_history']

    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.success(message.content, icon="🤔")
        else:
            st.write(message.content)

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
    2. What is Amazon Aurora Optimized Reads for Aurora PostgreSQL?
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
