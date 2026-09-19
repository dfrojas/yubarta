"""Bounded Docker operations for the automated Java scenario only."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


def docker(*args: str, timeout: float = 15.0) -> str:
    result = subprocess.run(
        ["docker", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode:
        raise RuntimeError(f"docker {' '.join(args)} failed: {result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def build_image(image: str) -> None:
    scenario = Path(__file__).parent / "scenarios" / "java"
    docker("build", "-t", image, str(scenario), timeout=300.0)


def mapped_port(name: str, container_port: int) -> int:
    return int(docker("port", name, f"{container_port}/tcp").rsplit(":", 1)[1])


@dataclass(frozen=True)
class Sandbox:
    name: str
    ssh_port: int
    http_port: int

    @property
    def health_url(self) -> str:
        return f"http://127.0.0.1:{self.http_port}/health"

    def run(self, *command: str) -> str:
        return docker("exec", self.name, *command)

    def diagnostics(self) -> str:
        sections: list[str] = []
        for args in (
            ("inspect", "--format", "{{json .State}}", self.name),
            ("logs", "--tail", "100", self.name),
        ):
            try:
                sections.append(docker(*args, timeout=5.0))
            except (RuntimeError, subprocess.TimeoutExpired) as exc:
                sections.append(str(exc))
        return "\n".join(sections)
