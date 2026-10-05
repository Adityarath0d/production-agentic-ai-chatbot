import json
from itertools import chain
import time

import requests
import streamlit as st

BACKEND_URL = "http://localhost:8000"
DEFAULT_TITLE = "New chat"  # must match the backend's DEFAULT_TITLE

st.title("Agentic Chatbot")


# ---------- backend helpers ----------
def api_list_threads():
    r = requests.get(f"{BACKEND_URL}/threads", timeout=10)
    r.raise_for_status()
    return r.json()


def api_create_thread():
    r = requests.post(f"{BACKEND_URL}/threads", timeout=10)
    r.raise_for_status()
    return r.json()


def api_get_messages(thread_id: str):
    r = requests.get(f"{BACKEND_URL}/threads/{thread_id}/messages", timeout=10)
    r.raise_for_status()
    return r.json()


def api_delete_thread(thread_id: str):
    r = requests.delete(f"{BACKEND_URL}/threads/{thread_id}", timeout=10)
    r.raise_for_status()


def stream_reply(thread_id: str, message: str):
    """Generator: yields text pieces from the backend's SSE stream."""
    with requests.post(
        f"{BACKEND_URL}/chat/stream",
        json={"thread_id": thread_id, "message": message},
        stream=True,
        timeout=(5, 60),
    ) as response:
        response.raise_for_status()
        response.encoding = "utf-8"
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            payload = json.loads(line[len("data: "):])
            content = payload.get("content")
            if content:
                yield content


# ---------- startup: load chats, pick the active one ----------
try:
    threads = api_list_threads()
    if "thread_id" not in st.session_state:
        if threads:
            st.session_state.thread_id = threads[0]["id"]  # backend sorts newest first
        else:
            st.session_state.thread_id = api_create_thread()["id"]
            threads = api_list_threads()  # refresh: the list was empty a moment ago
        st.session_state.messages = api_get_messages(st.session_state.thread_id)
except requests.RequestException:
    st.error(f"Can't reach the backend at {BACKEND_URL}. Is it running?")
    st.stop()


# ---------- sidebar ----------
with st.sidebar:
    st.header("Chats")

    if st.button("➕ New chat", use_container_width=True):
        st.session_state.thread_id = api_create_thread()["id"]
        st.session_state.messages = []
        st.rerun()

    for t in threads:
        is_active = t["id"] == st.session_state.thread_id
        col_title, col_del = st.columns([5, 1])

        with col_title:
            if st.button(
                t["title"],
                key=t["id"],
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.thread_id = t["id"]
                st.session_state.messages = api_get_messages(t["id"])
                st.rerun()

        with col_del:
            if st.button("🗑", key=f"del-{t['id']}"):
                api_delete_thread(t["id"])
                if is_active:
                    remaining = api_list_threads()
                    if remaining:
                        st.session_state.thread_id = remaining[0]["id"]
                    else:
                        st.session_state.thread_id = api_create_thread()["id"]
                    st.session_state.messages = api_get_messages(
                        st.session_state.thread_id
                    )
                st.rerun()


# ---------- conversation ----------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("Type a message")

if user_input:
    with st.chat_message("user"):
        st.write(user_input)

    succeeded = False
    try:
        with st.chat_message("assistant"):
            stream = stream_reply(st.session_state.thread_id, user_input)

            with st.spinner("Thinking..."):
                first_chunk = next(stream, None)

            if first_chunk is None:
                st.warning("The assistant returned an empty response.")
            else:
                reply = st.write_stream(chain([first_chunk], stream))
                st.session_state.messages.append({"role": "user", "content": user_input})
                st.session_state.messages.append({"role": "assistant", "content": reply})
                succeeded = True

    except requests.Timeout:
        st.error("The backend took too long to respond. Try again.")
    except requests.ConnectionError:
        st.error(f"Can't reach the backend at {BACKEND_URL}. Is it running?")
    except requests.HTTPError as e:
        st.error(f"Backend returned an error: {e.response.status_code}")
    except ValueError:
        st.error("Backend sent a malformed stream event.")

        if succeeded:
            active = next(
                (t for t in threads if t["id"] == st.session_state.thread_id), None
            )
            # Only a chat that's still untitled is waiting for a title
            if active and active["title"] == DEFAULT_TITLE:
                for _ in range(12):  # up to about 6 seconds
                    time.sleep(0.5)
                    try:
                        latest = api_list_threads()
                    except requests.RequestException:
                        break
                    current = next(
                        (t for t in latest if t["id"] == st.session_state.thread_id), None
                    )
                    if current and current["title"] != DEFAULT_TITLE:
                        break
            st.rerun()