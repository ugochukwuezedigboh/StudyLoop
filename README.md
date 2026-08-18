# StudyLoop — Lecture & Meeting Notes AI

> Built for the **3MTT Showcase**.

Record a lecture or meeting, get a clean transcript, an organized summary,
the key insights worth remembering, and practice exam questions — all in
one browser tab, on any device.

## What it does

1. **Sign up / log in** — each user has their own account, so their usage
   is tracked individually.
2. **Capture** — record straight from the browser mic, or upload an audio
   file (mp3/wav/m4a/ogg/flac/aac), or upload a PDF/Word document.
3. **Transcribe** — sends the audio to Gemini and returns an editable,
   cleaned-up transcript.
4. **Generate**
   - **Summary** — overview, main points, action items.
   - **Key insights** — core concepts, important details, likely exam points.
   - **Practice questions** — multiple choice, short answer, essay, or a mix,
     with adjustable count and difficulty.
5. **Export** — download the whole study pack as Markdown or PDF.

Free accounts get a limited number of sessions per month; once that's used
up, the app prompts an upgrade to Premium for unlimited use.

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

Alternatively, skip the `.env` file entirely and paste the Gemini API key
directly into the sidebar when the app loads — it's kept only in that
browser session.

For local testing of accounts and the paywall, also add your Supabase and
Paystack keys (see **Accounts, usage limits & payments** below) to
`.streamlit/secrets.toml`. Make sure that file is listed in `.gitignore` so
it never gets pushed to GitHub.

## Deploy for free (so it's reachable from any device)

The easiest path, matching the stack this was built for:

1. Push this folder to a GitHub repo.
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in, and
   deploy the repo (main file: `app.py`).
3. In the app's **Settings → Secrets**, add:
   ```toml
   GEMINI_API_KEY = "your_key_here"
   SUPABASE_URL = "your_supabase_project_url"
   SUPABASE_KEY = "your_supabase_secret_key"
   PAYSTACK_SECRET_KEY = "your_paystack_secret_key"
   ```
4. Once deployed, the app is reachable from any phone, tablet, or laptop
   browser at the streamlit.app URL — no install needed.

## Accounts, usage limits & payments

StudyLoop uses a lightweight freemium model:

- **Accounts** — email/password sign-up and login, backed by a
  [Supabase](https://supabase.com) Postgres database (hosted, so data
  persists across redeploys — unlike SQLite on Streamlit Cloud).
- **Usage tracking** — each recording, upload, or transcription counts as
  one session for that month; free accounts get a set number of sessions
  before hitting the paywall.
- **Payments** — upgrading to Premium runs through
  [Paystack](https://paystack.com); once payment is verified, the account
  is flagged premium and the monthly cap no longer applies.

This logic lives in `monetization.py`, which is imported at the top of
`app.py` and wraps the recording/upload flow with a usage check.

## Project structure

```
lecture-notes-ai/
├── app.py                  # Streamlit UI and page flow
├── monetization.py          # Accounts, usage tracking, paywall, Paystack payments
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
- Accounts and usage tracking are intentionally simple (email/password with
  hashed passwords, no email verification or password reset flow yet).
- Natural next steps if you extend this past MVP: persistent storage of
  each user's recordings and generated notes (not just usage counts),
  multi-recording history, spaced-repetition scheduling for the generated
  questions, speaker diarization for multi-person meetings, and a proper
  password reset flow.
