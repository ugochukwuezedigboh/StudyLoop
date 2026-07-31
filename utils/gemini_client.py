"""
Handles Gemini API configuration and the low-level calls used across the app:
audio transcription, summarization, insight extraction, and question generation.
"""

import os
import time
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def get_api_key() -> str | None:
    """Look for the API key in Streamlit secrets, env vars, then session state
    (set via the sidebar input), in that order of preference."""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

    env_key = os.getenv("GEMINI_API_KEY")
    if env_key:
        return env_key

    return st.session_state.get("gemini_api_key")


def is_configured() -> bool:
    return bool(get_api_key())


def _get_model():
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "No Gemini API key found. Add one in the sidebar, or set "
            "GEMINI_API_KEY in a .env file / Streamlit secrets."
        )
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(DEFAULT_MODEL)


def transcribe_audio(file_path: str) -> str:
    """Upload an audio file to Gemini and return a clean transcript."""
    genai.configure(api_key=get_api_key())
    audio_file = genai.upload_file(path=file_path)

    # Wait for the file to finish processing on Google's side.
    while audio_file.state.name == "PROCESSING":
        time.sleep(1.5)
        audio_file = genai.get_file(audio_file.name)

    if audio_file.state.name == "FAILED":
        raise RuntimeError("Audio upload failed processing on Gemini's side.")

    model = _get_model()
    prompt = (
        "Transcribe this recording word-for-word. Add speaker labels only if "
        "multiple distinct speakers are clearly audible (Speaker 1, Speaker 2, "
        "etc). Do not summarize, do not add commentary — just the transcript, "
        "cleaned of filler sounds like 'um' and 'uh' but keeping the actual words."
    )
    response = model.generate_content([prompt, audio_file])

    try:
        genai.delete_file(audio_file.name)
    except Exception:
        pass

    return response.text.strip()


def generate_summary(transcript: str) -> str:
    model = _get_model()
    prompt = f"""You are helping a student review a lecture or meeting recording.
Read the transcript below and produce a clear, well-organized summary in Markdown.

Structure it as:
## Overview
2-3 sentences on what this recording covered.

## Main Points
Bulleted list of the core points, grouped under short subheadings if the
material has natural sections (topics, agenda items, etc).

## Action Items / Follow-ups
Anything that sounds like a task, deadline, or decision (skip this section
entirely if there genuinely aren't any).

Transcript:
\"\"\"
{transcript}
\"\"\"
"""
    return model.generate_content(prompt).text.strip()


def generate_insights(transcript: str) -> str:
    model = _get_model()
    prompt = f"""Read the transcript below and pull out the key insights a student
would want to remember. Return Markdown with:

## Key Concepts
The core ideas, terms, or definitions introduced, each with a one-line explanation.

## Important Details
Numbers, dates, names, formulas, or examples worth memorizing.

## Likely Exam-Worthy Points
The 3-6 points most likely to appear on a test, and briefly why.

Transcript:
\"\"\"
{transcript}
\"\"\"
"""
    return model.generate_content(prompt).text.strip()


def generate_questions(transcript: str, num_questions: int, q_format: str, difficulty: str) -> str:
    model = _get_model()

    format_instructions = {
        "Multiple choice": (
            "Each question should have 4 labeled options (A-D), with the correct "
            "answer marked clearly at the end of that question as 'Answer: X'."
        ),
        "Short answer": (
            "Each question should be answerable in 1-3 sentences. Provide a "
            "model answer directly below each question, prefixed with 'Answer:'."
        ),
        "Essay / long answer": (
            "Each question should require a paragraph-length response that "
            "tests understanding and synthesis, not recall. Provide 2-3 bullet "
            "points of what a strong answer would cover, prefixed with 'Key points:'."
        ),
        "Mixed": (
            "Vary the format across multiple choice, short answer, and one or "
            "two essay questions. Label each question with its type, and "
            "provide the answer or key points as appropriate for that type."
        ),
    }

    prompt = f"""Based on the transcript below, write {num_questions} exam-style
practice questions at a {difficulty.lower()} difficulty level, formatted as: {q_format}.

{format_instructions.get(q_format, "")}

Number the questions. Return only the questions and answers in Markdown —
no preamble.

Transcript:
\"\"\"
{transcript}
\"\"\"
"""
    return model.generate_content(prompt).text.strip()
