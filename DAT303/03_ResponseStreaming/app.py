import streamlit as st
from PyPDF2 import PdfReader
from langchain.embeddings import BedrockEmbeddings
from langchain.llms import Bedrock
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
from dotenv import load_dotenv
import os

class StreamHandler(BaseCallbackHandler):
    def __init__(self, container, initial_text=""):
        self.container = container
        self.text = initial_text

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.text += token
        self.container.markdown(self.text)

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text


def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ".", " "],
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
     )

    chunks = text_splitter.split_text(text)
    return chunks


def get_vectorstore(text_chunks):
    if text_chunks is None:
        return PGVector(
            connection_string=CONNECTION_STRING,
            embedding_function=embeddings,
        )
    return PGVector.from_texts(texts=text_chunks, embedding=embeddings, connection_string=CONNECTION_STRING)


def main():
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

    if "vectorDB" not in st.session_state:
        st.session_state.vectorDB = get_vectorstore(None)

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    st.header("Generative AI Streaming Chat with Amazon Bedrock, Aurora PostgreSQL and pgvector :books::parrot:")
    subheader = '<p style="font-family:Calibri (Body); color:Grey; font-size: 16px;">Leverage Foundational Models from <a href="https://aws.amazon.com/bedrock/">Amazon Bedrock</a> and <a href="https://github.com/pgvector/pgvector">pgvector</a> as Vector Engine</p>'
    st.markdown(subheader, unsafe_allow_html=True)

    for msg in st.session_state.messages:
        if msg.type == "human":
            st.chat_message("Human: ").write(msg.content)
        if msg.type == "ai":
            st.chat_message("Assistant: ").write(msg.content)

    if prompt := st.chat_input():
        st.chat_message("user").write(prompt)
        st.session_state.messages.append(ChatMessage(role="user", content=prompt))
        with st.chat_message("Assistant"):
                stream_handler = StreamHandler(st.empty())

                llm = Bedrock(model_id="anthropic.claude-v2", streaming=True, callbacks=[stream_handler])
                llm.model_kwargs = {"temperature": 0.5, "max_tokens_to_sample": 8191}

                general_system_template = """ 
                Human: "You are a helpful and talkative assistant that answers questions directly and only using the information provided in the context below. 
                Guidance for answers:
                    - Always use English as the language in your responses.
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
    load_dotenv()

    region_name ="us-west-2"
    model_id = "amazon.titan-embed-text-v1"

    embeddings = BedrockEmbeddings(
        region_name=region_name,
        model_id=model_id
    )

    CONNECTION_STRING = PGVector.connection_string_from_db_params(                                                  
        driver = os.environ.get("PGVECTOR_DRIVER"),
        user = os.environ.get("PGVECTOR_USER"),                                      
        password = os.environ.get("PGVECTOR_PASSWORD"),                                  
        host = os.environ.get("PGVECTOR_HOST"),                                            
        port = os.environ.get("PGVECTOR_PORT"),                                          
        database = os.environ.get("PGVECTOR_DATABASE")                                       
)                                      

main()