"""
Streamlit chat UI for the Strands-based incident-remediation agent.

Key differences from the classic Bedrock Agents lab:
- One Agent instance per browser session (st.session_state) — the agent's
  .messages list persists across turns, giving real multi-turn continuity.
- The classic lab creates a new uuid1 session ID on every button click, so
  context is lost between messages.
- Streaming is handled via agent.stream_async() + asyncio, showing tokens
  as they arrive rather than blocking until the full response is ready.
"""

from __future__ import annotations

import asyncio
import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Page config — must be the first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Aurora Incident Remediation (Strands)",
    page_icon="🛡",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Lazy import of agent to avoid re-initialising boto3 clients on every rerun
# ---------------------------------------------------------------------------
from agent import create_agent  # noqa: E402  (after st.set_page_config)


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

def _init_session() -> None:
    """Initialise session-state keys on first load."""
    if "agent" not in st.session_state:
        st.session_state.agent = create_agent()
    if "messages" not in st.session_state:
        # Display history: list of {"role": "user"|"assistant", "content": str}
        st.session_state.messages = []


_init_session()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _stream_response(prompt: str) -> str:
    """Stream agent response tokens and return the full text."""
    agent: object = st.session_state.agent
    full_text = ""
    placeholder = st.empty()
    async for event in agent.stream_async(prompt):
        if "data" in event:
            chunk = event["data"]
            if isinstance(chunk, str):
                full_text += chunk
                placeholder.markdown(full_text + "▌")
    placeholder.markdown(full_text)
    return full_text


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.title("Aurora Incident Remediation")
st.caption(
    "Powered by Strands Agents + Amazon Bedrock "
    f"({os.environ.get('BEDROCK_MODEL_ID', 'global.anthropic.claude-sonnet-5')})"
)

# Sidebar — configuration / session controls
with st.sidebar:
    st.header("Configuration")
    st.markdown(f"**Region:** `{os.environ.get('AWS_REGION', 'us-west-2')}`")
    st.markdown(f"**Model:** `{os.environ.get('BEDROCK_MODEL_ID', 'global.anthropic.claude-sonnet-5')}`")
    db_secret = os.environ.get("DB_SECRET_NAME", "(not set — uses {instance}-agent-secret pattern)")
    st.markdown(f"**DB secret:** `{db_secret}`")
    st.divider()
    st.markdown(
        "**Session continuity:** this agent keeps full conversation history "
        "in memory for the lifetime of this browser tab."
    )
    if st.button("Clear conversation", type="secondary"):
        # Reset both the display history and the agent's internal message list
        st.session_state.messages = []
        st.session_state.agent = create_agent()
        st.rerun()

# Render existing conversation
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
user_input = st.chat_input("Describe the incident or ask a question…")

if user_input:
    # Show user message immediately
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Stream assistant response
    with st.chat_message("assistant"):
        response_text = asyncio.run(_stream_response(user_input))

    # Append assistant turn to display history
    # (agent.messages already updated internally by Strands)
    st.session_state.messages.append({"role": "assistant", "content": response_text})
