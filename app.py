import streamlit as st
import sys
import os
from pathlib import Path

# Add backend to path so we can import gemini_client
sys.path.append(str(Path(__file__).parent / "backend"))
from gemini_client import GeminiAbletonClient

# --- Page Configuration ---
st.set_page_config(
    page_title="Text-To-Ableton",
    page_icon="🎹",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Custom Styling ---
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        color: #fafafa;
    }
    .stChatFloatingInputContainer {
        bottom: 20px;
    }
    h1 {
        background: linear-gradient(90deg, #ff4b4b, #ff8a8a);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        margin-bottom: 2rem;
    }
    .stChatMessage {
        border-radius: 12px;
        margin-bottom: 1rem;
    }
    /* Simple glassmorphism for titles/headers */
    .header-container {
        padding: 1.5rem;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        margin-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- App Logic ---

@st.cache_resource
def get_client():
    return GeminiAbletonClient()

def main():
    # Header Section
    st.markdown('<div class="header-container"><h1>Text-To-Ableton</h1></div>', unsafe_allow_html=True)

    # Initialize Session State for Chat
    if "messages" not in st.session_state:
        st.session_state.messages = []

    try:
        client = get_client()
    except Exception as e:
        st.error(f"Failed to initialize Gemini Client: {str(e)}")
        st.info("Please ensure GEMINI_API_KEY is set in your .env file.")
        return

    # Display Chat History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("Command Ableton Live..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Processing musical intent..."):
                try:
                    response = client.chat(prompt)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

if __name__ == "__main__":
    main()
