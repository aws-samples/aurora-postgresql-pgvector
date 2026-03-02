import streamlit as st 
import chatbot as chatbot
from langchain.memory import ConversationBufferWindowMemory

st.set_page_config(page_title="AuroraML ChatBot")
st.title("AuroraML ChatBot") 

if 'memory' not in st.session_state:
    st.session_state.memory = ConversationBufferWindowMemory(memory_key="chat_history", return_messages=True) 

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

#Re-render the chat history (Streamlit re-runs this script, so need this to preserve previous chat messages)
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["text"]) 

input_text = st.chat_input("Enter your question here")

if input_text:
    
    with st.chat_message("user"): 
        st.markdown(input_text)
    
    st.session_state.chat_history.append({"role":"user", "text":input_text}) 
    
    chat_response = chatbot.ask_question(input_text)
    
    with st.chat_message("assistant"): 
        st.markdown(chat_response)
    
    st.session_state.chat_history.append({"role":"assistant", "text":chat_response}) 
    

        
