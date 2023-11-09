# TODO: Add imports here



# TODO: This function takes a list of PDF documents as input and extracts the text from them using PdfReader. 
# It concatenates the extracted text and returns it.
def get_pdf_text(pdf_docs):
    
    

# TODO: Given the extracted text, this function splits it into smaller chunks using the RecursiveCharacterTextSplitter module. 
# The chunk size, overlap, and other parameters are configured to optimize processing efficiency.
def get_text_chunks(text):
    
    
    
# TODO: Create a custom handler and pass a streamlit container to it
class StreamHandler(BaseCallbackHandler):
    


# TODO: This function takes the text chunks as input and creates a vector store using Bedrock Embeddings (Titan) and pgvector. 
# The vector store stores the vector representations of the text chunks, enabling efficient retrieval based on semantic similarity.
def get_vectorstore(text_chunks):
    
    

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

    # TODO: Check if the vectorDB and messages are not present in the session state and initialize them to None.
    
    
    # A header with the text appears at the top of the Streamlit application.
    st.header("Generative AI Streaming Chat with Amazon Bedrock, Aurora PostgreSQL and pgvector :books::parrot:")
    subheader = '<p style="font-family:Calibri (Body); color:Grey; font-size: 16px;">Leverage Foundational Models from <a href="https://aws.amazon.com/bedrock/">Amazon Bedrock</a> and <a href="https://github.com/pgvector/pgvector">pgvector</a> as Vector Engine</p>'
    st.markdown(subheader, unsafe_allow_html=True)
    
    # A chat message can be associated with an AI assistant, a human or a system role. Here we are displaying the question (asked by the human) and the response (answered by the AI assistant) alternately.
    for msg in st.session_state.messages:
        if msg.type == "human":
            st.chat_message("Human: ").write(msg.content)
        if msg.type == "ai":
            st.chat_message("Assistant: ").write(msg.content)
    
    # TODO: The text that you give Claude is designed to elicit, or "prompt", a relevant output. A prompt is usually in the form of a question or instructions. 
    # When prompting Claude through the API, it is very important to use the correct \n\nHuman: and \n\nAssistant: formatting.
    # Claude was trained as a conversational agent using these special tokens to mark who is speaking. 
    # The \n\nHuman: (you) asks a question or gives instructions, and the\n\nAssistant: (Claude) responds.
    
    
    
    
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
    
    
    # TODO: Define the Bedrock client
    
    
    
    # TODO: Define the Embedding model using the Bedrock client
    
    
    
    # TODO: Create the connection string for pgvector from .env file.
    
    
                                       
)

main()
