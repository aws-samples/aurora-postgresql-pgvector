import streamlit as st

def init_session():
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    if 'token' not in st.session_state:
        st.session_state['token'] = ""
    if 'page' not in st.session_state:
        st.session_state['page'] = 'login'
    if 'guest_mode' not in st.session_state:
        st.session_state['guest_mode'] = False
    if 'verifying' not in st.session_state:
        st.session_state['verifying'] = False
    if 'email' not in st.session_state:
        st.session_state['email'] = ""
    if 'password' not in st.session_state:
        st.session_state['password'] = ""
    if 'extra_input_params' not in st.session_state:
        st.session_state['extra_input_params'] = {}
        
def reset_session():
    st.session_state['authenticated'] = False
    st.session_state['page'] = 'login'
    st.session_state['guest_mode'] = False
    st.session_state['verifying'] = False
    st.session_state['otp'] = ""
    st.session_state['email'] = ""
    st.session_state['password'] = ""
    st.session_state['signup_error'] = ""
    
