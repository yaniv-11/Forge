from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlanStep:
    """A single step in a task plan."""

    name: str
    status: str = "pending"
    notes: str = ""


@dataclass
class AgentPlan:
    """A lightweight execution plan for a coding task."""

    objective: str
    steps: list[PlanStep] = field(default_factory=list)

    def add_step(self, name: str) -> PlanStep:
        step = PlanStep(name=name)
        self.steps.append(step)
        return step

    def mark_step_done(self, name: str) -> None:
        for step in self.steps:
            if step.name == name:
                step.status = "done"
                return
        raise ValueError(f"Unknown step: {name}")

    def mark_step_pending(self, name: str) -> None:
        for step in self.steps:
            if step.name == name:
                step.status = "pending"
                return
        raise ValueError(f"Unknown step: {name}")

    @property
    def status(self) -> str:
        if not self.steps:
            return "pending"
        if all(step.status == "done" for step in self.steps):
            return "done"
        return "in_progress"

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "status": self.status,
            "steps": [
                {"name": step.name, "status": step.status, "notes": step.notes}
                for step in self.steps
            ],
        }


class PlanManager:
    """Simple plan manager with bounded self-correction."""

    def __init__(self, objective: str, max_retries: int = 3) -> None:
        self.plan = AgentPlan(objective=objective)
        self.failure_count = 0
        self.max_retries = max_retries

    def add_step(self, name: str) -> PlanStep:
        return self.plan.add_step(name)

    def mark_step_done(self, name: str) -> None:
        self.plan.mark_step_done(name)

    def record_failure(self, reason: str) -> None:
        self.failure_count += 1
        if not self.plan.steps:
            self.add_step("diagnose failure")
        last_step = self.plan.steps[-1]
        last_step.notes = reason
        last_step.status = "blocked"

    def should_replan(self) -> bool:
        return self.failure_count > 0 and self.failure_count <= self.max_retries

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective": self.plan.objective,
            "status": self.plan.status,
            "failure_count": self.failure_count,
            "max_retries": self.max_retries,
            "steps": self.plan.to_dict()["steps"],
        }
