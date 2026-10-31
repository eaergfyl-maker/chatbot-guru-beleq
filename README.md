# Guru Beleq: Gendang Beleq Teacher Chatbot

Guru Beleq ("Big Teacher") is a rule-based chatbot that teaches about the Gendang Beleq (Gendang Belek), the traditional drum ensemble of the Sasak people of Lombok. English only. It uses no LLM and no API key: the flow is a LangGraph graph and all language handling is plain Python.

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

**3. Open it:** go to http://localhost:8000 in your browser. Keep the terminal open while you chat; press `Ctrl+C` there to stop.

Prefer Streamlit or the terminal instead?
- Streamlit UI (http://localhost:8501): `streamlit run app.py`
- Terminal chat: `python -m src.graph`

## What it does

- Speaks first, greets by the computer's time of day, and asks your name.
- Menu by number (`1–8`, `0`), clickable quick-action chips, or free text: lessons, questions, quiz, recommendation, progress, help, sources, and Sasak glossary.
- Acts as a teacher: teaches a step, asks a question, gives hints, explains after two misses, and answers interrupting side questions before returning to the lesson or quiz.
- Understands small typos, alternative wording and the kind of question asked (spelling correction, synonyms, keywords, question cues, one-hop semantic network expansion).
- Cites its sources in Harvard style in every answer, and admits when it has no exact answer instead of guessing.
- Remembers learners by name between sessions (`data/profiles.json`).
- **Special Web & Streamlit UI Features**:
  - **Context-Aware Quick-Action Menu Bar**: One-click pills for all menu options (`1–8`) and a direct lesson topic selector in menu mode; switches automatically to `Hint`, `Repeat step`, `Skip question`, and `Leave/Stop` buttons during a lesson or quiz.
  - **Explore Knowledge Modal (`Explore knowledge`)**: Interactive 3-tab browser for all 6 lessons (with completion badges), a searchable 17-term Sasak & musical glossary with one-click *"Ask Guru"* buttons, and the 24-edge cited semantic network.
  - **Export Learning Transcript (`Export chat`)**: Downloads the conversation transcript and learner progress summary as `guru-beleq-transcript.txt`.
  - **Built-in CUQ Usability Modal (`Rate this chatbot`)**: 16-item Chatbot Usability Questionnaire dialog saving anonymous scores to `eval/cuq_responses.csv`.

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
python -m unittest discover tests         # 44 scripted conversation tests
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
| `src/profiles.py` | saves learner progress by name |
| `data/knowledge/topics.json` | cited facts, lessons, quiz questions, glossary, references |
| `data/knowledge/semantic_net.json` | semantic network edges, with citations |
| `data/sources/` | notes on each source the knowledge base is written from |
| `assets/` | GenAI avatar (`avatar.png`) and `AVATAR_LOG.md` (prompts and how it was made) |
| `server.py`, `web/index.html` | standalone web chat page with interactive menu, knowledge explorer, transcript export, and CUQ modal |
| `app.py`, `.streamlit/config.toml` | Streamlit UI with Sasak theme, quick-action bar, knowledge explorer, transcript export, and CUQ modal |
| `docs/REPORT.md` | full technical and academic report (Chapters 1–4) |
| `tests/` | scripted conversation tests |
| `eval/` | question set and runner, CUQ questionnaire (`cuq.py`) and test plan (`CUQ_TEST_PLAN.md`) |

## Adding knowledge

1. Add a notes file for the source to `data/sources/`, and its citation to `references` in `data/knowledge/topics.json`.
2. Edit `topics.json`: facts (each with its `sources`), lesson steps (teach, question, answer groups, hint, explain), quiz questions, glossary.
3. Add edges to `data/knowledge/semantic_net.json`.
4. Run `python -m src.knowledge` and the tests. The tests fail if a fact has no citation.

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
