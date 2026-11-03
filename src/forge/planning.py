from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlanStep:
    """A single step in a task plan."""

    name: str
    status: str = "pending"
    notes: str = ""
    verification: str = ""
    depends_on: list[str] = field(default_factory=list)

    VALID_STATUSES = {"pending", "in_progress", "done", "blocked"}

    def __post_init__(self) -> None:
        if self.status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid plan step status: {self.status}")


@dataclass
class AgentPlan:
    """A task-specific, dependency-aware execution plan."""

    objective: str
    steps: list[PlanStep] = field(default_factory=list)

    def add_step(
        self,
        name: str,
        verification: str = "",
        depends_on: list[str] | None = None,
    ) -> PlanStep:
        step = PlanStep(
            name=name,
            verification=verification,
            depends_on=list(depends_on or []),
        )
        self.steps.append(step)
        return step

    def replace_steps(self, steps: list[dict[str, Any]]) -> None:
        names: set[str] = set()
        replacement: list[PlanStep] = []
        for item in steps:
            name = str(item.get("name", "")).strip()
            if not name:
                raise ValueError("Plan step names cannot be empty.")
            if name in names:
                raise ValueError(f"Duplicate plan step: {name}")
            names.add(name)
            replacement.append(
                PlanStep(
                    name=name,
                    status=str(item.get("status", "pending")),
                    notes=str(item.get("notes", "")),
                    verification=str(item.get("verification", "")),
                    depends_on=[str(value) for value in item.get("depends_on", [])],
                )
            )
        if replacement:
            errors: list[str] = []
            for step in replacement:
                for dependency in step.depends_on:
                    if dependency == step.name:
                        errors.append(f"{step.name} depends on itself.")
                    elif dependency not in names:
                        errors.append(f"{step.name} has unknown dependency {dependency}.")
            if errors:
                raise ValueError("; ".join(errors))
            self.steps = replacement

    def validate_dependencies(self) -> list[str]:
        names = {step.name for step in self.steps}
        errors: list[str] = []
        for step in self.steps:
            for dependency in step.depends_on:
                if dependency == step.name:
                    errors.append(f"{step.name} depends on itself.")
                elif dependency not in names:
                    errors.append(f"{step.name} has unknown dependency {dependency}.")
        return errors

    def get_step(self, name: str) -> PlanStep:
        for step in self.steps:
            if step.name == name:
                return step
        raise ValueError(f"Unknown step: {name}")

    def ready_steps(self) -> list[PlanStep]:
        name_to_step = {step.name: step for step in self.steps}
        return [
            step
            for step in self.steps
            if step.status in {"pending", "in_progress"}
            and all(
                dependency in name_to_step
                and name_to_step[dependency].status == "done"
                for dependency in step.depends_on
            )
        ]

    def start_step(self, name: str) -> None:
        step = self.get_step(name)
        if step.status == "done":
            raise ValueError(f"Plan step is already done: {name}")
        if self.validate_dependencies():
            raise ValueError("; ".join(self.validate_dependencies()))
        for dependency in step.depends_on:
            if self.get_step(dependency).status != "done":
                raise ValueError(f"Dependencies are not complete for: {name}")
        step.status = "in_progress"

    def mark_step_done(self, name: str) -> None:
        self.get_step(name).status = "done"

    def mark_step_pending(self, name: str) -> None:
        self.get_step(name).status = "pending"

    def mark_step_blocked(self, name: str, reason: str) -> None:
        step = self.get_step(name)
        step.status = "blocked"
        step.notes = reason

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
                {
                    "name": step.name,
                    "status": step.status,
                    "notes": step.notes,
                    "verification": step.verification,
                    "depends_on": step.depends_on,
                }
                for step in self.steps
            ],
        }


class PlanManager:
    """Plan lifecycle and bounded repair manager."""

    def __init__(self, objective: str, max_retries: int = 3) -> None:
        self.plan = AgentPlan(objective=objective)
        self.failure_count = 0
        self.max_retries = max_retries

    def add_step(
        self,
        name: str,
        verification: str = "",
        depends_on: list[str] | None = None,
    ) -> PlanStep:
        return self.plan.add_step(name, verification, depends_on)

    def replace_plan(self, steps: list[dict[str, Any]]) -> None:
        if not steps:
            raise ValueError("A plan must contain at least one step.")
        self.plan.replace_steps(steps)

    def start_step(self, name: str) -> None:
        self.plan.start_step(name)

    def mark_step_done(self, name: str) -> None:
        self.plan.mark_step_done(name)

    def mark_step_pending(self, name: str) -> None:
        self.plan.mark_step_pending(name)

    def mark_step_blocked(self, name: str, reason: str) -> None:
        self.plan.mark_step_blocked(name, reason)

    def ready_steps(self) -> list[PlanStep]:
        return self.plan.ready_steps()

    def apply_tool_progress(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        del arguments
        if result.get("status") != "ok":
            return
        if tool_name in {"inspect_repo", "list_files", "read_file", "search_files"}:
            self._complete_matching(("inspect", "investigate", "research"))
            return
        if tool_name in {"create_file", "replace_file", "edit_file", "write_file"}:
            self._complete_matching(("implement", "fix", "patch", "change"))
            return
        if tool_name == "run_command":
            nested = result.get("result")
            if isinstance(nested, dict) and nested.get("returncode") == 0:
                self._complete_matching(("verify", "test", "check"))

    def _complete_matching(self, words: tuple[str, ...]) -> None:
        for step in self.ready_steps():
            if any(word in step.name.lower() for word in words):
                self.mark_step_done(step.name)
                return

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
