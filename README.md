# Guru Beleq: Gendang Beleq Teacher Chatbot

Guru Beleq ("Big Teacher") is a rule-based chatbot that teaches about the Gendang Beleq (Gendang Belek), the traditional drum ensemble of the Sasak people of Lombok. English only. It uses no LLM and no API key: the flow is a LangGraph graph and all language handling is plain Python.

## What it does

- Speaks first, greets by the computer's time of day, and asks your name.
- Menu by number or free text: lessons, questions, quiz, recommendation, progress, help.
- Acts as a teacher: teaches a step, asks a question, gives hints, explains after two misses.
- Understands small typos and alternative wording (spelling correction, synonyms, keywords).
- Remembers learners by name between sessions (`data/profiles.json`).

## Flow

```
START -> boot? -> greet (time greeting, ask name)
      -> validate -> reject (empty / too long / gibberish)
                  -> stage? -> take_name
                            -> normalize (spelling, synonyms, semantic net) -> classify
                                  -> answer | lesson_start | lesson_reply | quiz_start | quiz_reply
                                     recommend | progress | menu | leave | invite | help
                                     smalltalk | offtopic | bye
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
streamlit run app.py                      # web UI
python -m unittest discover tests         # scripted conversation tests
python -m eval.run_eval                   # runs eval/questions.csv, saves eval/results.csv
python -m src.knowledge                   # checks the knowledge base
python -m src.semantic_net                # prints the semantic network as a Mermaid diagram
```

## Layout

| Path | Purpose |
|---|---|
| `src/graph.py` | graph wiring, `start()` and `ask()` helpers, terminal chat |
| `src/nodes.py` | all nodes: greeting, name, intent rules, answers, lessons, quiz, recommender |
| `src/state.py` | graph state |
| `src/nlp.py` | validation, spelling correction, synonyms, keywords, answer matching |
| `src/search.py` | TF-IDF keyword search over the knowledge base |
| `src/knowledge.py` | loads and checks the knowledge base |
| `src/semantic_net.py` | semantic network used to widen searches |
| `src/persona.py` | name, time greetings, teacher phrases, menu, badges |
| `src/profiles.py` | saves learner progress by name |
| `data/knowledge/topics.json` | topics, lessons, quiz questions, glossary |
| `data/knowledge/semantic_net.json` | semantic network edges |
| `data/sources/` | the sources the knowledge base is written from |
| `assets/` | avatar and `AVATAR_LOG.md` (how it was made) |
| `app.py` | Streamlit UI with progress sidebar |
| `tests/`, `eval/` | automated tests, question set and runner |

## Adding knowledge

1. Put each source in `data/sources/` (see its README).
2. Edit `data/knowledge/topics.json`: facts, lesson steps (teach, question, answer groups, hint, explain), quiz questions, glossary.
3. Set `source` to the citation and `verified` to `true` once a topic is checked. The starter content is from general knowledge and is all marked `verified: false`.
4. Add edges to `data/knowledge/semantic_net.json`.
5. Run `python -m src.knowledge` and the tests.

Answer groups: each inner list is one concept with accepted wordings, and a learner answer is correct when every group is mentioned.

## Marking-scheme mapping

| Criterion | Where |
|---|---|
| Knowledge representation | semantic network, topic and lesson structure |
| NLP (synonyms, spelling, keywords) | `src/nlp.py`, `src/search.py` |
| Validation beyond menu options | `validate_input`, name check, `reject` node |
| Expert modules | question answering, teacher lessons, quiz, recommender |
| Exception handling | `safe()` wrapper, `ask()` guard, profile file recovery |
| Testing | `tests/`, `eval/` (CUQ questionnaire still to add) |

## Still to do

- Replace starter facts with verified, cited content.
- Generate the GenAI avatar and complete `assets/AVATAR_LOG.md`.
- Report documentation and submission format.
- Persistent chat history across restarts (swap `MemorySaver` for `SqliteSaver`) if needed.
