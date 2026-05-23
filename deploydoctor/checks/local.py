"""Local Linux server diagnostics. All checks are defensive and optional."""

from __future__ import annotations

import os
import platform

from deploydoctor.models import CheckResult, Status
from deploydoctor.utils.subprocess import has_command, run

NGINX_ERROR_LOG = "/var/log/nginx/error.log"


def _is_linux() -> bool:
    return platform.system() == "Linux"


def _skip_non_linux(name: str) -> CheckResult:
    return CheckResult(
        name=name,
        status=Status.SKIP,
        message=f"Local check skipped on {platform.system()}",
    )


def check_nginx_installed() -> CheckResult:
    if not _is_linux():
        return _skip_non_linux("Nginx installed")
    if has_command("nginx"):
        return CheckResult(name="Nginx installed", status=Status.PASS, message="nginx found on PATH")
    return CheckResult(
        name="Nginx installed",
        status=Status.SKIP,
        message="nginx not found on PATH",
    )


def check_docker_installed() -> CheckResult:
    if not _is_linux():
        return _skip_non_linux("Docker installed")
    if has_command("docker"):
        return CheckResult(name="Docker installed", status=Status.PASS, message="docker found on PATH")
    return CheckResult(
        name="Docker installed",
        status=Status.SKIP,
        message="docker not found on PATH",
    )


def check_listening_ports() -> CheckResult:
    if not _is_linux():
        return _skip_non_linux("Listening ports")
    if not has_command("ss"):
        return CheckResult(
            name="Listening ports",
            status=Status.SKIP,
            message="`ss` not available",
        )
    res = run(["ss", "-tulpn"], timeout=6.0)
    if res.timed_out:
        return CheckResult(name="Listening ports", status=Status.WARN, message="`ss -tulpn` timed out")
    if res.error:
        return CheckResult(name="Listening ports", status=Status.SKIP, message=res.error)
    if res.returncode != 0:
        return CheckResult(
            name="Listening ports",
            status=Status.WARN,
            message=f"`ss` returned {res.returncode}",
            details=[res.stderr.strip()] if res.stderr.strip() else [],
        )
    lines = [ln for ln in res.stdout.splitlines() if ln.strip()]
    head = lines[:20]
    overflow = len(lines) - len(head)
    details = head + ([f"… ({overflow} more line(s))"] if overflow > 0 else [])
    return CheckResult(
        name="Listening ports",
        status=Status.PASS,
        message=f"Found {len(lines)} line(s) of listening sockets",
        details=details,
    )


def check_nginx_config() -> CheckResult:
    if not _is_linux():
        return _skip_non_linux("Nginx config test")
    if not has_command("nginx"):
        return CheckResult(name="Nginx config test", status=Status.SKIP, message="nginx not installed")
    res = run(["nginx", "-t"], timeout=8.0)
    if res.timed_out:
        return CheckResult(name="Nginx config test", status=Status.WARN, message="`nginx -t` timed out")
    output = (res.stderr or res.stdout or "").strip()
    if res.error:
        return CheckResult(name="Nginx config test", status=Status.SKIP, message=res.error)
    if res.returncode == 0:
        return CheckResult(
            name="Nginx config test",
            status=Status.PASS,
            message="nginx config syntax is OK",
            details=[output] if output else [],
        )
    suggestions = ["sudo nginx -t", "Fix syntax errors before `sudo systemctl reload nginx`"]
    if "permission denied" in output.lower():
        return CheckResult(
            name="Nginx config test",
            status=Status.SKIP,
            message="permission denied (try with sudo)",
            details=[output],
        )
    return CheckResult(
        name="Nginx config test",
        status=Status.FAIL,
        message="nginx config has errors",
        details=[output] if output else [],
        suggestions=suggestions,
    )


def check_nginx_error_log(path: str = NGINX_ERROR_LOG, lines: int = 30) -> CheckResult:
    if not _is_linux():
        return _skip_non_linux("Nginx error log")
    if not os.path.exists(path):
        return CheckResult(name="Nginx error log", status=Status.SKIP, message=f"{path} not found")
    if not os.access(path, os.R_OK):
        return CheckResult(
            name="Nginx error log",
            status=Status.SKIP,
            message=f"permission denied reading {path}",
            suggestions=[f"sudo tail -n {lines} {path}"],
        )
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            data = f.readlines()
    except OSError as e:
        return CheckResult(name="Nginx error log", status=Status.SKIP, message=f"read error: {e}")
    tail = [ln.rstrip("\n") for ln in data[-lines:]]
    if not tail:
        return CheckResult(name="Nginx error log", status=Status.PASS, message="log empty")
    has_error = any(("error" in ln.lower() or "crit" in ln.lower() or "alert" in ln.lower()) for ln in tail)
    return CheckResult(
        name="Nginx error log",
        status=Status.WARN if has_error else Status.PASS,
        message=f"showing last {len(tail)} line(s)" + (" (errors present)" if has_error else ""),
        details=tail,
    )


def check_docker_containers() -> CheckResult:
    if not _is_linux():
        return _skip_non_linux("Docker containers")
    if not has_command("docker"):
        return CheckResult(name="Docker containers", status=Status.SKIP, message="docker not installed")
    res = run(["docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"], timeout=6.0)
    if res.timed_out:
        return CheckResult(name="Docker containers", status=Status.WARN, message="`docker ps` timed out")
    if res.error:
        return CheckResult(name="Docker containers", status=Status.SKIP, message=res.error)
    if res.returncode != 0:
        stderr = res.stderr.strip()
        if "permission denied" in stderr.lower() or "cannot connect" in stderr.lower():
            return CheckResult(
                name="Docker containers",
                status=Status.SKIP,
                message="cannot talk to docker daemon (permission or socket)",
                details=[stderr] if stderr else [],
                suggestions=["sudo docker ps", "Add user to `docker` group"],
            )
        return CheckResult(
            name="Docker containers",
            status=Status.WARN,
            message=f"`docker ps` returned {res.returncode}",
            details=[stderr] if stderr else [],
        )
    lines = [ln for ln in res.stdout.splitlines() if ln.strip()]
    if not lines:
        return CheckResult(name="Docker containers", status=Status.PASS, message="no running containers")
    return CheckResult(
        name="Docker containers",
        status=Status.PASS,
        message=f"{len(lines)} running container(s)",
        details=lines,
    )


def run_local_checks() -> list[CheckResult]:
    """Run all defensive local checks. Never raises."""
    return [
        check_nginx_installed(),
        check_docker_installed(),
        check_listening_ports(),
        check_nginx_config(),
        check_nginx_error_log(),
        check_docker_containers(),
    ]
