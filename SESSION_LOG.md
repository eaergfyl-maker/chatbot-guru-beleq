# Session Handoff Log

## Latest Status
- **Last Updated By:** Antigravity
- **Current Task:** Added interactive menu, special features, and full project documentation (`docs/REPORT.md`)

## Recent Changes
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

## Open items from this session
- `eval/cuq_responses.csv` is not in `.gitignore`: real tester answers will appear as git changes and publish if pushed. Decide whether to ignore it.
- The web page has not been checked visually in a browser by Claude; only via HTTP requests.

## Next Steps / Open Items
- [ ] Run the CUQ usability test with real testers (see `eval/CUQ_TEST_PLAN.md`) and report results (`python -m eval.cuq report`).
- [ ] Optional: swap `MemorySaver` for `SqliteSaver` if persistent chat history across restarts is needed.
