"""DNS A/AAAA record checks."""

from __future__ import annotations

import dns.exception
import dns.rdatatype
import dns.resolver

from deploydoctor.models import CheckResult, Status


def _resolve(domain: str, rdtype: str, timeout: float) -> tuple[list[str], str | None]:
    resolver = dns.resolver.Resolver()
    resolver.lifetime = timeout
    resolver.timeout = timeout
    try:
        answer = resolver.resolve(domain, rdtype)
        return [r.to_text() for r in answer], None
    except dns.resolver.NoAnswer:
        return [], "no_answer"
    except dns.resolver.NXDOMAIN:
        return [], "nxdomain"
    except dns.resolver.NoNameservers:
        return [], "no_nameservers"
    except dns.exception.Timeout:
        return [], "timeout"
    except dns.exception.DNSException as e:
        return [], f"dns_error: {e}"


def check_dns(domain: str, timeout: float = 5.0) -> CheckResult:
    """Resolve A and AAAA records for `domain`."""
    a_records, a_err = _resolve(domain, "A", timeout)
    aaaa_records, aaaa_err = _resolve(domain, "AAAA", timeout)

    details: list[str] = []
    for ip in a_records:
        details.append(f"A: {ip}")
    for ip in aaaa_records:
        details.append(f"AAAA: {ip}")

    if a_records or aaaa_records:
        msg_parts = []
        if a_records:
            msg_parts.append(f"{len(a_records)} A")
        if aaaa_records:
            msg_parts.append(f"{len(aaaa_records)} AAAA")
        return CheckResult(
            name="DNS",
            status=Status.PASS,
            message=f"Resolved {' / '.join(msg_parts)} record(s)",
            details=details,
        )

    if a_err == "nxdomain":
        return CheckResult(
            name="DNS",
            status=Status.FAIL,
            message=f"NXDOMAIN: {domain} does not exist",
            suggestions=[
                f"dig {domain}",
                "Verify domain registration and nameservers at your registrar",
            ],
        )
    if a_err == "timeout" or aaaa_err == "timeout":
        return CheckResult(
            name="DNS",
            status=Status.FAIL,
            message="DNS resolution timed out",
            suggestions=[
                f"dig +trace {domain}",
                "Check upstream resolver / firewall rules on port 53",
            ],
        )
    return CheckResult(
        name="DNS",
        status=Status.FAIL,
        message=f"No A/AAAA records found ({a_err or 'unknown'})",
        suggestions=[
            f"dig {domain} A",
            f"dig {domain} AAAA",
            "Verify zone records at your DNS provider",
        ],
    )
