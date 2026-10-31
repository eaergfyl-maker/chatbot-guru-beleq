# Claude Instructions

## Session Synchronization Protocol
- Before starting any task:
  1. Read `SESSION_LOG.md` to see the latest changes and context from previous work.
  2. Run `git log -n 3` to see recent commits.
- After completing a task or milestone:
  1. Update `SESSION_LOG.md` with:
     - Summary of changes made.
     - Any breaking changes or new conventions introduced.
     - Unfinished items or recommended next steps.
  2. Commit your changes with a descriptive Git message.

# Git and GitHub

- Do not add any attribution to commits or pull requests: no `Co-Authored-By` trailer, no "Generated with Claude Code" line, and no mention of Claude or Anthropic in commit messages, PR titles or PR descriptions.
- This applies every time you commit or push: remove your name (Claude/Anthropic) from anything that goes to GitHub.
- Commit messages should read as written by the user alone.
