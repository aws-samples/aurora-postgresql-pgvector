# Import libraries
from PyPDF2 import PdfReader
from langchain_community.embeddings import BedrockEmbeddings
from langchain_community.chat_models import BedrockChat
from langchain.schema import (
    AIMessage,
    HumanMessage
)
from langchain.prompts import ChatPromptTemplate
from langchain.prompts import SystemMessagePromptTemplate
from langchain.prompts import HumanMessagePromptTemplate
from langchain.vectorstores.pgvector import PGVector
from langchain.chains import ConversationalRetrievalChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import ChatMessage
import streamlit as st
from dotenv import load_dotenv
from PIL import Image
import os
import boto3

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

# Create a custom handler and pass a streamlit container to it. This is required for response streaming.
class StreamHandler(BaseCallbackHandler):
    def __init__(self, container, initial_text=""):
        self.container = container
        self.text = initial_text

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.text += token
        self.container.markdown(self.text)

# This function takes the text chunks as input and creates a vector store using Bedrock Embeddings (Titan) and pgvector. 
# The vector store stores the vector representations of the text chunks, enabling efficient retrieval based on semantic similarity.
def get_vectorstore(text_chunks):
    if text_chunks is None:
        return PGVector(
            connection_string=CONNECTION_STRING,
            embedding_function=embeddings,
        )
    return PGVector.from_texts(texts=text_chunks, embedding=embeddings, connection_string=CONNECTION_STRING)

def main():
    # Set the page configuration for the Streamlit application, including the page title and icon.
    st.set_page_config(page_title="Streamlit Question Answering App",
                       layout="wide",
                       page_icon=":books::parrot:")

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
    # Check if the vectorDB and messages are not present in the session state and initialize them to None.
    if "vectorDB" not in st.session_state:
        st.session_state.vectorDB = get_vectorstore(None)

    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    
    # A header with the text appears at the top of the Streamlit application.
    st.header("Generative AI Streaming Chat with Amazon Bedrock, Aurora PostgreSQL and pgvector :books::parrot:")
    subheader = '<p style="font-family:Calibri (Body); color:Grey; font-size: 16px;">Leverage Foundational Models from <a href="https://aws.amazon.com/bedrock/">Amazon Bedrock</a> and <a href="https://github.com/pgvector/pgvector">pgvector</a> as Vector Engine</p>'
    
    # Write the CSS style to the Streamlit application, allowing you to customize the appearance.
    st.markdown(subheader, unsafe_allow_html=True)
    st.image(Image.open("static/Streaming_Responses_RAG.png"))
    
    # A chat message can be associated with an AI assistant, a human or a system role. Here we are displaying the question (asked by the human) and the response (answered by the AI assistant) alternately.
    for msg in st.session_state.messages:
        if msg.type == "human":
            st.chat_message("Human: ").write(msg.content)
        if msg.type == "ai":
            st.chat_message("Assistant: ").write(msg.content)

    # The text that you give Claude is designed to elicit, or "prompt", a relevant output. A prompt is usually in the form of a question or instructions. 
    # When prompting Claude through the API, it is very important to use the correct \n\nHuman: and \n\nAssistant: formatting.
    # Claude was trained as a conversational agent using these special tokens to mark who is speaking. 
    # The \n\nHuman: (you) asks a question or gives instructions, and the\n\nAssistant: (Claude) responds.
    prompt = st.chat_input("Your question")
    if prompt:
        st.chat_message("user").write(prompt)
        st.session_state.messages.append(ChatMessage(role="user", content=prompt))
        with st.chat_message("Assistant"):
            stream_handler = StreamHandler(st.empty())

            llm = BedrockChat(model_id="anthropic.claude-v2:1", streaming=True, callbacks=[stream_handler], client=BEDROCK_CLIENT)
            llm.model_kwargs = {"temperature": 0.5, "max_tokens": 8191}

            general_system_template = """ 
            Human: "You are a helpful and talkative assistant that answers questions directly in only English and only using the information provided in the context below. 
            Guidance for answers:
                - In your answers, always use a professional tone.
                - Begin your answers with "Based on the context provided: "
                - Simply answer the question clearly and with lots of detail using only the relevant details from the information below. If the context does not contain the answer, say "I don't know."
                - Use bullet-points and provide as much detail as possible in your answer. 
                - Always provide a summary at the end of your answer.
            ----
            {context}
            ----

            Assistant: """
                
            general_user_template = "Question:```{question}```"

            messages = [
                SystemMessagePromptTemplate.from_template(general_system_template),
                HumanMessagePromptTemplate.from_template(general_user_template)
            ]
                
            qa_prompt = ChatPromptTemplate.from_messages(messages)

            conversation_chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                chain_type="stuff",
                combine_docs_chain_kwargs={"prompt": qa_prompt},
                retriever=st.session_state.vectorDB.as_retriever(search_kwargs={"k": 1}),
            )
                
            response = conversation_chain({'question': prompt, 'chat_history':st.session_state.messages})

            st.session_state.messages = st.session_state.messages + [HumanMessage(content = response["question"]), AIMessage(content = response["answer"])]
    
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
                st.session_state.vectorDB = get_vectorstore(text_chunks)

                st.success('PDF uploaded successfully!', icon="✅")
        
        with st.sidebar:
            st.divider()

        st.sidebar.markdown(
        """
        ### Sample questions to get started:
        1. How has AWS evolved over time?
        2. How has Amazon managed to make AWS so successful?
        3. What business challenges has Amazon had to overcome?
        4. How was Amazon impacted by COVID-19?
        5. What is Amazon's AI strategy?
        """
        )

if __name__ == '__main__':
    # This function loads the environment variables from a .env file.
    load_dotenv()
    
    # Define the Bedrock client
    BEDROCK_CLIENT = boto3.client("bedrock-runtime", 'us-west-2')
    
    # Define the Embedding model using the Bedrock client
    embeddings = BedrockEmbeddings(model_id= "amazon.titan-embed-text-v1", client=BEDROCK_CLIENT)
    
    # Create the connection string for pgvector from .env file.
    CONNECTION_STRING = PGVector.connection_string_from_db_params(                                                  
        driver = os.environ.get("PGVECTOR_DRIVER"),
        user = os.environ.get("PGVECTOR_USER"),                                      
        password = os.environ.get("PGVECTOR_PASSWORD"),                                  
        host = os.environ.get("PGVECTOR_HOST"),                                            
        port = os.environ.get("PGVECTOR_PORT"),                                          
        database = os.environ.get("PGVECTOR_DATABASE")                                       
    )

main()
