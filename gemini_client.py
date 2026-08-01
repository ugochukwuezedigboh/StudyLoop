"""
Handles Gemini API configuration and the low-level calls used across the app:
audio transcription, summarization, insight extraction, and question generation.

Uses the current `google-genai` SDK, which supports both the legacy
AIza... "Standard" key format and the newer AQ.Ab... "Auth" key format
that Google AI Studio issues as of mid-2026. The older `google-generativeai`
package this originally used has been fully deprecated by Google and does
not support the new key format.
"""

import os
import time
import streamlit as st
from google import genai
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


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


def _get_client() -> genai.Client:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "No Gemini API key found. Add one in the sidebar, or set "
            "GEMINI_API_KEY in a .env file / Streamlit secrets."
        )
    return genai.Client(api_key=api_key)


def transcribe_audio(file_path: str, mime_type: str | None = None) -> str:
    """Upload an audio file to Gemini and return a clean transcript."""
    client = _get_client()
    if mime_type:
        audio_file = client.files.upload(file=file_path, config={"mime_type": mime_type})
    else:
        audio_file = client.files.upload(file=file_path)

    # Wait for the file to finish processing on Google's side.
    while audio_file.state == "PROCESSING":
        time.sleep(1.5)
        audio_file = client.files.get(name=audio_file.name)

    if audio_file.state == "FAILED":
        raise RuntimeError("Audio upload failed processing on Gemini's side.")

    prompt = (
        "Transcribe this recording word-for-word. Add speaker labels only if "
        "multiple distinct speakers are clearly audible (Speaker 1, Speaker 2, "
        "etc). Do not summarize, do not add commentary — just the transcript, "
        "cleaned of filler sounds like 'um' and 'uh' but keeping the actual words."
    )
    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents=[prompt, audio_file],
    )

    try:
        client.files.delete(name=audio_file.name)
    except Exception:
        pass

    return response.text.strip()


def generate_summary(transcript: str) -> str:
    client = _get_client()
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
    response = client.models.generate_content(model=DEFAULT_MODEL, contents=prompt)
    return response.text.strip()


def generate_insights(transcript: str) -> str:
    client = _get_client()
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
    response = client.models.generate_content(model=DEFAULT_MODEL, contents=prompt)
    return response.text.strip()


def generate_questions(transcript: str, num_questions: int, q_format: str, difficulty: str) -> str:
    client = _get_client()

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
    response = client.models.generate_content(model=DEFAULT_MODEL, contents=prompt)
    return response.text.strip()


def generate_multiple_choice_questions(transcript: str, num_questions: int, difficulty: str) -> str:
    """Generates multiple-choice-only practice questions (used by the
    dedicated 'Multiple choice only' button)."""
    client = _get_client()
    prompt = f"""Based on the transcript below, write {num_questions} multiple-choice
exam-style practice questions at a {difficulty.lower()} difficulty level.

Each question should have 4 labeled options (A-D), with the correct answer
marked clearly at the end of that question as 'Answer: X'. Number the
questions. Return only the questions and answers in Markdown — no preamble.

Transcript:
\"\"\"
{transcript}
\"\"\"
"""
    response = client.models.generate_content(model=DEFAULT_MODEL, contents=prompt)
    return response.text.strip()
