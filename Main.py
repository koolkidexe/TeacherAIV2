import streamlit as st
import PyPDF2
import io
import requests
import json

# --- Configuration ---
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
ELEVENLABS_API_BASE_URL = "https://api.elevenlabs.io/v1/text-to-speech"

# --- Streamlit App Setup ---
st.set_page_config(layout="centered", page_title="PDF to Podcast")
st.title("PDF to Podcast 🎙️")

# --- Sidebar for API Keys ---
st.sidebar.header("API Keys")

# Initialize session state for API keys if they don't exist
if 'gemini_api_key' not in st.session_state:
    st.session_state.gemini_api_key = ""
if 'elevenlabs_api_key' not in st.session_state:
    st.session_state.elevenlabs_api_key = ""

st.session_state.gemini_api_key = st.sidebar.text_input(
    "Gemini API Key",
    value=st.session_state.gemini_api_key,
    type="password",
    help="Get your Gemini API Key from Google AI Studio."
)
st.session_state.elevenlabs_api_key = st.sidebar.text_input(
    "ElevenLabs API Key",
    value=st.session_state.elevenlabs_api_key,
    type="password",
    help="Get your ElevenLabs API Key from your ElevenLabs dashboard."
)

# --- Functions for API Calls ---

def extract_text_from_pdf(uploaded_file):
    """Extracts text from an uploaded PDF file."""
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            text += pdf_reader.pages[page_num].extract_text()
        return text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
        return None

def summarize_text_with_gemini(text, gemini_api_key):
    """Summarizes text using the Gemini API."""
    if not gemini_api_key:
        st.error("Gemini API Key is not provided. Please enter it in the sidebar.")
        return None

    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": f"Summarize the following PDF text without using any asterisks. Keep the summary concise and informative:\n\n{text}"
                    }
                ]
            }
        ]
    }

    try:
        with st.spinner("Summarizing with Gemini..."):
            response = requests.post(f"{GEMINI_API_URL}?key={gemini_api_key}", headers=headers, json=payload)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            result = response.json()

            if result and result.get("candidates") and result["candidates"][0].get("content") and result["candidates"][0]["content"].get("parts"):
                summary = result["candidates"][0]["content"]["parts"][0]["text"]
                return summary
            else:
                st.error("Gemini API did not return a valid summary. Response structure unexpected.")
                st.json(result) # Display full response for debugging
                return None
    except requests.exceptions.HTTPError as e:
        st.error(f"Gemini API Error: {e.response.status_code} - {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Gemini API Request Failed: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during Gemini summarization: {e}")
        return None

def text_to_speech_elevenlabs(text, elevenlabs_api_key, voice_id="21m00Tcm4obsnInGRB_v"): # Default to 'Adam' voice
    """Converts text to speech using the ElevenLabs API."""
    if not elevenlabs_api_key:
        st.error("ElevenLabs API Key is not provided. Please enter it in the sidebar.")
        return None

    headers = {
        "xi-api-key": elevenlabs_api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2", # A good general-purpose model
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    try:
        with st.spinner("Generating audio with ElevenLabs..."):
            response = requests.post(f"{ELEVENLABS_API_BASE_URL}/{voice_id}", headers=headers, json=payload)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            return response.content # Returns audio bytes
    except requests.exceptions.HTTPError as e:
        st.error(f"ElevenLabs API Error: {e.response.status_code} - {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"ElevenLabs API Request Failed: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during ElevenLabs text-to-speech: {e}")
        return None

# --- Main App Logic ---

uploaded_file = st.file_uploader(
    "Upload a PDF file",
    type=["pdf"],
    help="Drag and drop your PDF here, or click to browse.",
    accept_multiple_files=False
)

summarized_text = None

if uploaded_file is not None:
    st.success(f"PDF '{uploaded_file.name}' uploaded successfully!")

    # Read PDF as bytes
    pdf_bytes = io.BytesIO(uploaded_file.getvalue())

    # Extract text
    extracted_text = extract_text_from_pdf(pdf_bytes)

    if extracted_text:
        # st.subheader("Extracted Text (for debugging):")
        # st.text_area("PDF Content", extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text, height=200)

        # Summarize text
        if st.session_state.gemini_api_key:
            summarized_text = summarize_text_with_gemini(extracted_text, st.session_state.gemini_api_key)
            if summarized_text:
                st.subheader("Summarized Content:")
                st.write(summarized_text)
                st.session_state.last_summary = summarized_text # Store summary in session state
            else:
                st.session_state.last_summary = None
        else:
            st.warning("Please provide your Gemini API Key in the sidebar to summarize the PDF.")
    else:
        st.error("Could not extract text from the PDF. Please try a different file.")
        st.session_state.last_summary = None # Clear summary if extraction failed

# Text-to-Speech Section
if st.session_state.get('last_summary'):
    st.subheader("Convert Summary to Audio")
    if st.button("Generate Podcast Audio"):
        if st.session_state.elevenlabs_api_key:
            audio_bytes = text_to_speech_elevenlabs(st.session_state.last_summary, st.session_state.elevenlabs_api_key)
            if audio_bytes:
                st.audio(audio_bytes, format="audio/mpeg")
                st.success("Audio generated successfully! You can now listen to your podcast.")
        else:
            st.warning("Please provide your ElevenLabs API Key in the sidebar to generate audio.")
else:
    if uploaded_file and not summarized_text:
        st.info("Upload a PDF and ensure Gemini API key is provided to see the summary and generate audio.")
    elif not uploaded_file:
        st.info("Upload a PDF to get started!")

st.markdown("---")
st.markdown("Developed with Streamlit, Gemini API, and ElevenLabs API.")
