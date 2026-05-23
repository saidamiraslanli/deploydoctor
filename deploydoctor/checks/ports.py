"""External port reachability checks (TCP connect)."""

from __future__ import annotations

import socket

from deploydoctor.models import CheckResult, Status


def _probe(host: str, port: int, timeout: float) -> tuple[str, str | None]:
    """Return (state, detail). state ∈ {'open','closed','timeout','error'}."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return "open", None
    except TimeoutError:
        return "timeout", None
    except ConnectionRefusedError:
        return "closed", "connection refused"
    except OSError as e:
        return "error", str(e)


def check_ports(domain: str, ports: tuple[int, ...] = (80, 443), timeout: float = 4.0) -> CheckResult:
    """Probe TCP reachability for the given ports."""
    details: list[str] = []
    any_open = False
    any_bad = False
    for p in ports:
        state, info = _probe(domain, p, timeout)
        line = f"Port {p}: {state}"
        if info:
            line += f" ({info})"
        details.append(line)
        if state == "open":
            any_open = True
        else:
            any_bad = True

    if any_open and not any_bad:
        return CheckResult(name="Ports", status=Status.PASS, message="All probed ports open", details=details)
    if any_open and any_bad:
        return CheckResult(
            name="Ports",
            status=Status.WARN,
            message="Some ports not reachable",
            details=details,
            suggestions=["Verify firewall / security group / nginx listen directives"],
        )
    return CheckResult(
        name="Ports",
        status=Status.FAIL,
        message="No probed ports reachable",
        details=details,
        suggestions=[
            "Verify the server is running and bound to a public interface",
            "Check cloud firewall and host iptables/ufw rules",
        ],
    )
