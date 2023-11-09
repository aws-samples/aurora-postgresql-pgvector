# TODO: Add imports here



# TODO: This function takes a list of PDF documents as input and extracts the text from them using PdfReader. 
# It concatenates the extracted text and returns it.
def get_pdf_text(pdf_docs):
    


# TODO: Given the extracted text, this function splits it into smaller chunks using the RecursiveCharacterTextSplitter module. 
# The chunk size, overlap, and other parameters are configured to optimize processing efficiency.
def get_text_chunks(text):
    
    

# TODO: This function takes the text chunks as input and creates a vector store using Bedrock Embeddings (Titan) and pgvector. 
# The vector store stores the vector representations of the text chunks, enabling efficient retrieval based on semantic similarity.
def get_vectorstore(text_chunks):
    


# TODO: Here, a conversation chain is created using the conversational AI model (Anthropic's Claude v2), vector store (created in the previous function), and conversation memory (ConversationSummaryBufferMemory). 
# This chain allows the Gen AI app to engage in conversational interactions.
def get_conversation_chain(vectorstore):
    


# TODO: This function is responsible for processing the user's input question and generating a response from the chatbot
def handle_userinput(user_question):
    


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
    
    # TODO: Check if the conversation and chat history are not present in the session state and initialize them to None.
    

    # A header with the text appears at the top of the Streamlit application.
    st.header("Generative AI Q&A with Amazon Bedrock, Aurora PostgreSQL and pgvector :books::parrot:")
    subheader = '<p style="font-family:Calibri (Body); color:Grey; font-size: 16px;">Leverage Foundational Models from <a href="https://aws.amazon.com/bedrock/">Amazon Bedrock</a> and <a href="https://github.com/pgvector/pgvector">pgvector</a> as Vector Engine</p>'
    
    # Write the CSS style to the Streamlit application, allowing you to customize the appearance.
    st.markdown(subheader, unsafe_allow_html=True)
    image = Image.open("static/RAG_APG.png")
    st.image(image, caption='Generative AI Q&A with Amazon Bedrock, Aurora PostgreSQL and pgvector')
    
    # TODO: Create a text input box where you can ask questions about your documents.
    
    
    
    # TODO: Define a Go button for user action
    
    
    
    # TODO: If the go button is pressed or the user enters a question, it calls the handle_userinput() function to process the user's input.
    if go_button or user_question:
        with st.spinner("Processing..."):
    
    
    with st.sidebar:
        st.subheader("Your documents")
        pdf_docs = st.file_uploader(
            "Upload your PDFs here and click on 'Process'", type="pdf", accept_multiple_files=True)
    
    # TODO: If the user clicks the "Process" button, the following code is executed:
    # i. raw_text = get_pdf_text(pdf_docs): retrieves the text content from the uploaded PDF documents.
    # ii. text_chunks = get_text_chunks(raw_text): splits the text content into smaller chunks for efficient processing.
    # iii. vectorstore = get_vectorstore(text_chunks): creates a vector store that stores the vector representations of the text chunks.
    if st.button("Process"):
        with st.spinner("Processing"):
    
    
    
    with st.sidebar:
        st.divider()

    st.sidebar.markdown(
    """
    ### Sample questions to get started:
    1. What is Amazon Aurora?
    2. How can I migrate from PostgreSQL to Aurora and the other way around?
    3. What does "three times the performance of PostgreSQL" mean?
    4. What is Aurora Standard and Aurora I/O-Optimized?
    5. How do I scale the compute resources associated with my Amazon Aurora DB Instance?
    6. How does Amazon Aurora improve my databases fault tolerance to disk failures?
    7. How does Aurora improve recovery time after a database crash?
    8. How can I improve upon the availability of a single Amazon Aurora database?
    """
)
    
if __name__ == '__main__':
    # This function loads the environment variables from a .env file.
    load_dotenv()
    
    
    # TODO: Define the Bedrock client
    
    
    
    # TODO: Create the connection string for pgvector from .env file.
    
    
    
    main()
