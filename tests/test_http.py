import httpx

from deploydoctor.checks.http import check_http, check_https
from deploydoctor.models import Status

_REAL_CLIENT = httpx.Client


def _client_with(handler):
    """Return a factory that builds a real httpx.Client wired to a MockTransport."""
    transport = httpx.MockTransport(handler)

    def _factory(*args, **kwargs):
        kwargs.pop("verify", None)
        kwargs["transport"] = transport
        return _REAL_CLIENT(*args, **kwargs)

    return _factory


def test_http_200(monkeypatch):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="ok", headers={"server": "nginx"})

    monkeypatch.setattr("deploydoctor.checks.http.httpx.Client", _client_with(handler))
    r = check_http("example.com")
    assert r.status == Status.PASS
    assert "200" in r.message


def test_https_502(monkeypatch):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="bad gateway")

    monkeypatch.setattr("deploydoctor.checks.http.httpx.Client", _client_with(handler))
    r = check_https("example.com")
    assert r.status == Status.FAIL
    assert "502" in r.message
    assert any("nginx" in s.lower() or "ss -tulpn" in s for s in r.suggestions)


def test_http_404_warn(monkeypatch):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="nope")

    monkeypatch.setattr("deploydoctor.checks.http.httpx.Client", _client_with(handler))
    r = check_http("example.com")
    assert r.status == Status.WARN
    assert "404" in r.message


def test_http_connect_refused(monkeypatch):
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr("deploydoctor.checks.http.httpx.Client", _client_with(handler))
    r = check_http("example.com")
    assert r.status == Status.FAIL
    assert "refused" in r.message.lower()


def test_http_connect_timeout(monkeypatch):
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout")

    monkeypatch.setattr("deploydoctor.checks.http.httpx.Client", _client_with(handler))
    r = check_https("example.com")
    assert r.status == Status.FAIL
    assert "timeout" in r.message.lower()
