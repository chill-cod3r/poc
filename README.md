# Deep Coder

A deep coding agent with iterative refinement and verification-first planning. Built on LangChain's [Deep Agents](https://github.com/langchain-ai/deepagents) SDK.

## Philosophy

Most coding agents jump straight to code. Deep Coder forces a structured workflow:

1. **Discover** — Analyze the codebase before making assumptions
2. **Refine** — Pressure-test requirements against what actually exists (2-3 passes)
3. **Verify Requirements** — Human approves before any planning starts
4. **Plan** — Break into tasks, each with copy-pasteable verification commands
5. **Approve** — Human reviews the plan and verification steps
6. **Execute** — Autonomous implementation with self-verification
7. **Verify Execution** — Final evidence-based verification report

The agent can't skip phases. Human gates at requirements and plan approval. Every task is born with its proof of completion.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- An Anthropic API key (`ANTHROPIC_API_KEY`)

## Quick Start

```bash
cd projects/deep-coder
uv sync

# Run the CLI
ANTHROPIC_API_KEY=your-key uv run deep-coder

# Or run directly
ANTHROPIC_API_KEY=your-key uv run python -m deep_coder.cli
```

## Verification Categories

Every task must include verification steps from these categories:

- **HTTP** — curl commands with expected status codes and response bodies
- **LOG** — grep patterns in server/application logs
- **STATE** — database queries, file checks, config validation
- **INTEGRATION** — multi-step sequences (create → read → update → verify)
- **REGRESSION** — existing features that must still work

## Architecture

- Built on `deepagents` SDK (LangChain/LangGraph)
- State machine with 7 phases and conditional routing
- LangGraph checkpointing for state persistence
- Human-in-the-loop via LangGraph interrupts
- Each phase gets a dedicated system prompt optimized for its role

## Project Structure

```
deep_coder/
├── cli.py          # CLI interface with rich formatting
├── graph.py        # The workflow state machine
├── state.py        # State definitions and data models
├── prompts/
│   └── system.py   # Phase-specific system prompts
├── phases/         # (future) Phase-specific logic
└── tools/          # (future) Custom verification tools
```
