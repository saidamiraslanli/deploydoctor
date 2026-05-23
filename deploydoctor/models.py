"""Core data models for DeployDoctor check results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Status(StrEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class CheckResult:
    name: str
    status: Status
    message: str = ""
    details: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == Status.PASS

    @property
    def warned(self) -> bool:
        return self.status == Status.WARN

    @property
    def failed(self) -> bool:
        return self.status == Status.FAIL

    @property
    def skipped(self) -> bool:
        return self.status == Status.SKIP


@dataclass
class Report:
    domain: str | None
    results: list[CheckResult] = field(default_factory=list)

    def add(self, result: CheckResult) -> None:
        self.results.append(result)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def warn_count(self) -> int:
        return sum(1 for r in self.results if r.warned)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if r.failed)

    @property
    def skipped_count(self) -> int:
        return sum(1 for r in self.results if r.skipped)

    @property
    def most_likely_issue(self) -> str | None:
        for r in self.results:
            if r.failed:
                return f"{r.name}: {r.message}"
        for r in self.results:
            if r.warned:
                return f"{r.name}: {r.message}"
        return None

    @property
    def next_commands(self) -> list[str]:
        cmds: list[str] = []
        seen: set[str] = set()
        for r in self.results:
            if r.failed or r.warned:
                for s in r.suggestions:
                    if s not in seen:
                        seen.add(s)
                        cmds.append(s)
        return cmds
