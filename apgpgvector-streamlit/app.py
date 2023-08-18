import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.embeddings import HuggingFaceInstructEmbeddings
from langchain.llms import HuggingFaceHub
from langchain.vectorstores.pgvector import PGVector
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from htmlTemplates import css, bot_template, user_template
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text


def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
     )

    chunks = text_splitter.split_text(text)
    return chunks


def get_vectorstore(text_chunks):
    embeddings = HuggingFaceInstructEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
    if text_chunks is None:
        return PGVector(
            connection_string=CONNECTION_STRING,
            embedding_function=embeddings,
        )
    return PGVector.from_texts(texts=text_chunks, embedding=embeddings, connection_string=CONNECTION_STRING)


def get_conversation_chain(vectorstore):
    llm = HuggingFaceHub(repo_id="MBZUAI/LaMini-T5-738M", model_kwargs={"temperature":0.2, "max_length":4096})

    memory = ConversationBufferMemory(
        memory_key='chat_history', return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(search_kwargs={"k": 1}),
        memory=memory
    )
    return conversation_chain


def handle_userinput(user_question):
    try:
        response = st.session_state.conversation({'question': user_question})
    except ValueError:
        st.write("Sorry, please ask again in a different way.")
        return

    st.session_state.chat_history = response['chat_history']

    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.write(user_template.replace(
                "{{MSG}}", message.content), unsafe_allow_html=True)
        else:
            st.write(bot_template.replace(
                "{{MSG}}", message.content), unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="Streamlit Question Answering App",
                       page_icon=":books::parrot:")
    st.write(css, unsafe_allow_html=True)

    st.sidebar.markdown(
    """
    ### Instructions:
    1. Browse and upload PDF files
    2. Click Process
    3. Type your question in the search bar to get more insights
    """
)

    if "conversation" not in st.session_state:
        st.session_state.conversation = get_conversation_chain(get_vectorstore(None))
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None

    st.header("GenAI Q&A with pgvector and Amazon Aurora PostgreSQL :books::parrot:")
    user_question = st.text_input("Ask a question about your documents:")
    if user_question:
        handle_userinput(user_question)

    with st.sidebar:
        st.subheader("Your documents")
        pdf_docs = st.file_uploader(
            "Upload your PDFs here and click on 'Process'", type="pdf", accept_multiple_files=True)
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


if __name__ == '__main__':
    load_dotenv()
    
    CONNECTION_STRING = PGVector.connection_string_from_db_params(                                                  
        driver = os.environ.get("PGVECTOR_DRIVER"),
        user = os.environ.get("PGVECTOR_USER"),                                      
        password = os.environ.get("PGVECTOR_PASSWORD"),                                  
        host = os.environ.get("PGVECTOR_HOST"),                                            
        port = os.environ.get("PGVECTOR_PORT"),                                          
        database = os.environ.get("PGVECTOR_DATABASE")                                       
)  

    main()
