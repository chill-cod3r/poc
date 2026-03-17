# AGENTS.md — Deep Coder

## Tech Stack
- Python 3.11+
- deepagents SDK (LangChain/LangGraph based)
- langgraph for state machine and checkpointing
- rich for CLI formatting
- pydantic for state models

## Architecture
State machine graph with 7 phases: DISCOVER → REFINE → VERIFY_REQUIREMENTS → PLAN → APPROVE → EXECUTE → VERIFY_EXECUTION

Each phase node:
1. Creates a deep agent with a phase-specific system prompt
2. Invokes it with the current message history
3. Returns updated state including the next phase

Human gates use LangGraph `interrupt()` — the graph pauses and resumes when the human responds.

## Key Design Decisions
- Each phase gets its own agent instance (fresh context, focused prompt)
- Verification steps are first-class data, not afterthoughts
- Minimum 1 refinement pass before requirements can be approved
- Max 3 refinement passes to prevent infinite loops
- State is checkpointed — can resume from any phase after crash

## Gotchas
- deepagents `create_deep_agent` returns a compiled LangGraph graph. We invoke it inside our own graph nodes.
- The inner agent (deepagents) has its own tool loop. The outer graph (our state machine) manages phase transitions.
- Messages accumulate across phases. Consider summarization for long sessions.
- `interrupt()` blocks the graph execution thread — the CLI polls for human input.

## What's Next
- [ ] FastAPI backend for web UI
- [ ] React frontend with phase display, diff view, evidence panel
- [ ] Custom verification tools (HTTP assertions, log watchers)
- [ ] Persistent session storage (SQLite or LangGraph Store)
- [ ] Model selection per phase (cheaper models for verification parsing)
