"""CLI interface for deep-coder."""

import sys
import uuid

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

from deep_coder.graph import build_graph
from deep_coder.state import Phase

console = Console()

PHASE_DISPLAY = {
    Phase.DISCOVER: ("🔍", "Discovery", "Analyzing codebase and building requirements"),
    Phase.REFINE: ("🔄", "Refinement", "Pressure-testing requirements against codebase"),
    Phase.VERIFY_REQUIREMENTS: ("✅", "Requirements Review", "Waiting for your approval"),
    Phase.PLAN: ("📋", "Planning", "Breaking requirements into verified tasks"),
    Phase.APPROVE: ("👍", "Plan Review", "Waiting for your approval"),
    Phase.EXECUTE: ("⚡", "Execution", "Implementing tasks with self-verification"),
    Phase.VERIFY_EXECUTION: ("🧪", "Final Verification", "Running complete verification pass"),
    Phase.COMPLETE: ("🎉", "Complete", "All tasks verified and done"),
}


def display_phase(phase: Phase):
    """Show current phase in a nice banner."""
    emoji, name, desc = PHASE_DISPLAY.get(phase, ("❓", "Unknown", ""))
    console.print(Panel(
        f"{desc}",
        title=f"{emoji} {name}",
        border_style="cyan",
    ))


def display_message(role: str, content: str):
    """Display a message from the agent or user."""
    if role == "assistant":
        console.print(Panel(Markdown(content), title="🤖 Agent", border_style="green"))
    elif role == "user":
        console.print(Panel(content, title="👤 You", border_style="blue"))


def main():
    """Run the deep-coder CLI."""
    console.print(Panel(
        "[bold cyan]Deep Coder[/bold cyan]\n"
        "Iterative refinement → Verification-first planning → Autonomous execution\n\n"
        "Describe what you want to build. I'll analyze your codebase,\n"
        "refine the requirements with you, plan verified tasks,\n"
        "and execute autonomously with proof of completion.",
        title="🧠 Deep Coder v0.1",
        border_style="bold cyan",
    ))

    # Get the project path
    project_path = Prompt.ask(
        "\n📁 Project path",
        default=".",
    )

    # Get the initial request
    console.print()
    request = Prompt.ask("💬 What do you want to build?")

    if not request.strip():
        console.print("[red]No request provided. Exiting.[/red]")
        sys.exit(1)

    # Build the graph
    graph = build_graph()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # Initial input
    initial_input = {
        "messages": [
            {
                "role": "user",
                "content": (
                    f"Project path: {project_path}\n\n"
                    f"Request: {request}\n\n"
                    "Start by reading the project structure and key files "
                    "to understand the codebase before building requirements."
                ),
            }
        ],
        "project_path": project_path,
        "phase": Phase.DISCOVER,
    }

    console.print()
    display_phase(Phase.DISCOVER)

    # Run the graph with interrupt handling
    current_input = initial_input

    while True:
        try:
            # Stream events from the graph
            for event in graph.stream(current_input, config, stream_mode="updates"):
                for node_name, node_output in event.items():
                    # Display phase changes
                    if "phase" in node_output:
                        phase = node_output["phase"]
                        if isinstance(phase, str):
                            phase = Phase(phase)
                        console.print()
                        display_phase(phase)

                    # Display new messages
                    if "messages" in node_output:
                        for msg in node_output["messages"]:
                            if hasattr(msg, "content") and msg.content:
                                display_message(msg.type, msg.content)
                            elif isinstance(msg, dict) and msg.get("content"):
                                display_message(msg.get("role", "assistant"), msg["content"])

            # Check if we're done
            state = graph.get_state(config)
            if state.values.get("phase") == Phase.COMPLETE:
                console.print(Panel(
                    "All tasks implemented and verified. Check `.deep-coder/` for the full report.",
                    title="🎉 Complete",
                    border_style="bold green",
                ))
                break

            # If we hit an interrupt, get human input
            if state.next:
                # There's a pending interrupt
                console.print()
                human_input = Prompt.ask("[bold yellow]Your response[/bold yellow]")
                current_input = Command(resume=human_input)
            else:
                break

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. State is saved — you can resume later.[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            console.print("[yellow]State is checkpointed. Debug and resume.[/yellow]")
            break


if __name__ == "__main__":
    main()
