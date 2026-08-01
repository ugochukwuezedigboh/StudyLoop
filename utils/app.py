import mimetypes
import os
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from audio_recorder_streamlit import audio_recorder

from utils import gemini_client as gc
from utils import document_parser as dp
from utils import export

st.set_page_config(
    page_title="StudyLoop — Lecture & Meeting Notes AI",
    page_icon="🎓",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
defaults = {
    "transcript": "",
    "summary": "",
    "insights": "",
    "questions": "",
    "title": "",
    "audio_bytes": None,
    "audio_filename": None,
    "document_filename": None,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


def process_document_upload(uploaded_file):
    if not uploaded_file:
        return

    try:
        document_text = dp.extract_document_text(uploaded_file)
        if not document_text.strip():
            st.error("The document contains no extractable text.")
            return

        st.session_state["transcript"] = document_text
        st.session_state["audio_bytes"] = None
        st.session_state["audio_filename"] = None
        st.session_state["document_filename"] = uploaded_file.name
        st.success("Document text extracted. You can edit it below or generate study material.")
    except Exception as e:
        st.error(f"Failed to extract document text: {e}")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🎓 StudyLoop")
    st.caption("Record it. Understand it. Get quizzed on it.")

    st.divider()
    st.subheader("Setup")

    if not gc.is_configured():
        key_input = st.text_input(
            "Gemini API key",
            type="password",
            help="Get a free key at https://aistudio.google.com/apikey. "
                 "Not stored anywhere except this browser session.",
        )
        if key_input:
            st.session_state["gemini_api_key"] = key_input
            st.rerun()
        st.info("Add a Gemini API key to get started.")
    else:
        st.success("Gemini API connected")

    st.divider()
    st.subheader("Question settings")
    num_questions = st.slider("Number of questions", 3, 20, 8)
    q_format = st.selectbox(
        "Format",
        ["Mixed", "Multiple choice", "Short answer", "Essay / long answer"],
    )
    difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"], index=1)

    st.divider()
    if st.button("🗑️ Clear session", use_container_width=True):
        for key, val in defaults.items():
            st.session_state[key] = val
        st.rerun()

    st.caption("Works from any browser — desktop or mobile. Nothing is "
               "saved after you close the tab, so download your notes "
               "before you leave.")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("StudyLoop")
st.caption(
    "Record a lecture or meeting, get a clean transcript, an organized "
    "summary, the key insights worth remembering, and practice questions "
    "to test yourself before an exam."
)

if not gc.is_configured():
    st.warning(
        "👈 Add your Gemini API key in the sidebar to enable transcription and AI generation. "
        "You can still upload a document now."
    )

# ---------------------------------------------------------------------------
# Step 1 — Capture audio
# ---------------------------------------------------------------------------
st.header("1. Capture the recording")

st.caption("Record in browser, upload an audio file, or upload a document below.")

tab_record, tab_upload, tab_doc = st.tabs([
    "🎙️ Record in browser",
    "📁 Upload audio file",
    "📄 Upload document",
])

with tab_record:
    st.caption("Works on desktop and mobile browsers with microphone access.")
    recorded = audio_recorder(
        text="Click to record",
        recording_color="#e63946",
        neutral_color="#457b9d",
        icon_size="2x",
        key="audio_recorder",
        pause_threshold=60.0,
    )
    if recorded:
        st.session_state["audio_bytes"] = recorded
        st.session_state["audio_filename"] = "recording.wav"
        st.session_state["document_filename"] = None
        st.audio(recorded, format="audio/wav")

with tab_upload:
    uploaded = st.file_uploader(
        "Upload an audio file",
        type=["mp3", "wav", "m4a", "ogg", "flac", "aac"],
        key="audio_upload",
    )
    if uploaded:
        st.session_state["audio_bytes"] = uploaded.read()
        st.session_state["audio_filename"] = uploaded.name
        st.session_state["document_filename"] = None
        st.audio(st.session_state["audio_bytes"])

with tab_doc:
    doc_file = st.file_uploader(
        "Upload a PDF or Word document",
        type=["pdf", "docx"],
        key="doc_upload",
    )
    if doc_file:
        process_document_upload(doc_file)

if st.session_state["audio_bytes"]:
    st.success("Audio loaded. Click Transcribe to continue.")
elif st.session_state["document_filename"]:
    st.success("Document text loaded. Edit it below or generate study material.")
else:
    st.info("First record, upload audio, or upload a document to begin.")

title = st.text_input(
    "Give this recording a title",
    value=st.session_state["title"] or "Untitled recording",
    key="title_input",
)
st.session_state["title"] = title

# ---------------------------------------------------------------------------
# Step 2 — Transcribe
# ---------------------------------------------------------------------------
st.header("2. Transcribe")

col_a, col_b = st.columns([1, 3])
with col_a:
    if st.session_state["audio_bytes"]:
        transcribe_clicked = st.button(
            "📝 Transcribe audio",
            type="primary",
            key="transcribe_button",
            use_container_width=True,
            disabled=not gc.is_configured(),
        )
    else:
        transcribe_clicked = False

if st.session_state["audio_bytes"]:
    if transcribe_clicked:
        with st.spinner("Transcribing — this can take a moment for longer recordings..."):
            try:
                suffix = Path(st.session_state.get("audio_filename", "recording.wav")).suffix or ".wav"
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(st.session_state["audio_bytes"])
                    tmp_path = tmp.name
                mime_type, _ = mimetypes.guess_type(tmp_path)
                st.session_state["transcript"] = gc.transcribe_audio(tmp_path, mime_type=mime_type)
                os.unlink(tmp_path)
                st.success("Transcription complete.")
            except Exception as e:
                st.error(f"Transcription failed: {e}")
else:
    if st.session_state["document_filename"] and not st.session_state["transcript"]:
        st.info("Document text has been loaded; skip transcription and generate study material below.")
    elif not st.session_state["document_filename"]:
        st.info("Upload audio or a document to begin.")

if st.session_state["transcript"]:
    st.session_state["transcript"] = st.text_area(
        "Transcript / document text (editable — fix any errors before generating notes)",
        value=st.session_state["transcript"],
        height=220,
    )

# ---------------------------------------------------------------------------
# Step 3 — Generate study material
# ---------------------------------------------------------------------------
st.header("3. Generate study material")

gen_col1, gen_col2, gen_col3 = st.columns(3)
has_transcript = bool(st.session_state["transcript"].strip())

with gen_col1:
    if st.button(
        "📋 Summary",
        disabled=not gc.is_configured() or not has_transcript,
        use_container_width=True,
        key="summary_button",
    ):
        with st.spinner("Summarizing..."):
            try:
                st.session_state["summary"] = gc.generate_summary(st.session_state["transcript"])
            except Exception as e:
                st.error(f"Couldn't generate summary: {e}")

with gen_col2:
    if st.button(
        "💡 Key insights",
        disabled=not gc.is_configured() or not has_transcript,
        use_container_width=True,
        key="insights_button",
    ):
        with st.spinner("Pulling out key insights..."):
            try:
                st.session_state["insights"] = gc.generate_insights(st.session_state["transcript"])
            except Exception as e:
                st.error(f"Couldn't generate insights: {e}")

with gen_col3:
    if st.button(
        "❓ Practice questions",
        disabled=not gc.is_configured() or not has_transcript,
        use_container_width=True,
        key="practice_questions",
    ):
        with st.spinner("Writing practice questions..."):
            try:
                st.session_state["questions"] = gc.generate_questions(
                    st.session_state["transcript"], num_questions, q_format, difficulty
                )
            except Exception as e:
                st.error(f"Couldn't generate questions: {e}")

if any([st.session_state["summary"], st.session_state["insights"], st.session_state["questions"]]):
    tab_sum, tab_ins, tab_q = st.tabs(["Summary", "Key Insights", "Practice Questions"])
    with tab_sum:
        st.markdown(st.session_state["summary"] or "_Not generated yet._")
    with tab_ins:
        st.markdown(st.session_state["insights"] or "_Not generated yet._")
    with tab_q:
        st.markdown(st.session_state["questions"] or "_Not generated yet._")

# ---------------------------------------------------------------------------
# Step 4 — Export
# ---------------------------------------------------------------------------
st.header("4. Export your study pack")

has_any_content = any([
    st.session_state["summary"], st.session_state["insights"],
    st.session_state["questions"], st.session_state["transcript"],
])

if has_any_content:
    md_content = export.build_markdown(
        st.session_state["title"],
        st.session_state["transcript"],
        st.session_state["summary"],
        st.session_state["insights"],
        st.session_state["questions"],
    )
    safe_name = "".join(c if c.isalnum() or c in " -_" else "" for c in st.session_state["title"]).strip() or "study-pack"
    date_stamp = datetime.now().strftime("%Y-%m-%d")

    col_md, col_pdf = st.columns(2)
    with col_md:
        st.download_button(
            "⬇️ Download as Markdown",
            data=md_content,
            file_name=f"{safe_name}-{date_stamp}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col_pdf:
        try:
            pdf_bytes = export.build_pdf(
                st.session_state["title"],
                st.session_state["transcript"],
                st.session_state["summary"],
                st.session_state["insights"],
                st.session_state["questions"],
            )
            st.download_button(
                "⬇️ Download as PDF",
                data=pdf_bytes,
                file_name=f"{safe_name}-{date_stamp}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.caption(f"PDF export unavailable: {e}")
else:
    st.caption("Generate a summary, insights, or questions above to unlock export.")
