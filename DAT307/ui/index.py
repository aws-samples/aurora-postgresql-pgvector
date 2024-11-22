import streamlit as st
from page.login_page import login_page
from page.signup_page import signup_page
from page.pending_incidents import pending_incident_page
from page.all_incidents import all_incident_page
from utils.init_session import init_session, reset_session

init_session()

if st.session_state['authenticated'] and st.session_state['page'] == "pending_incidents":
    pending_incident_page()
elif st.session_state['authenticated'] and st.session_state['page'] == "all_incidents":
    all_incident_page()
else:
    print(st.session_state['page'])
    if st.session_state['page'] == 'login':
        reset_session()
        print("calling the login page")
        login_page()
    elif st.session_state['page'] == 'signup':
        print("calling the signup page")
        signup_page()
