# Import libraries
import sys
import os
# rag_shared lives one directory up from this app
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from rag_shared import get_pdf_text, get_text_chunks, build_pg_connection_string
from langchain_aws import BedrockEmbeddings
from langchain_aws import ChatBedrock
from langchain_core.messages import (
    AIMessage,
    HumanMessage
)
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import SystemMessagePromptTemplate
from langchain_core.prompts import HumanMessagePromptTemplate
from langchain_postgres.vectorstores import PGVector
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import ChatMessage
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
import streamlit as st
from dotenv import load_dotenv
from PIL import Image
import boto3

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
            connection=connection,
            embeddings=embeddings,
            use_jsonb=True
        )
    return PGVector.from_texts(texts=text_chunks, embedding=embeddings, connection=connection)

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

    prompt = st.chat_input("Your question")
    if prompt:
        st.chat_message("user").write(prompt)
        st.session_state.messages.append(ChatMessage(role="user", content=prompt))
        with st.chat_message("Assistant"):
            stream_handler = StreamHandler(st.empty())

            llm = ChatBedrock(
                model_id=os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0"),
                streaming=True,
                callbacks=[stream_handler],
                client=BEDROCK_CLIENT,
                model_kwargs={"temperature": 0.5, "max_tokens": 8191},
            )

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

            general_user_template = "Question:```{input}```"

            qa_prompt = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(general_system_template),
                HumanMessagePromptTemplate.from_template(general_user_template),
            ])

            # LCEL: create_stuff_documents_chain + create_retrieval_chain replace
            # ConversationalRetrievalChain while preserving streaming callbacks.
            docs_chain = create_stuff_documents_chain(llm, qa_prompt)
            rag_chain = create_retrieval_chain(
                st.session_state.vectorDB.as_retriever(search_kwargs={"k": 1}),
                docs_chain,
            )

            response = rag_chain.invoke({"input": prompt})
            answer = response.get("answer", "")

            st.session_state.messages = st.session_state.messages + [
                HumanMessage(content=prompt),
                AIMessage(content=answer),
            ]

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

    # Define the Bedrock client (region from env; defaults to us-west-2)
    aws_region = os.environ.get('AWS_REGION', 'us-west-2')
    BEDROCK_CLIENT = boto3.client("bedrock-runtime", aws_region)

    # Define the Embedding model using the Bedrock client
    embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v2:0", client=BEDROCK_CLIENT)

    # Create the connection string for pgvector (psycopg3)
    connection = build_pg_connection_string()

    main()
