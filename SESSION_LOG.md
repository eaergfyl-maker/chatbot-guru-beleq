# Session Handoff Log

## Latest Status
- **Last Updated By:** Claude Code (2026-11-21)
- **Current Task:** Gemini-first conversation with silent fallback, fun facts, thinking indicator

## Recent Changes
- Built Replika-inspired split-stage companion layout in `web/index.html` with a sunlit arch room backdrop, top floating navigation dock, `LVL X · <Title>` badge pill, and a 2.5D multi-layer rigged Guru Beleq SVG puppet (`#guru-puppet`) with 3D mouse-tilt parallax, eye tracking, and interactive Web Audio drum beat on click.
- Added `reaction_of()` and `level_of()` in `src/persona.py` (exposed in `server.py` `/api/start` and `/api/chat` and shown in `app.py`) driving 8 live avatar reaction states (`idle`, `listening` while typing, `greeting`, `teaching` with animated talking mouth & drum taps, `celebrate` with double-mallet drum roll & musical notes, `thinking` with glasses adjustment, `comfort`, and `six_seven` juggle). Added test in `tests/test_bot.py` (53 tests pass).
- Updated `src/persona.py` (`reply_greeting`) and `src/nodes.py` (`_GREETING`, `take_name`, `smalltalk`) so that in addition to the automatic clock-based greeting on startup, typing `"good morning"` / `"morning"`, `"good afternoon"` / `"afternoon"`, or `"good evening"` / `"evening"` at any time of day mirrors the corresponding greeting (`"Good morning"`, `"Good afternoon"`, or `"Good evening"`). Added tests in `tests/test_bot.py`.
- Added menu option `8. Browse the Sasak glossary` (`glossary` intent & `glossary_node` in `src/nodes.py`, `src/persona.py`, `src/graph.py`) and unit tests in `tests/test_bot.py`.
- Added interactive context-aware quick-action menu bars (`menu`, `lesson`, and `quiz` stage controls), **Explore Knowledge** modal (6-lesson browser with completion badges, searchable 17-term Sasak glossary with one-click queries, and 24-edge semantic network viewer), and **Export Chat** transcript download to both `web/index.html` (`server.py` `/api/meta`) and `app.py` (Streamlit).
- Created full technical and academic report in `docs/REPORT.md` (Chapters 1–4, Mermaid architecture & semantic network diagrams, TF-IDF and CUQ formulas, and Harvard bibliography) and updated `README.md`.
- Invited `mightywound` and `amaninnit-hub` as collaborators (`write` permission) on `eaergfyl-maker/chatbot-guru-beleq`.
- Initialized `GEMINI.md`, `CLAUDE.md`, and `SESSION_LOG.md` for cross-agent collaboration.
- Replaced placeholder `assets/avatar.svg` with generated 512×512 PNG mascot (`assets/avatar.png`) and completed `assets/AVATAR_LOG.md`.
- Fixed false-positive partial-match disclaimer on synonym queries in `src/nodes.py` (`answer()`), added regression assertion in `tests/test_bot.py`, and scored `eval/results.csv`.
- Standardised the Streamlit UI (`app.py` + `.streamlit/config.toml`) and standalone web UI (`web/index.html` + `server.py`) with a shared Sasak colour palette, favicon, quiz progress badge, and CUQ modal dialog.

## Claude Code session (latest)
- Reviewed repo: 44 tests pass, `python -m src.knowledge` reports 0 problems, intent routing 15/15. Pushed avatar and partial-answer fix, README updated.
- Added `server.py` + `web/index.html`: standard-library web chat (`python server.py`, then http://localhost:8000). Endpoints: `POST /api/start`, `POST /api/chat`, `GET/POST /api/cuq`.
- Server binds IPv4 and IPv6 (`::` dual stack) because `localhost` resolved to `::1` on Windows and failed. `allow_reuse_address` is off so a second copy reports "Port 8000 is already in use" instead of silently sharing the port.
- Added the CUQ pop-up to the web page ("Rate this chatbot"); it saves via `eval.cuq.save` to `eval/cuq_responses.csv`.
- Committed Antigravity's uncommitted UI edits with this entry (`app.py` styling, `.streamlit/config.toml`, favicon and quiz score in the web badge, `GEMINI.md`). Not reviewed in depth beyond the tests passing.
- Convention: per `CLAUDE.md`, commits carry no Claude/Anthropic attribution.

- Added a copy-and-paste "Quick start" section to the top of `README.md` (clone, install, `python server.py`, open http://localhost:8000).

- Added a "67" easter egg: the exact message `67` gets `🤲 67`, then returns to the current lesson or quiz question (no attempt used), the menu, or the name prompt. `six_seven` intent/node in `src/nodes.py` and `src/graph.py`; 5 new tests (49 total). Variants like `6 7` or `six seven` are not matched.

- Vercel deployment: live at https://chatbot-guru-beleq.vercel.app, project `eaergfyl/chatbot-guru-beleq`, connected to GitHub so pushes to `main` deploy automatically. Added the link and online limits to `README.md` and `docs/REPORT.md`.
- Fixed two Vercel bugs: greetings used UTC (now UTC+8 when the `VERCEL` env var is set), and `POST /api/cuq` crashed with a 500 on the read-only disk (now returns the score with `saved: false`, and the page tells the tester). `server.submit_cuq` and 3 new tests (52 total).
- Online limits: no durable storage, so CUQ responses and learner profiles are not kept; `MemorySaver` state is lost when an instance is recycled. Collect CUQ data from a local copy, or add a hosted database.
- Local Vercel CLI is not linked: Node.js is not installed on this machine. `.vercel/` is now gitignored for when it is.

## Claude Code session: landing page and Sasak Village Sandbox (2026-11-21)
- **Breaking route change:** `/` now serves `web/landing.html` (mode selector). The chat moved to `/chat` (`web/index.html`, unchanged apart from new `🏠 Switch mode` and `🗺️ Sandbox` links in its header). `/chat/` and `/sandbox/` also work. Old bookmarks of `/` land on the selector, one click from the chat.
- New `/sandbox` (`web/sandbox.html`): self-contained canvas game, no external files. Courtyard with lumbung barns, Rinjani, bamboo fence, mats, stage; player moves with WASD/arrows, click/tap-to-walk, touch D-pad + E button; axis-separated collisions; fixed 1/60 s physics steps so speed does not depend on frame rate; camera follows the player when the screen is too small to show the whole 1200x780 world.
- 8 stations with Web Audio voices (drum dag-dug, accelerating petuq ticks, gong + kempur, reyong motif + suling, kenceng shimmer, procession groove). RPG dialogue: cited fact, glossary chips, Sources (full Harvard refs), Tell me more (station facts, then `/api/chat`), Play sound, Ask Guru Beleq (free text), and on Guru Beleq a Mini-quiz with Hint/Skip/Stop. HUD: discovery pill with walk-to dots, celebration banner at 8/8, sound toggle (remembered in localStorage), CUQ "Rate this chatbot", Switch mode.
- The sandbox chats on its own thread: it calls `/api/start`, then sends the player's name (or `Explorer`) and strips the menu text from replies.
- New `GET /api/sandbox` from `src/sandbox.py`: each station names `(topic, phrase)` pairs that must match exactly one fact in `topics.json`, plus glossary terms. Convention: if you reword a fact, update the phrase; `SandboxStations` tests fail otherwise.
- 9 new tests (`SandboxStations`, `WebRoutes` which runs the real handler on a free port). 62 tests pass.
- Checked in Chrome: landing, sandbox at desktop and 390px width, click-to-walk, dialogue, chatbot question, quiz start/stop, 8/8 celebration; no console errors. Not checked on a real touch device (D-pad only appears with a coarse pointer).

## Claude Code session: optional Gemini Smart Mode (2026-11-21)
- New `src/llm.py` (standard library only): reads `GEMINI_API_KEY`, `GEMINI_MODEL` (default `gemini-2.5-flash`), `GEMINI_ENABLED` from the environment or a local `.env` (real env vars win). Calls `generateContent` with the key in the `x-goog-api-key` header, 6 s timeout, `thinkingBudget: 0` on 2.5 Flash for speed.
- Fallback: every helper returns `None` on any failure and the node uses the rule-based reply it already built. HTTP 429 / `RESOURCE_EXHAUSTED` and 401/403 start a 300 s in-memory cooldown (per server instance; on Vercel each instance has its own). Non-STOP finish reasons (MAX_TOKENS, SAFETY) are discarded.
- Grounding check: `llm.grounded()` rejects an answer with no citation or with any citation part not among the supplied references. Small-talk rewrites must contain no citations and keep the mirrored greeting / bot name.
- `src/nodes.py`: `answer` (retrieved facts + up to two close runners-up; keeps the `(I read that as ...)` note, the related-lessons line and `_reprompt`), `smalltalk` and `offtopic` use Gemini. Everything else, including lesson/quiz grading, is unchanged and rule-based.
- Convention: `_msg()` now sets `engine: "python"` on every reply; Gemini replies set `engine: "gemini"`. `/api/chat` returns `engine` and `smart` (Gemini will be tried next turn), `/api/start` returns `smart`, `/api/meta` returns `llm` status. Chat header and sandbox HUD show `✨ Smart Mode` / `⚡ Classic Mode`.
- Tests set `GEMINI_ENABLED=0` at import so a developer's local `.env` never changes test results; `SmartMode` tests mock `urlopen`. 12 new tests, 74 total, no network.
- Not tested against the live Gemini API (no key in this session). Try it with a real key before relying on it; if Google changes the response shape, the code falls back to Classic Mode rather than breaking.
- The Streamlit app (`app.py`) also gets Smart Mode through the shared nodes but has no mode indicator yet.

## Claude Code session: Gemini-first and Vercel fixes (2026-11-22)
- Reported after deploying `5707578`: "give me a fun fact" got "That's outside what I teach", and `/api/chat` returned `engine: "python"` in ~1s with no cooldown. Most likely cause: the old `grounded()` read any "(2019)" as a citation and rejected "Saputra (2019)"-style replies, and it also required a citation. The real cause couldn't be confirmed without the live key; `/api/meta` now shows `llm.last_error` so it can be read on Vercel.
- **Gemini-first:** `answer`, `smalltalk`, `offtopic` and the new `fun_fact` node call `nodes._gemini()` first when `llm.available()`; on `None` they give their old rule-based reply. Gemini gets the full cited KB (`llm.knowledge_text()`, cached) plus the last 6 messages, and, inside a lesson/quiz, the current question with an instruction not to reveal it; `_reprompt` is still appended. Deterministic flows unchanged.
- `src/llm.py`: `systemInstruction` (camelCase), `TIMEOUT` 15 s, `maxOutputTokens` 1024. `thinkingConfig: {thinkingBudget: 0}` is still sent for gemini-2.5-flash (it is a supported field), but an HTTP 400 retries once without it and stops sending it. `grounded()` now only rejects (author, year) pairs that are not in the references, and accepts "(Saputra, 2019)", "Saputra (2019)", "et al." and "n.d." forms; no citation is fine. `status()` adds `last_error` (key redacted) and `last_success`.
- New Classic-Mode `fun_fact` intent ("fun/interesting/random/cool fact", "surprise me", "trivia", "did you know", and "another one" right after a fun fact): a random cited fact not given yet, also inside lessons/quizzes (returns to the question).
- UI: removed the Smart/Classic Mode pills; the `engine` and `smart` fields stay in the API for debugging only. Chat shows a "Guru Beleq is thinking" bubble with 3 bouncing dots and the avatar's `thinking` state while `/api/chat` runs; the sandbox dialogue shows the same dots; Streamlit wraps `ask()` in `st.spinner`.
- **Bug fixed:** commit `5707578` shipped `web/sandbox.html` with an unescaped apostrophe in a JS string (`'...Guru Beleq's answers...'`), a syntax error that stopped the whole sandbox script. Removed with the pill; sandbox checked in Chrome with no console errors.
- Tests: 81 pass, no key or network. Gemini-first fun fact / off-topic / follow-up / Q&A, full KB and history in the request, Classic fun facts, 401/403/429/timeout fallbacks, invented vs valid citation styles, the thinkingConfig 400 retry, key redaction in `last_error`, and pages without mode pills but with the thinking indicator.
- Watch: Vercel's function time limit must be above 15 s or a slow Gemini call could be cut off by the platform before the fallback runs.
- Note for local testing: stopping a background `python server.py` task can leave the Python process running on port 8000 (seen on Windows); check the port before starting another copy.

## Open items from this session
- `eval/cuq_responses.csv` is not in `.gitignore`: real tester answers will appear as git changes and publish if pushed. Decide whether to ignore it.
- Sandbox D-pad not yet tried on a real phone or tablet.

## Next Steps / Open Items
- [ ] Run the CUQ usability test with real testers (see `eval/CUQ_TEST_PLAN.md`) and report results (`python -m eval.cuq report`).
- [ ] Optional: swap `MemorySaver` for `SqliteSaver` if persistent chat history across restarts is needed.
