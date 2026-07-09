import streamlit as st
import chatbot as chatbot

# Maximum number of prior turns (Human + Assistant pairs) to include in the
# history string sent to the in-database prompt template.
MAX_HISTORY_TURNS = 6

st.set_page_config(page_title="AuroraML ChatBot", layout="wide")
st.title("AuroraML ChatBot")

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Re-render the chat history (Streamlit re-runs this script, so need this to
# preserve previous chat messages).
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["text"])

input_text = st.chat_input("Enter your question here")

if input_text:

    with st.chat_message("user"):
        st.markdown(input_text)

    # Build the history string from the last MAX_HISTORY_TURNS * 2 messages
    # (each turn = one user message + one assistant message). Slice BEFORE
    # appending the current question — it goes in the <question> slot of the
    # prompt, not in <history>.
    history_messages = st.session_state.chat_history[-(MAX_HISTORY_TURNS * 2):]
    history_lines = [
        f"{'Human' if msg['role'] == 'user' else 'Assistant'}: {msg['text']}"
        for msg in history_messages
    ]
    history_string = "\n".join(history_lines)

    st.session_state.chat_history.append({"role": "user", "text": input_text})

    chat_response = chatbot.ask_question(input_text, chat_history=history_string)

    with st.chat_message("assistant"):
        st.markdown(chat_response)

    st.session_state.chat_history.append({"role": "assistant", "text": chat_response})
