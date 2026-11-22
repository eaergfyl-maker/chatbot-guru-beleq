# Guru Beleq: Gendang Beleq Teacher Chatbot

Guru Beleq ("Big Teacher") is a rule-based chatbot that teaches about the Gendang Beleq (Gendang Belek), the traditional drum ensemble of the Sasak people of Lombok. English only. It works with no LLM and no API key: the flow is a LangGraph graph and all language handling is plain Python. An optional free Gemini key lets Gemini answer open-ended conversation first, grounded in the same cited facts, with a silent fallback to the rule-based engine (see [Optional Gemini](#optional-gemini-free-api-key)).

**Try it online:** https://chatbot-guru-beleq.vercel.app (nothing to install)

Pushes to `main` deploy automatically to the [Vercel project](https://vercel.com/eaergfyl/chatbot-guru-beleq). The online version runs `server.py` as a serverless function, so it differs from a local copy:
- Greetings use UTC+8 (Lombok time), not the visitor's clock.
- Learners are not remembered between sessions, and a conversation can restart if the server instance is recycled.
- `Rate this chatbot` shows the score but does not store it. Run the app locally to collect CUQ responses.

## Quick start (copy and paste)

You need [Python 3.10 or newer](https://www.python.org/downloads/) and [Git](https://git-scm.com/downloads). Open a terminal (PowerShell on Windows) and paste these lines one block at a time.

**1. Get the code and install (once):**

```
git clone https://github.com/eaergfyl-maker/chatbot-guru-beleq.git
cd chatbot-guru-beleq
pip install -r requirements.txt
```

**2. Start the chatbot web page:**

```
python server.py
```

**3. Open it:** go to http://localhost:8000 in your browser and pick a mode: **Talk with Guru Beleq** (`/chat`) or the **Sasak Village Sandbox** game (`/sandbox`). Keep the terminal open while you use it; press `Ctrl+C` there to stop.

Prefer Streamlit or the terminal instead?
- Streamlit UI (http://localhost:8501): `streamlit run app.py`
- Terminal chat: `python -m src.graph`

## What it does

- Speaks first, greets by the computer's time of day, and asks your name.
- Menu by number (`1–8`, `0`), clickable quick-action chips, or free text: lessons, questions, quiz, recommendation, progress, help, sources, Sasak glossary, and fun facts ("give me a fun fact", "surprise me").
- Acts as a teacher: teaches a step, asks a question, gives hints, explains after two misses, and answers interrupting side questions before returning to the lesson or quiz.
- Understands small typos, alternative wording and the kind of question asked (spelling correction, synonyms, keywords, question cues, one-hop semantic network expansion).
- Cites its sources in Harvard style in every answer, and admits when it has no exact answer instead of guessing.
- Remembers learners by name between sessions (`data/profiles.json`).
- **Special Web & Streamlit UI Features**:
  - **Context-Aware Quick-Action Menu Bar**: One-click pills for all menu options (`1–8`) and a direct lesson topic selector in menu mode; switches automatically to `Hint`, `Repeat step`, `Skip question`, and `Leave/Stop` buttons during a lesson or quiz.
  - **Explore Knowledge Modal (`Explore knowledge`)**: Interactive 3-tab browser for all 6 lessons (with completion badges), a searchable 17-term Sasak & musical glossary with one-click *"Ask Guru"* buttons, and the 24-edge cited semantic network.
  - **Export Learning Transcript (`Export chat`)**: Downloads the conversation transcript and learner progress summary as `guru-beleq-transcript.txt`.
  - **Built-in CUQ Usability Modal (`Rate this chatbot`)**: 16-item Chatbot Usability Questionnaire dialog saving anonymous scores to `eval/cuq_responses.csv`.

## Time-of-day themes

`/` and `/chat` change look with the visitor's own clock: **🌿 Morning** (05:00–11:59, tropical emerald and coastal teal), **🌅 Afternoon** (12:00–17:59, Lombok sunset coral and twilight plum) and **🏮 Evening** (18:00–04:59, twilight indigo with lantern-gold glass, a dark mode). The pill next to EN | BM cycles *Auto → Morning → Afternoon → Evening*; the choice is remembered in the browser and shared by both pages. `?theme=evening` forces a look for one visit without saving it. The sandbox keeps its own daylight art.

## Bahasa Malaysia

Every page has an **EN | BM** switch (top right on the chat and sandbox, top corner on the landing page; a *Language / Bahasa* selector in the Streamlit sidebar). The choice is remembered in the browser, carried across `/`, `/chat` and `/sandbox`, and can be forced with `?lang=ms` (for example `http://localhost:8000/chat?lang=ms`).

- **Everything switches**: page text, the bot's replies (greeting, menu, lessons, quiz, hints, recommendations, small talk), lesson titles, the glossary, the semantic network labels, sandbox station notes and the CUQ questionnaire. Gemini is told to reply in Bahasa Malaysia and gets the Malay knowledge base.
- **Switching mid-conversation** keeps your progress: Guru Beleq confirms the switch and repeats the current lesson or quiz question (or the menu) in the new language, without using an attempt.
- **Both languages are understood at once**: Malay intent words (`pelajaran`, `kuiz`, `petunjuk`, `langkau`, `berhenti`, `nama saya ...`, `fakta menarik`, `satu lagi`) work in either mode, an English question in BM mode gets a Malay answer, and English answer words are still accepted in Malay lessons.
- **Citations are unchanged**: `data/knowledge/topics_ms.json` holds only the Malay text and lines up with `topics.json` by position, so each translated fact keeps the English fact's sources and Harvard citation. `python -m src.knowledge` checks that the two files line up.
- **API**: `POST /api/start` and `/api/chat` take `"lang": "ms"`; `POST /api/language {thread_id, lang}` switches a conversation; `GET /api/meta`, `/api/sandbox` and `/api/cuq` take `?lang=ms`. The bot's own sentences live in `src/i18n.py`; page text lives in each page's `GBLang.add({...})` dictionary (shared helper `web/lang.js`).
- The Malay wording, including the CUQ items, is our own translation and has not been checked by a native speaker yet.

## Optional Gemini (free API key)

Without a key, Guru Beleq is fully rule-based (pure Python). With a free Google AI Studio key, **Gemini answers open-ended conversation first**: questions, follow-ups ("explain it simply", "tell me more"), comparisons, "give me a fun fact", small talk and off-topic questions (which it politely declines). Learners are never told which engine replied.

**Add a key locally:**
1. Get a free key at https://aistudio.google.com/apikey.
2. Copy `.env.example` to `.env` and paste the key after `GEMINI_API_KEY=`. `.env` is gitignored, so the key is never committed.
3. Restart `python server.py`. No extra packages are needed (`src/llm.py` uses only the standard library).

**Add a key on Vercel:** Project → Settings → Environment Variables → add `GEMINI_API_KEY` (and optionally `GEMINI_MODEL`, default `gemini-2.5-flash`), then redeploy.

**What stays rule-based:** input validation, name capture, menu numbers `0–8`, `67`, lesson and quiz steps and grading (so scores stay predictable), progress, sources, glossary, recommendations, leaving and goodbye.

**Grounding:** Gemini receives the whole cited knowledge base (31 facts, 17 glossary entries and 6 Harvard references, about 2k tokens) plus the last few messages, and is told to use only those facts with their exact citations. A reply that cites a source or year not in the references is discarded. Inside a lesson or quiz, Gemini is told not to give away the current answer, and the learner is brought back to the question afterwards.

**Silent fallback:** no key, `GEMINI_ENABLED=0`, a 15-second timeout, network or server errors, odd responses or an invented citation all give the normal rule-based reply. A quota/rate-limit error (HTTP 429) or a rejected key (401/403) also pauses Gemini for 5 minutes. If the API rejects `thinkingConfig` (HTTP 400), the call is retried once without it.

**Diagnosing on Vercel:** open `/api/meta` and look at `llm`: `enabled`, `available`, `cooldown_seconds`, `last_error` (the last reason Gemini was not used, with the key redacted) and `last_success`. This is never shown in the chat.

## Sasak Village Sandbox (`/sandbox`)

A playable top-down courtyard (HTML5 canvas, no libraries or CDN files) set in a Lombok *sanggar*, with *lumbung* rice barns, palms, woven mats and a stage.

- **Move** with WASD or the arrow keys, click/tap to walk, or use the on-screen D-pad and `E` button on touch screens. `E`/Space inspects the station you stand next to; `Esc` closes the dialogue.
- **8 stations**: Gendang Mame & Gendang Nine, Petuq / Oncer, Gong Beleq & Kempur, Reyong & Suling, Kenceng & Rincik, the costume stand (sapuk, dodot, bebet), the Nyongkolan arch and history mural, and Guru Beleq on the stage.
- **RPG dialogue box** with Guru Beleq's portrait. Facts come from `GET /api/sandbox`, which picks them from `data/knowledge/topics.json` (`src/sandbox.py`), so every fact carries its Harvard citation and the full references are listed under *Sources*. Buttons: **Tell me more** (next fact, then the chatbot), **Play sound** (Web Audio synthesis of each instrument), **Ask Guru Beleq** (free-text question through `/api/chat`), and on the stage a **Mini-quiz** with hint/skip/stop.
- **HUD**: `Discovered n/8 stations` with dots that walk you to each station, a drum-roll celebration when all 8 are found, sound on/off, **Rate this chatbot** (CUQ), and **Switch mode** back to `/`.

## Flow

```
START -> boot? -> greet (time greeting, ask name)
      -> validate -> reject (empty / too long / gibberish)
                  -> stage? -> take_name
                            -> normalize (spelling, synonyms, semantic net) -> classify
                                  -> answer | lesson_start | lesson_reply | quiz_start | quiz_reply
                                     recommend | progress | sources | glossary | menu | leave
                                     invite | help | smalltalk | offtopic | bye
```

State (stage, user name, lesson, quiz, progress) is kept per conversation by the LangGraph `MemorySaver` checkpointer. Every node is wrapped by `safe()` so an error produces an apology instead of a crash.

## Setup and run

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

```bash
python -m src.graph                       # terminal chat
python server.py                          # standalone web page at http://localhost:8000
streamlit run app.py                      # Streamlit web UI at http://localhost:8501
python -m unittest discover tests         # 103 scripted tests (no API key or network needed)
python -m eval.run_eval                   # runs eval/questions.csv, saves eval/results.csv
python -m eval.cuq collect                # one tester fills in the CUQ (also in the web UI)
python -m eval.cuq report                 # CUQ score and item means from all responses
python -m src.knowledge                   # checks the knowledge base and its citations
python -m src.semantic_net                # prints the semantic network as a Mermaid diagram
```

## Layout

| Path | Purpose |
|---|---|
| `src/graph.py` | graph wiring, `start()` and `ask()` helpers, terminal chat |
| `src/nodes.py` | all nodes: greeting, name, intent rules, answers, lessons, quiz, recommender, glossary |
| `src/state.py` | graph state |
| `src/nlp.py` | validation, spelling correction, synonyms, keywords, answer matching |
| `src/search.py` | TF-IDF keyword search over the knowledge base |
| `src/knowledge.py` | loads and checks the knowledge base |
| `src/semantic_net.py` | semantic network used to widen searches |
| `src/persona.py` | name, time greetings, teacher phrases, menu, badges |
| `src/llm.py` | optional Gemini: full cited knowledge base prompt, citation check, timeout, quota cooldown, diagnostics, `.env` loading |
| `.env.example` | template for `GEMINI_API_KEY` / `GEMINI_MODEL` (copy to `.env`) |
| `src/profiles.py` | saves learner progress by name |
| `data/knowledge/topics.json` | cited facts, lessons, quiz questions, glossary, references |
| `data/knowledge/topics_ms.json` | Bahasa Malaysia text for the same facts, lessons, quiz and glossary, matched by position |
| `src/i18n.py`, `web/lang.js` | the bot's sentences in both languages, and the pages' language switch |
| `data/knowledge/semantic_net.json` | semantic network edges, with citations |
| `data/sources/` | notes on each source the knowledge base is written from |
| `assets/` | GenAI avatar (`avatar.png`, favicon), 3D companion sprite (`guru_3d.png`) and `AVATAR_LOG.md` (prompts and how they were made) |
| `server.py` | standard-library web server: pages `/`, `/chat`, `/sandbox`; API `/api/start`, `/api/chat`, `/api/meta`, `/api/cuq`, `/api/sandbox` |
| `web/landing.html` | mode selection page (`/`) |
| `web/theme.css`, `web/theme.js` | time-of-day frosted-glass themes shared by `/` and `/chat` |
| `web/index.html` | companion chat page (`/chat`): arched 3D companion stage, interactive menu, knowledge explorer, transcript export, and CUQ modal |
| `web/sandbox.html`, `src/sandbox.py` | Sasak Village Sandbox game (`/sandbox`) and its cited station facts (`/api/sandbox`) |
| `app.py`, `.streamlit/config.toml` | Streamlit UI with Sasak theme, quick-action bar, knowledge explorer, transcript export, and CUQ modal |
| `docs/REPORT.md` | full technical and academic report (Chapters 1–4) |
| `tests/` | scripted conversation tests |
| `eval/` | question set and runner, CUQ questionnaire (`cuq.py`) and test plan (`CUQ_TEST_PLAN.md`) |

## Adding knowledge

1. Add a notes file for the source to `data/sources/`, and its citation to `references` in `data/knowledge/topics.json`.
2. Edit `topics.json`: facts (each with its `sources`), lesson steps (teach, question, answer groups, hint, explain), quiz questions, glossary.
3. Add edges to `data/knowledge/semantic_net.json`.
4. Add the Malay text in the same position in `data/knowledge/topics_ms.json` (facts, lesson steps with Malay answer words, quiz items, glossary meanings). Sources and citations are taken from `topics.json`.
5. Run `python -m src.knowledge` and the tests. The tests fail if a fact has no citation or the Malay file does not line up.

Answer groups: each inner list is one concept with accepted wordings, and a learner answer is correct when every group is mentioned.

## Marking-scheme mapping

| Criterion | Where |
|---|---|
| Knowledge representation | semantic network (`data/knowledge/semantic_net.json`), topic, lesson, and glossary structure (`data/knowledge/topics.json`) |
| NLP (synonyms, spelling, keywords) | `src/nlp.py`, `src/search.py` |
| Validation beyond menu options | `validate_input`, `extract_name`, `reject` node |
| Expert modules | question answering, teacher lessons, adaptive quiz, recommender, Sasak glossary explorer |
| Exception handling | `safe()` wrapper, `ask()` guard, atomic profile file recovery |
| Testing | `tests/`, `eval/run_eval.py`, CUQ in `eval/cuq.py` and web/Streamlit UI |
| Harvard referencing | `references` in `topics.json`, in-text citations in answers & glossary, menu option 7 |
| Report & documentation | `docs/REPORT.md`, `assets/AVATAR_LOG.md`, `eval/CUQ_TEST_PLAN.md` |

## Still to do

- Run the CUQ with real testers (see `eval/CUQ_TEST_PLAN.md`) and report the results (`python -m eval.cuq report`).
- Optional: swap `MemorySaver` for `SqliteSaver` if persistent chat history across restarts is needed.
