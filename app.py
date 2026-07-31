import os
import tempfile
from datetime import datetime

import streamlit as st
from audio_recorder_streamlit import audio_recorder

from utils import gemini_client as gc
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
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

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
    st.warning("👈 Add your Gemini API key in the sidebar to begin.")
    st.stop()

# ---------------------------------------------------------------------------
# Step 1 — Capture audio
# ---------------------------------------------------------------------------
st.header("1. Capture the recording")

tab_record, tab_upload = st.tabs(["🎙️ Record in browser", "📁 Upload a file"])

with tab_record:
    st.caption("Works on desktop and mobile browsers with microphone access.")
    recorded = audio_recorder(
        text="Click to record",
        recording_color="#e63946",
        neutral_color="#457b9d",
        icon_size="2x",
    )
    if recorded:
        st.session_state["audio_bytes"] = recorded
        st.audio(recorded, format="audio/wav")

with tab_upload:
    uploaded = st.file_uploader(
        "Upload an audio file",
        type=["mp3", "wav", "m4a", "ogg", "flac", "aac"],
    )
    if uploaded:
        st.session_state["audio_bytes"] = uploaded.read()
        st.audio(st.session_state["audio_bytes"])

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
    transcribe_clicked = st.button(
        "📝 Transcribe audio",
        type="primary",
        disabled=not st.session_state["audio_bytes"],
        use_container_width=True,
    )

if transcribe_clicked and st.session_state["audio_bytes"]:
    with st.spinner("Transcribing — this can take a moment for longer recordings..."):
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(st.session_state["audio_bytes"])
                tmp_path = tmp.name
            st.session_state["transcript"] = gc.transcribe_audio(tmp_path)
            os.unlink(tmp_path)
            st.success("Transcription complete.")
        except Exception as e:
            st.error(f"Transcription failed: {e}")

if st.session_state["transcript"]:
    st.session_state["transcript"] = st.text_area(
        "Transcript (editable — fix any errors before generating notes)",
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
    if st.button("📋 Summary", disabled=not has_transcript, use_container_width=True):
        with st.spinner("Summarizing..."):
            try:
                st.session_state["summary"] = gc.generate_summary(st.session_state["transcript"])
            except Exception as e:
                st.error(f"Couldn't generate summary: {e}")

with gen_col2:
    if st.button("💡 Key insights", disabled=not has_transcript, use_container_width=True):
        with st.spinner("Pulling out key insights..."):
            try:
                st.session_state["insights"] = gc.generate_insights(st.session_state["transcript"])
            except Exception as e:
                st.error(f"Couldn't generate insights: {e}")

with gen_col3:
    if st.button("❓ Practice questions", disabled=not has_transcript, use_container_width=True):
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
