"""SSL/TLS certificate inspection."""

from __future__ import annotations

import socket
import ssl
from datetime import UTC, datetime

from deploydoctor.models import CheckResult, Status

WARN_DAYS = 30


def _parse_cert_time(value: str) -> datetime:
    """Parse openssl-style cert timestamps like 'Mar  5 12:00:00 2027 GMT'.

    `%Z` parsing is platform-dependent for non-local timezone names, so
    fall back to stripping the trailing tz token and parsing as UTC.
    """
    try:
        return datetime.strptime(value, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC)
    except ValueError:
        pass
    # Strip trailing alphabetic tz token (e.g. "GMT"/"UTC") if present.
    parts = value.rsplit(" ", 1)
    candidate = parts[0] if len(parts) == 2 and parts[1].isalpha() else value
    return datetime.strptime(candidate, "%b %d %H:%M:%S %Y").replace(tzinfo=UTC)


def _flatten(seq) -> dict[str, str]:
    out: dict[str, str] = {}
    for pair in seq:
        for k, v in pair:
            out[k] = v
    return out


def check_ssl(domain: str, port: int = 443, timeout: float = 6.0) -> CheckResult:
    """Connect to domain:port over TLS and inspect the peer certificate."""
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((domain, port), timeout=timeout) as raw:
            with ctx.wrap_socket(raw, server_hostname=domain) as tls:
                cert = tls.getpeercert()
    except ssl.SSLCertVerificationError as e:
        return CheckResult(
            name="SSL",
            status=Status.FAIL,
            message=f"Certificate verification failed: {e.verify_message or e}",
            suggestions=[
                f"openssl s_client -connect {domain}:{port} -servername {domain}",
                "Verify full chain (cert + intermediates) is served",
            ],
        )
    except ssl.SSLError as e:
        return CheckResult(
            name="SSL",
            status=Status.FAIL,
            message=f"TLS error: {e}",
            suggestions=[f"openssl s_client -connect {domain}:{port} -servername {domain}"],
        )
    except TimeoutError:
        return CheckResult(
            name="SSL",
            status=Status.FAIL,
            message=f"TLS connect timeout to {domain}:{port}",
            suggestions=["Check firewall rules on 443"],
        )
    except ConnectionRefusedError:
        return CheckResult(
            name="SSL",
            status=Status.SKIP,
            message=f"Port {port} refused; domain may not serve TLS",
        )
    except OSError as e:
        return CheckResult(
            name="SSL",
            status=Status.FAIL,
            message=f"Connect error: {e}",
        )

    if not cert:
        return CheckResult(
            name="SSL",
            status=Status.WARN,
            message="No peer certificate returned",
        )

    subject = _flatten(cert.get("subject", ()))
    issuer = _flatten(cert.get("issuer", ()))
    not_after = cert.get("notAfter")
    if not not_after:
        return CheckResult(name="SSL", status=Status.WARN, message="Certificate has no expiry date")

    try:
        expiry = _parse_cert_time(not_after)
    except ValueError as e:
        return CheckResult(name="SSL", status=Status.WARN, message=f"Cannot parse expiry: {e}")

    now = datetime.now(tz=UTC)
    days_left = (expiry - now).days

    cn = subject.get("commonName", "?")
    issuer_cn = issuer.get("commonName") or issuer.get("organizationName", "?")

    details = [
        f"Subject CN: {cn}",
        f"Issuer: {issuer_cn}",
        f"Expires: {expiry.isoformat()} ({days_left} days)",
    ]

    if days_left < 0:
        return CheckResult(
            name="SSL",
            status=Status.FAIL,
            message=f"Certificate expired {abs(days_left)} day(s) ago",
            details=details,
            suggestions=["Renew certificate (e.g. `sudo certbot renew`)"],
        )
    if days_left < WARN_DAYS:
        return CheckResult(
            name="SSL",
            status=Status.WARN,
            message=f"Certificate expires in {days_left} day(s)",
            details=details,
            suggestions=["Schedule renewal (`sudo certbot renew --dry-run` to verify automation)"],
        )
    return CheckResult(
        name="SSL",
        status=Status.PASS,
        message=f"Valid certificate ({days_left} days remaining)",
        details=details,
    )
