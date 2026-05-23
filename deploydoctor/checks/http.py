"""HTTP / HTTPS connectivity and response checks."""

from __future__ import annotations

import time

import httpx

from deploydoctor.models import CheckResult, Status


def _classify_status(code: int) -> tuple[Status, str, list[str]]:
    if 200 <= code < 300:
        return Status.PASS, f"{code} OK", []
    if 300 <= code < 400:
        return Status.WARN, f"{code} redirect", ["Inspect Location header / redirect chain"]
    if code in (502, 503, 504):
        return (
            Status.FAIL,
            f"{code} gateway error",
            [
                "Possible cause: reverse proxy cannot reach upstream app",
                "sudo systemctl status nginx",
                "sudo tail -n 50 /var/log/nginx/error.log",
                "ss -tulpn",
            ],
        )
    if 500 <= code < 600:
        return Status.FAIL, f"{code} server error", ["Check application logs and recent deploys"]
    if code == 404:
        return Status.WARN, "404 Not Found", ["Verify route / virtual host config"]
    if code == 401 or code == 403:
        return Status.WARN, f"{code} auth/forbidden", ["Check auth headers, IP allowlists, basic-auth config"]
    if 400 <= code < 500:
        return Status.WARN, f"{code} client error", ["Verify the request path / method"]
    return Status.WARN, f"unexpected status {code}", []


def _check_url(url: str, timeout: float, verify: bool = True) -> CheckResult:
    name = "HTTP" if url.startswith("http://") else "HTTPS"
    start = time.perf_counter()
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout, verify=verify) as client:
            resp = client.get(url, headers={"User-Agent": "DeployDoctor/0.1"})
    except httpx.TooManyRedirects:
        return CheckResult(
            name=name,
            status=Status.FAIL,
            message="Too many redirects",
            suggestions=["Inspect redirect chain for loops (curl -ILs)"],
        )
    except httpx.ConnectTimeout:
        return CheckResult(
            name=name,
            status=Status.FAIL,
            message="Connection timeout",
            suggestions=[
                "Verify firewall / security group allows inbound on 80/443",
                f"curl -v --connect-timeout 5 {url}",
            ],
        )
    except httpx.ReadTimeout:
        return CheckResult(
            name=name,
            status=Status.FAIL,
            message="Read timeout (server accepted connection but did not respond in time)",
            suggestions=["Check upstream app performance / worker saturation"],
        )
    except httpx.ConnectError as e:
        emsg = str(e)
        low = emsg.lower()
        if "certificate" in low or "ssl" in low or "tls" in low:
            host = url.split("://", 1)[1].rstrip("/")
            return CheckResult(
                name=name,
                status=Status.FAIL,
                message=f"SSL verification failure: {emsg}",
                suggestions=[
                    f"openssl s_client -connect {host}:443 -servername {host}",
                    "Verify intermediate chain is served (ssl_certificate fullchain)",
                ],
            )
        if "refused" in low:
            return CheckResult(
                name=name,
                status=Status.FAIL,
                message="Connection refused",
                suggestions=[
                    "Service not listening on this port",
                    "sudo systemctl status nginx",
                    "ss -tulpn",
                ],
            )
        return CheckResult(
            name=name,
            status=Status.FAIL,
            message=f"Connection error: {emsg}",
            suggestions=[f"curl -v {url}"],
        )
    except httpx.HTTPError as e:
        return CheckResult(
            name=name,
            status=Status.FAIL,
            message=f"{type(e).__name__}: {e}",
            suggestions=[f"curl -v {url}"],
        )

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    server = resp.headers.get("server", "")
    is_cloudflare = "cloudflare" in server.lower()

    if resp.status_code == 525 and is_cloudflare:
        domain = url.split("://", 1)[1].split("/")[0]
        status = Status.FAIL
        msg = "Cloudflare 525 SSL handshake failed: Cloudflare could reach the origin, but TLS negotiation between Cloudflare and the origin server failed."
        suggestions: list[str] = [
            "sudo nginx -T | grep -E 'listen 443|ssl_certificate'",
            "sudo nginx -t",
            f"openssl s_client -connect {domain}:443 -servername {domain}",
            "Cloudflare dashboard → SSL/TLS: Full requires TLS on origin; Full (strict) requires a valid trusted cert",
            "sudo tail -n 50 /var/log/nginx/error.log",
        ]
    else:
        status, msg, suggestions = _classify_status(resp.status_code)

    details: list[str] = [
        f"Final URL: {resp.url}",
        f"Time: {elapsed_ms:.0f} ms",
    ]
    if resp.history:
        chain = " -> ".join(str(h.url) for h in resp.history)
        details.append(f"Redirects: {chain} -> {resp.url}")
    if server:
        details.append(f"Server: {server}")

    return CheckResult(name=name, status=status, message=msg, details=details, suggestions=suggestions)


def check_http(domain: str, timeout: float = 8.0) -> CheckResult:
    return _check_url(f"http://{domain}", timeout=timeout)


def check_https(domain: str, timeout: float = 8.0) -> CheckResult:
    return _check_url(f"https://{domain}", timeout=timeout)
