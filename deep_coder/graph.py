"""The deep-coder workflow graph.

State machine: DISCOVER → REFINE (loop) → VERIFY_REQUIREMENTS → PLAN → APPROVE → EXECUTE → VERIFY_EXECUTION
"""

from typing import Literal

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from deep_coder.state import DeepCoderState, Phase
from deep_coder.prompts.system import (
    DISCOVER_PROMPT,
    REFINE_PROMPT,
    VERIFY_REQUIREMENTS_PROMPT,
    PLAN_PROMPT,
    APPROVE_PROMPT,
    EXECUTE_PROMPT,
    VERIFY_EXECUTION_PROMPT,
)


def _make_agent(system_prompt: str, model_name: str = "anthropic:claude-sonnet-4-20250514"):
    """Create a deep agent with a phase-specific system prompt."""
    model = init_chat_model(model_name)
    return create_deep_agent(
        model=model,
        system_prompt=system_prompt,
    )


# --- Phase Nodes ---


def discover(state: DeepCoderState) -> dict:
    """DISCOVER: Analyze codebase and build initial requirements."""
    agent = _make_agent(DISCOVER_PROMPT)
    result = agent.invoke({"messages": state["messages"]})
    return {
        "messages": result["messages"],
        "phase": Phase.REFINE,
        "refinement_count": 0,
    }


def refine(state: DeepCoderState) -> dict:
    """REFINE: Pressure-test requirements against the codebase."""
    agent = _make_agent(REFINE_PROMPT)
    result = agent.invoke({"messages": state["messages"]})
    return {
        "messages": result["messages"],
        "refinement_count": state.get("refinement_count", 0) + 1,
        "phase": Phase.VERIFY_REQUIREMENTS,
    }


def verify_requirements(state: DeepCoderState) -> dict:
    """VERIFY_REQUIREMENTS: Present requirements to human for approval."""
    agent = _make_agent(VERIFY_REQUIREMENTS_PROMPT)
    result = agent.invoke({"messages": state["messages"]})

    # Interrupt for human approval
    human_decision = interrupt(
        {
            "type": "requirements_review",
            "phase": "verify_requirements",
            "prompt": "Review the requirements above. Reply APPROVE, REJECT, or describe changes needed.",
        }
    )

    if human_decision.upper().strip() == "APPROVE":
        return {
            "messages": result["messages"] + [{"role": "user", "content": "Requirements approved. Proceed to planning."}],
            "requirements_approved": True,
            "phase": Phase.PLAN,
        }
    elif human_decision.upper().strip() == "REJECT":
        return {
            "messages": result["messages"] + [{"role": "user", "content": "Requirements rejected. Starting over."}],
            "requirements_approved": False,
            "phase": Phase.DISCOVER,
            "refinement_count": 0,
        }
    else:
        # Changes requested — go back to refine with the feedback
        return {
            "messages": result["messages"] + [{"role": "user", "content": f"Changes requested: {human_decision}"}],
            "requirements_approved": False,
            "phase": Phase.REFINE,
        }


def plan(state: DeepCoderState) -> dict:
    """PLAN: Break requirements into tasks with verification steps."""
    agent = _make_agent(PLAN_PROMPT)
    result = agent.invoke({"messages": state["messages"]})
    return {
        "messages": result["messages"],
        "phase": Phase.APPROVE,
    }


def approve(state: DeepCoderState) -> dict:
    """APPROVE: Present execution plan to human for approval."""
    agent = _make_agent(APPROVE_PROMPT)
    result = agent.invoke({"messages": state["messages"]})

    # Interrupt for human approval
    human_decision = interrupt(
        {
            "type": "plan_review",
            "phase": "approve",
            "prompt": "Review the execution plan above. Reply APPROVE, MODIFY (with details), or REJECT.",
        }
    )

    if human_decision.upper().strip() == "APPROVE":
        return {
            "messages": result["messages"] + [{"role": "user", "content": "Plan approved. Begin execution."}],
            "plan_approved": True,
            "phase": Phase.EXECUTE,
        }
    elif human_decision.upper().strip() == "REJECT":
        return {
            "messages": result["messages"] + [{"role": "user", "content": "Plan rejected. Return to planning."}],
            "plan_approved": False,
            "phase": Phase.PLAN,
        }
    else:
        # Modifications requested
        return {
            "messages": result["messages"] + [{"role": "user", "content": f"Plan modifications: {human_decision}"}],
            "plan_approved": False,
            "phase": Phase.PLAN,
        }


def execute(state: DeepCoderState) -> dict:
    """EXECUTE: Implement tasks autonomously with self-verification."""
    agent = _make_agent(EXECUTE_PROMPT)
    result = agent.invoke({"messages": state["messages"]})
    return {
        "messages": result["messages"],
        "phase": Phase.VERIFY_EXECUTION,
    }


def verify_execution(state: DeepCoderState) -> dict:
    """VERIFY_EXECUTION: Final verification pass with evidence."""
    agent = _make_agent(VERIFY_EXECUTION_PROMPT)
    result = agent.invoke({"messages": state["messages"]})

    # Interrupt to show the human the final report
    human_decision = interrupt(
        {
            "type": "final_review",
            "phase": "verify_execution",
            "prompt": "Review the verification report. Reply ACCEPT to complete, or REDO to re-execute failed tasks.",
        }
    )

    if human_decision.upper().strip() == "ACCEPT":
        return {
            "messages": result["messages"],
            "phase": Phase.COMPLETE,
        }
    else:
        return {
            "messages": result["messages"] + [{"role": "user", "content": f"Re-execution needed: {human_decision}"}],
            "phase": Phase.EXECUTE,
        }


# --- Routing ---


def route_phase(state: DeepCoderState) -> str:
    """Route to the next node based on current phase."""
    phase = state.get("phase", Phase.DISCOVER)

    # Check if we've hit max refinements and should force verification
    if phase == Phase.REFINE:
        count = state.get("refinement_count", 0)
        max_ref = state.get("max_refinements", 3)
        if count >= max_ref:
            return "verify_requirements"

    return phase.value


# --- Graph Construction ---


def build_graph():
    """Build the deep-coder workflow graph."""
    builder = StateGraph(DeepCoderState)

    # Add all phase nodes
    builder.add_node("discover", discover)
    builder.add_node("refine", refine)
    builder.add_node("verify_requirements", verify_requirements)
    builder.add_node("plan", plan)
    builder.add_node("approve", approve)
    builder.add_node("execute", execute)
    builder.add_node("verify_execution", verify_execution)

    # Entry point
    builder.add_edge(START, "discover")

    # Phase transitions via conditional routing
    builder.add_conditional_edges(
        "discover",
        route_phase,
        {
            "refine": "refine",
        },
    )

    builder.add_conditional_edges(
        "refine",
        route_phase,
        {
            "verify_requirements": "verify_requirements",
        },
    )

    builder.add_conditional_edges(
        "verify_requirements",
        route_phase,
        {
            "plan": "plan",
            "refine": "refine",
            "discover": "discover",
        },
    )

    builder.add_conditional_edges(
        "plan",
        route_phase,
        {
            "approve": "approve",
        },
    )

    builder.add_conditional_edges(
        "approve",
        route_phase,
        {
            "execute": "execute",
            "plan": "plan",
        },
    )

    builder.add_conditional_edges(
        "execute",
        route_phase,
        {
            "verify_execution": "verify_execution",
        },
    )

    builder.add_conditional_edges(
        "verify_execution",
        route_phase,
        {
            "complete": END,
            "execute": "execute",
        },
    )

    # Compile with checkpointing for persistence
    memory = MemorySaver()
    return builder.compile(checkpointer=memory)


# Singleton graph instance
graph = build_graph()
