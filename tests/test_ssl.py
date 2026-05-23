from datetime import UTC, datetime, timedelta

from deploydoctor.checks import ssl_check
from deploydoctor.checks.ssl_check import _parse_cert_time, check_ssl
from deploydoctor.models import Status


def test_parse_cert_time_gmt():
    dt = _parse_cert_time("Mar  5 12:00:00 2027 GMT")
    assert dt.year == 2027
    assert dt.tzinfo is UTC


def test_parse_cert_time_fallback_no_tz():
    dt = _parse_cert_time("Mar  5 12:00:00 2027")
    assert dt.year == 2027


class _FakeTLS:
    def __init__(self, cert):
        self._cert = cert

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def getpeercert(self):
        return self._cert


class _FakeRaw:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeCtx:
    def __init__(self, cert):
        self._cert = cert

    def wrap_socket(self, raw, server_hostname=None):
        return _FakeTLS(self._cert)


def _make_cert(days_left: int):
    expiry = datetime.now(tz=UTC) + timedelta(days=days_left)
    not_after = expiry.strftime("%b %d %H:%M:%S %Y GMT")
    return {
        "subject": ((("commonName", "example.com"),),),
        "issuer": ((("commonName", "Test CA"),),),
        "notAfter": not_after,
    }


def _patch_connect(monkeypatch, cert):
    monkeypatch.setattr(ssl_check.socket, "create_connection", lambda *a, **k: _FakeRaw())
    monkeypatch.setattr(ssl_check.ssl, "create_default_context", lambda: _FakeCtx(cert))


def test_ssl_pass_for_long_valid_cert(monkeypatch):
    _patch_connect(monkeypatch, _make_cert(90))
    r = check_ssl("example.com")
    assert r.status == Status.PASS
    assert "90" in r.message or "89" in r.message


def test_ssl_warns_under_30_days(monkeypatch):
    _patch_connect(monkeypatch, _make_cert(10))
    r = check_ssl("example.com")
    assert r.status == Status.WARN
    assert "10" in r.message or "9" in r.message


def test_ssl_fails_when_expired(monkeypatch):
    _patch_connect(monkeypatch, _make_cert(-2))
    r = check_ssl("example.com")
    assert r.status == Status.FAIL
    assert "expired" in r.message.lower()


def test_ssl_refused_returns_skip(monkeypatch):
    def raise_refused(*a, **k):
        raise ConnectionRefusedError

    monkeypatch.setattr(ssl_check.socket, "create_connection", raise_refused)
    r = check_ssl("example.com")
    assert r.status == Status.SKIP


def test_ssl_verification_error_fail(monkeypatch):
    import ssl as _ssl

    def raise_verify(*a, **k):
        err = _ssl.SSLCertVerificationError("verify failed")
        err.verify_message = "self signed certificate"
        raise err

    monkeypatch.setattr(ssl_check.socket, "create_connection", lambda *a, **k: _FakeRaw())

    class _BadCtx:
        def wrap_socket(self, raw, server_hostname=None):
            raise_verify()

    monkeypatch.setattr(ssl_check.ssl, "create_default_context", lambda: _BadCtx())
    r = check_ssl("example.com")
    assert r.status == Status.FAIL
    assert "verif" in r.message.lower()
