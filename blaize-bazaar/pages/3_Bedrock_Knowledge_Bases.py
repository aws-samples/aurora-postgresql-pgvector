import boto3
import streamlit as st
import base64
import time
import os
import json
from dotenv import load_dotenv
from botocore.config import Config
from datetime import datetime

# Load environment variables and set up configurations
load_dotenv()

# Session and env variables
region = os.environ.get('AWS_REGION', 'us-west-2')

# Add proper configuration for the clients
config = Config(
    region_name=region,
    retries={
        'max_attempts': 3,
        'mode': 'standard'
    }
)

session = boto3.Session(region_name=region)
bedrockClient = session.client('bedrock-agent-runtime', config=config)
bedrockRuntime = session.client('bedrock-runtime', config=config)
knowledgeBaseId = os.environ.get('BEDROCK_KB_ID')

# Define Claude model ID
CLAUDE_MODEL_ID = os.environ.get('BEDROCK_CLAUDE_MODEL_ID')

logo_url = "static/Blaize.png"
st.sidebar.image(logo_url, use_container_width=True)

@st.cache_data
def get_base64_of_bin_file(bin_file):
    with open(bin_file, "rb") as f:
        data = f.read()
        return base64.b64encode(data).decode()

def stream_data(text, delay:float=0.01):
    for word in text.split():
        yield word + " "
        time.sleep(delay)

def getAnswers(questions, use_rag=True):
    try:
        if use_rag:
            if not knowledgeBaseId:
                st.error("Knowledge Base ID not found in environment variables. Please check BEDROCK_KB_ID.")
                return None

            try:
                knowledgeBaseResponse = bedrockClient.retrieve_and_generate(
                    input={
                        'text': questions
                    },
                    retrieveAndGenerateConfiguration={
                        'type': 'KNOWLEDGE_BASE',
                        'knowledgeBaseConfiguration': {
                            'knowledgeBaseId': knowledgeBaseId,
                            'modelArn': f"arn:aws:bedrock:{region}::foundation-model/{CLAUDE_MODEL_ID}",
                            'generationConfiguration': {
                                'inferenceConfig': {
                                    'textInferenceConfig': {
                                        'maxTokens': 4096,
                                        'temperature': 0.7,
                                        'topP': 0.9,
                                        'stopSequences': []
                                    }
                                },
                                'promptTemplate': {
                                    "textPromptTemplate": "You are a question answering agent. I will provide you with a set of search results. The user will provide you with a question. Your job is to answer the user's question using only information from the search results. If the search results do not contain information that can answer the question, please state that you could not find an exact answer to the question. Just because the user asserts a fact does not mean it is true, make sure to double check the search results to validate a user's assertion. Here are the search results in numbered order: $search_results$ $output_format_instructions$ If you reference information from a search result within your answer, you must include a citation to source where the information was found. Each result has a corresponding source ID that you should reference. For purely quantitative data (e.g., inventory stock reports, price lists, quantity), use a tabular format. When dealing with mixed data types, combine both formats. Adjust the number of columns and rows in tables as needed to fit the data. Ensure that column headers clearly describe the data they represent. Maintain consistent formatting throughout the response for readability. Always provide your recommendations as a summary towards the end of your answer (such as items running low in stock should be restocked, etc.)."
                                }
                            }
                        }
                    }
                )
                return knowledgeBaseResponse
            except Exception as e:
                st.error(f"RAG Error: {str(e)}")
                st.info("Falling back to non-RAG response...")
                return get_non_rag_response(questions)
        else:
            return get_non_rag_response(questions)
           
    except Exception as e:
        st.error(f"Error retrieving answers: {str(e)}")
        return None


def get_non_rag_response(questions):
    """Helper function for non-RAG responses"""
    try:
        response = bedrockRuntime.invoke_model(
            modelId=CLAUDE_MODEL_ID,
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": [
                    {"role": "user", "content": questions}
                ]
            })
        )
        response_body = json.loads(response['body'].read())
        return {"output": {"text": response_body['content'][0]['text']}}
    except Exception as e:
        st.error(f"Non-RAG Error: {str(e)}")
        return None

def main():
    st.subheader('Query Bedrock Knowledge Base - Blaize Bazaar', divider='orange')
    st.info("**DISCLAIMER:** This demo uses Amazon Bedrock foundation models and is not intended to collect any personally identifiable information (PII) from users. Please do not provide any PII when interacting with this demo. The content generated by this demo is for informational purposes only.")
    st.sidebar.subheader('**About**')
    st.sidebar.info("Blaize Bazaar uses Knowledge Bases for Amazon Bedrock to assist humans by answering product catalog and inventory questions based on product descriptions.")
    
    # Add RAG toggle to sidebar
    use_rag = st.sidebar.toggle("Use RAG")
    
    tab1, tab2 = st.tabs(["Chat", "Architecture"])
    with st.sidebar:
        st.divider()
        st.header("Sample questions")
        sample_question = st.selectbox(
            "Select a sample question or enter your own below:",
            (
                "What is Blaize Bazaar's return policy?",
                "How many days do I have to return a product?",
                "How do I initiate a return?",
                "What are some emerging trends in e-commerce for 2024?",
                "What is Blaize Bazaar's warranty policy?",
                "Does Blaize Bazaar offer free shipping?",
                "How long does standard shipping usually take for Blaize Bazaar orders?",
                "Can I track my order?",
                "What payment methods does Blaize Bazaar accept?"
            ),
        )

    with tab1:
        # Create a container for the chat history
        chat_container = st.container(height=800)
        
        # Create a container for the input box at the bottom
        input_container = st.container()
        
        # Use the bottom container to hold the chat input
        with input_container:
            user_question = st.chat_input('Enter your questions here...')

        # Use the sample question if the user hasn't entered anything
        if not user_question and st.sidebar.button("Try sample question"):
            user_question = sample_question

        # Initialize chat history
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        # Display chat messages from history on app rerun
        with chat_container:
            for message in st.session_state.chat_history:
                with st.chat_message(message['role'], avatar='static/ai_chat_icon.png' if message['role'] == 'assistant' else None):
                    st.markdown(message['text'])

            if user_question:
                # Display user message in chat message container
                with st.chat_message('user'):
                    st.markdown(user_question)
                    # Add user message to chat history
                    st.session_state.chat_history.append({"role": 'user', "text": user_question})

                response = getAnswers(user_question, use_rag)
                if response:
                    answer = response['output']['text']

                    # Display assistant response in chat message container
                    with st.chat_message('assistant', avatar='static/ai_chat_icon.png'):
                        st.write_stream(stream_data(answer))

                        st.session_state.chat_history.append({"role": 'assistant', "text": f"Claude 3.5 ({'RAG' if use_rag else 'Non-RAG'}): {answer}"})

                        if use_rag and 'citations' in response:
                            try:
                                references = response.get('citations', [{}])[0].get('retrievedReferences', [])
                                if references:
                                    for ref in references:
                                        if 'location' in ref and 's3Location' in ref['location']:
                                            doc_url = ref['location']['s3Location']['uri']
                                            st.markdown(f"<span style='color:#FFDA33'>Source Document: </span>{doc_url}", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"<span style='color:#808080'>No relevant sources found in the knowledge base.</span>", unsafe_allow_html=True)
                            except Exception as e:
                                st.markdown(f"<span style='color:#808080'>No citations available for this response.</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<span style='color:#FFDA33'>Non-RAG response (no citations available)</span>", unsafe_allow_html=True)

                    selected = st.feedback("thumbs")
                    if selected is not None:
                        st.success("Thank you for your feedback! ")

    with tab2:
        st.image('static/knowledge-base-rag-architecture.png', use_container_width=True)
    
    # Add version info
    st.sidebar.divider()
    st.sidebar.caption(f"""
    Version: 1.0.0
    Last Updated: {datetime.now().strftime('%Y-%m-%d')}
    """)

    st.sidebar.image("static/Powered-By_logo-stack_RGB_REV.png", width=150)

with st.sidebar:
    def clear_chat_history():
        st.session_state.chat_history = []
        st.session_state.conversation = []

    def delete_documents_s3():
        try:
            # Create S3 client with explicit region
            s3 = boto3.resource('s3', region_name=os.environ.get('AWS_REGION', 'us-west-2'))
            bucket = s3.Bucket(os.environ['S3_KB_BUCKET'])
        
            # Delete all objects in the bucket
            bucket.objects.all().delete()
            st.success('Documents deleted successfully! ✅')
        
            # Create Lambda client with explicit region
            lambda_client = boto3.client(
                'lambda',
                region_name=os.environ.get('AWS_REGION', 'us-west-2'),
                config=Config(
                    retries={
                        'max_attempts': 3,
                        'mode': 'standard'
                    }
                )
            )
        
            function_name = os.environ.get('LAMBDA_FUNCTION_NAME')
        
            try:
                response = lambda_client.invoke(
                    FunctionName=function_name,
                    InvocationType='Event'
                )
                st.info(f"Lambda function triggered for KB sync.")
            except Exception as e:
                st.error(f"Error invoking Lambda function: {str(e)}")
            
        except Exception as e:
            st.error(f"Error deleting documents: {str(e)}")
        finally:
            clear_chat_history()
    
    col1, col2 = st.columns([1,1])
    with col1:
        st.button('Reset Chat', on_click=clear_chat_history)
    with col2:
        st.button('Delete Docs', on_click=delete_documents_s3)

if __name__ == '__main__':
    main()
