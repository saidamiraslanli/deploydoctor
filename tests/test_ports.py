from deploydoctor.checks import ports as ports_mod
from deploydoctor.checks.ports import check_ports
from deploydoctor.models import Status


def test_ports_all_open(monkeypatch):
    monkeypatch.setattr(ports_mod, "_probe", lambda h, p, t: ("open", None))
    r = check_ports("example.com")
    assert r.status == Status.PASS
    assert any("80" in d for d in r.details)
    assert any("443" in d for d in r.details)


def test_ports_mixed_warn(monkeypatch):
    def probe(h, p, t):
        return ("open", None) if p == 443 else ("timeout", None)

    monkeypatch.setattr(ports_mod, "_probe", probe)
    r = check_ports("example.com")
    assert r.status == Status.WARN


def test_ports_all_closed_fail(monkeypatch):
    monkeypatch.setattr(ports_mod, "_probe", lambda h, p, t: ("closed", "refused"))
    r = check_ports("example.com")
    assert r.status == Status.FAIL
    assert r.suggestions
