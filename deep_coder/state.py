"""State definitions for the deep-coder workflow."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from langgraph.graph import MessagesState


class Phase(str, Enum):
    """Workflow phases - the agent must progress through these in order."""

    DISCOVER = "discover"
    REFINE = "refine"
    VERIFY_REQUIREMENTS = "verify_requirements"
    PLAN = "plan"
    APPROVE = "approve"
    EXECUTE = "execute"
    VERIFY_EXECUTION = "verify_execution"
    COMPLETE = "complete"


class VerificationStep(BaseModel):
    """A single verification step for a task."""

    description: str
    command: str  # Shell command to run
    expected: str  # What the output should contain/match
    category: str = "shell"  # shell, http, log, state, integration


class Task(BaseModel):
    """A single task in the execution plan."""

    id: int
    title: str
    description: str
    verification: list[VerificationStep] = Field(default_factory=list)
    status: str = "pending"  # pending, in_progress, passed, failed
    evidence: str = ""  # Actual output from verification


class Requirements(BaseModel):
    """Requirements document that evolves through refinement."""

    version: int = 1
    summary: str = ""
    details: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    codebase_context: str = ""
    refinement_notes: list[str] = Field(default_factory=list)


class DeepCoderState(MessagesState):
    """Full state for the deep-coder workflow."""

    # Current phase
    phase: Phase = Phase.DISCOVER

    # Requirements (evolves through DISCOVER → REFINE → VERIFY)
    requirements: dict = Field(default_factory=dict)
    refinement_count: int = 0
    max_refinements: int = 3

    # Execution plan (created in PLAN phase)
    tasks: list[dict] = Field(default_factory=list)
    current_task_index: int = 0

    # Codebase context
    project_path: str = ""
    file_tree: str = ""

    # Human decisions
    requirements_approved: bool = False
    plan_approved: bool = False

    # Verification results
    verification_results: list[dict] = Field(default_factory=list)
