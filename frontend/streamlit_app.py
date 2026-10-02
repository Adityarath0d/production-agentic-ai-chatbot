# frontend/streamlit_app.py
import json
import uuid

import requests
import streamlit as st

BACKEND_URL = "http://localhost:8000"

st.title("Agentic Chatbot")

# --- Session state (initialized once per browser session) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())


#--------------------------- streaming functionality --------------------------
def stream_reply(thread_id: str, message: str):
    """Generator: yields text pieces from the backend's SSE stream."""
    
    with requests.post(
        f"{BACKEND_URL}/chat/stream",
        json={"thread_id": thread_id, "message": message},
        stream=True,
        timeout=(5, 60),  # (connect timeout, max silence between chunks)
    ) as response:
        response.raise_for_status()
        response.encoding = "utf-8"  # requests defaults to ISO-8859-1 otherwise

        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            payload = json.loads(line[len("data: "):])
            content = payload.get("content")
            if content:
                yield content

#------------------------- Side Bar ----------------------------------------------------
with st.sidebar:
    
    st.title("🤖 AI Assistant")

    if st.button("💬 New Chat", use_container_width=True):
        st.session_state.messages = []

    if st.button("📜 Chat History", use_container_width=True):
        st.session_state.show_history = True

    if st.button("⚙️ Settings", use_container_width=True):
        st.session_state.show_settings = True

    st.divider()

    st.caption("Production Agentic AI Chatbot")

# --- Re-render full history on every rerun ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- Handle new input ---
user_input = st.chat_input("Type a message")

if user_input:
    with st.chat_message("user"):
        st.write(user_input)

    try:
        with st.chat_message("assistant"):
            reply = st.write_stream(
                stream_reply(st.session_state.thread_id, user_input)
            )

        # Success: commit both sides of the turn together
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.messages.append({"role": "assistant", "content": reply})

    except requests.Timeout:
        st.error("The backend took too long to respond. Try again.")
    except requests.ConnectionError:
        st.error(f"Can't reach the backend at {BACKEND_URL}. Is it running?")
    except requests.HTTPError as e:
        st.error(f"Backend returned an error: {e.response.status_code}")
    except ValueError:
        st.error("Backend sent a malformed stream event.")