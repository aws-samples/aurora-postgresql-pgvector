import sys
import os
# rag_shared lives one directory up from this app
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from rag_shared import get_pdf_text, get_text_chunks
import streamlit as st
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFaceEndpoint
from langchain_postgres.vectorstores import PGVector
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_history_aware_retriever
from htmlTemplates import css, bot_template, user_template

# NOTE: A HUGGINGFACEHUB_API_TOKEN environment variable is required to use
# the HuggingFace Inference API.  Add it to your .env file before running.


def get_vectorstore(text_chunks):
    # HuggingFaceEmbeddings from langchain-huggingface replaces the sunset
    # langchain_community.embeddings.HuggingFaceInstructEmbeddings.
    # all-mpnet-base-v2 produces 768-dim vectors — no schema change required.
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-mpnet-base-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    if text_chunks is None:
        return PGVector(
            connection=CONNECTION_STRING,
            embeddings=embeddings,
        )
    return PGVector.from_texts(
        texts=text_chunks,
        embedding=embeddings,
        connection=CONNECTION_STRING,
    )


def get_conversation_chain(vectorstore):
    # HuggingFaceEndpoint from langchain-huggingface replaces the sunset
    # langchain_community.llms.HuggingFaceHub.
    # zephyr-7b-beta supports text-generation via the HF Serverless Inference API.
    llm = HuggingFaceEndpoint(
        repo_id="HuggingFaceH4/zephyr-7b-beta",
        task="text-generation",
        temperature=0.2,
        max_new_tokens=512,
    )

    retriever = vectorstore.as_retriever(search_kwargs={"k": 1})

    # History-aware retriever: rewrites the question as a standalone query when
    # there is prior chat history, so retrieval works across conversation turns.
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

    # Answer chain
    answer_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "Answer the user's question using only the context below.\n\n"
         "Context:\n{context}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])
    docs_chain = create_stuff_documents_chain(llm, answer_prompt)

    return create_retrieval_chain(history_aware_retriever, docs_chain)


def handle_userinput(user_question):
    if "chat_history" not in st.session_state or st.session_state.chat_history is None:
        st.session_state.chat_history = []

    try:
        result = st.session_state.conversation.invoke({
            "input": user_question,
            "chat_history": st.session_state.chat_history,
        })
    except ValueError:
        st.write("Sorry, please ask again in a different way.")
        return

    answer = result.get("answer", "")

    # Append this turn to the explicit history list
    st.session_state.chat_history = st.session_state.chat_history + [
        HumanMessage(content=user_question),
        AIMessage(content=answer),
    ]

    # Render history (alternating user / bot)
    for i, message in enumerate(st.session_state.chat_history):
        if isinstance(message, HumanMessage):
            st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
        else:
            st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="Streamlit Question Answering App",
                       layout="wide",
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
        st.session_state.chat_history = []

    st.header("GenAI Q&A with pgvector and Amazon Aurora PostgreSQL :books::parrot:")
    user_question = st.text_input("Ask a question about your documents:")
    if user_question:
        handle_userinput(user_question)

    with st.sidebar:
        st.subheader("Your documents")
        pdf_docs = st.file_uploader(
            "Upload your PDFs here and click on 'Process'", type="pdf", accept_multiple_files=True)
        if st.button("Process"):
            if not pdf_docs:
                st.error("Please upload at least one PDF document before processing.")
            else:
                with st.spinner("Processing"):
                    # get pdf text
                    raw_text = get_pdf_text(pdf_docs)

                    # get the text chunks
                    text_chunks = get_text_chunks(raw_text)

                    # create vector store
                    vectorstore = get_vectorstore(text_chunks)

                    # create conversation chain
                    st.session_state.conversation = get_conversation_chain(vectorstore)
                    # reset history on new document upload
                    st.session_state.chat_history = []

                    st.success('PDF uploaded successfully!', icon="✅")


if __name__ == '__main__':
    from rag_shared import build_pg_connection_string
    load_dotenv()
    CONNECTION_STRING = build_pg_connection_string()
    main()
