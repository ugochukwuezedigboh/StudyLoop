# StudyLoop — Lecture & Meeting Notes AI

> Built for the **3MTT Showcase**.

Record a lecture or meeting, get a clean transcript, an organized summary,
the key insights worth remembering, and practice exam questions — all in
one browser tab, on any device.

## What it does

1. **Capture** — record straight from the browser mic, or upload an audio
   file (mp3/wav/m4a/ogg/flac/aac).
2. **Transcribe** — sends the audio to Gemini and returns an editable,
   cleaned-up transcript.
3. **Generate**
   - **Summary** — overview, main points, action items.
   - **Key insights** — core concepts, important details, likely exam points.
   - **Practice questions** — multiple choice, short answer, essay, or a mix,
     with adjustable count and difficulty.
4. **Export** — download the whole study pack as Markdown or PDF.

Nothing is stored server-side — everything lives in the browser session and
is gone once you close the tab, so encourage downloading before leaving.

**Live demo:** _add your Streamlit Cloud URL here once deployed_

## Submission materials

- `StudyLoop-Solution-Brief.pdf` — problem, solution, how it works, tech stack
- Pitch deck — in progress
- Demo video script — in progress

## Run it locally

```bash
git clone <your-repo-url>
cd lecture-notes-ai
pip install -r requirements.txt

cp .env.example .env
# then edit .env and paste in a free key from https://aistudio.google.com/apikey

streamlit run app.py
```

Open the local URL Streamlit prints (usually `http://localhost:8501`).
Alternatively, skip the `.env` file entirely and paste the API key directly
into the sidebar when the app loads — it's kept only in that browser session.

## Deploy for free (so it's reachable from any device)

The easiest path, matching the stack this was built for:

1. Push this folder to a GitHub repo.
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in, and
   deploy the repo (main file: `app.py`).
3. In the app's **Settings → Secrets**, add:
   ```toml
   GEMINI_API_KEY = "your_key_here"
   ```
4. Once deployed, the app is reachable from any phone, tablet, or laptop
   browser at the streamlit.app URL — no install needed.

## Project structure

```
lecture-notes-ai/
├── app.py                  # Streamlit UI and page flow
├── utils/
│   ├── gemini_client.py    # Gemini API calls: transcribe, summarize, insights, questions
│   └── export.py           # Markdown / PDF study-pack export
├── requirements.txt
├── .env.example
└── README.md
```

## Notes on the MVP scope

- Transcription and all generation calls go through a single Gemini model
  (`gemini-3.6-flash` by default, configurable via `GEMINI_MODEL` in `.env`)
  — it's free-tier friendly and handles audio input directly, so there's no
  separate speech-to-text service to wire up.
- The transcript is editable before generating notes, so small
  transcription errors (names, jargon) can be fixed before they propagate
  into the summary and questions.
- Natural next steps if you extend this past MVP: persistent storage per
  user (so recordings survive a page refresh), multi-recording history,
  spaced-repetition scheduling for the generated questions, and speaker
  diarization for multi-person meetings.
