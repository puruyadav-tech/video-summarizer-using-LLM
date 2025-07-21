import streamlit as st
import google.generativeai as genai
# Corrected import for get_transcript and the exceptions
from youtube_transcript_api import get_transcript
from youtube_transcript_api.exceptions import TranscriptsDisabled, NoTranscriptFound # Corrected import path for exceptions
import re # Import the re module for regular expressions

# Configure the Google Generative AI library with your API key
# IMPORTANT: For deployment, ensure you've added GEMINI_API_KEY to Streamlit Secrets.
# For local testing, create a .streamlit folder in your app's root directory
# and inside it, create a secrets.toml file with:
# GEMINI_API_KEY = "your_api_key_here"
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except KeyError: # Changed AttributeError to KeyError as it's more appropriate for missing secret
    st.error("Gemini API Key not found in Streamlit Secrets. Please add it to your app's secrets.")
    st.stop() # Stop the app if the API key is not configured

# Define the prompt for the YouTube video summarizer
prompt = """You are a YouTube video summarizer. You will be taking the transcript text
and summarizing the entire video and providing the important summary in points
within 250 words. Please provide the summary of the text given here: """

## Function to get the transcript data from YouTube videos
@st.cache_data # Cache the transcript to avoid re-fetching on rerun
def extract_transcript_details(youtube_video_url):
    """
    Extracts the transcript from a given YouTube video URL.

    Args:
        youtube_video_url (str): The URL of the YouTube video.

    Returns:
        str: The concatenated transcript text.
    """
    try:
        # Improved regex to extract video ID from various YouTube URL formats
        video_id_match = re.search(r'(?:v=|youtu\.be\/|http:\/\/googleusercontent\.com\/youtube\.com\/\d+)([a-zA-Z0-9_-]{11})', youtube_video_url)
        if not video_id_match:
            raise ValueError("Invalid YouTube URL format provided. Please use a valid YouTube link.")
        video_id = video_id_match.group(1)

        # Corrected call: Directly use get_transcript function
        transcript_list = get_transcript(video_id)

        # Concatenate all transcript parts into a single string
        transcript = " ".join([item["text"] for item in transcript_list])
        return transcript

    except TranscriptsDisabled:
        # Specific error for disabled transcripts
        raise Exception("Transcripts are disabled for this video by the uploader.")
    except NoTranscriptFound:
        # Specific error for no transcript found (e.g., no English transcript)
        raise Exception("No English transcript found for this video.")
    except Exception as e:
        # Catch any other potential errors from YouTubeTranscriptApi
        raise Exception(f"Failed to fetch transcript: {e}")

## Function to generate the summary based on Prompt from Google Gemini Pro
def generate_gemini_content(transcript_text: str, prompt_text: str) -> str:
    """
    Generates a summary of the given transcript text using the Google Gemini Pro model.

    Args:
        transcript_text (str): The video transcript to summarize.
        prompt_text (str): The prompt to guide the summarization.

    Returns:
        str: The generated summary.
    """
    # Initialize the Gemini model with 'gemini-2.0-flash'
    model = genai.GenerativeModel("gemini-2.0-flash")
    try:
        # Generate content by combining the prompt and the transcript
        response = model.generate_content(prompt_text + transcript_text)
        return response.text
    except Exception as e:
        # Catch any errors from the Gemini API call
        raise Exception(f"Gemini API call failed: {e}")

# --- Streamlit UI Components ---
st.set_page_config(page_title="YouTube Video Summarizer", layout="centered", icon="📹")

st.markdown("<h1 style='text-align: center;'>📹 YouTube Video Summarizer</h1>", unsafe_allow_html=True)
st.markdown("Enter a YouTube video link below to get a detailed summary of its transcript.")
st.markdown("---")

# Input field for the YouTube link
youtube_link = st.text_input(
    "Enter YouTube Video Link:",
    placeholder="e.g., https://www.youtube.com/watch?v=VIDEO_ID234567890 or https://www.youtube.com/watch?v=VIDEO_ID",
    help="Supports standard YouTube links and shortened Googleusercontent links."
)

# Button to trigger the summary generation
if st.button("Get Summary", use_container_width=True):
    if not youtube_link:
        st.warning("Please enter a YouTube video link to get a summary.")
    else:
        # Use a spinner to indicate that processing is ongoing
        with st.spinner("Fetching transcript and generating summary... This may take a moment."):
            try:
                # 1. Extract Transcript
                transcript_text = extract_transcript_details(youtube_link)
                st.success(f"Transcript fetched successfully. Length: {len(transcript_text)} characters.")

                # 2. Generate Summary using Gemini
                summary = generate_gemini_content(transcript_text, prompt)

                st.markdown("---")
                st.subheader("Detailed Notes:")
                # Display the summary as Markdown for better formatting (points, etc.)
                st.markdown(summary)

            except Exception as e:
                # Centralized error handling for all potential issues
                st.error(f"Error: Could not process video or generate summary. {e}")
                if "No English transcript found" in str(e):
                    st.info("This video might not have English transcripts available, or the language is not supported by default.")
                elif "Transcripts are disabled" in str(e):
                    st.info("Transcripts are disabled for this video by the uploader.")
                elif "Invalid YouTube URL" in str(e):
                    st.warning("Please ensure the YouTube URL is valid and correctly formatted. Examples: `https://www.youtube.com/watch?v=YOUR_ID` or `http://googleusercontent.com/youtube.com/YOUR_ID`.")
                elif "403" in str(e) or "429" in str(e) or "API rate limit exceeded" in str(e):
                    st.error("API rate limit exceeded or access denied. Please check your API key or try again later.")
                elif "400" in str(e) and "Gemini API call failed" in str(e):
                    st.error("Bad request to Gemini API. The video transcript might be too long for the model, or there's an issue with the prompt. Try a shorter video.")
                else:
                    st.error("An unexpected error occurred. Please check the video link and your internet connection.")

st.markdown("---")
st.caption("Powered by Google Gemini and YouTube Transcript API")
