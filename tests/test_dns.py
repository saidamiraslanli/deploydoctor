from unittest.mock import patch

import dns.exception
import dns.resolver

from deploydoctor.checks.dns import check_dns
from deploydoctor.models import Status


class _FakeRR:
    def __init__(self, text):
        self._t = text

    def to_text(self):
        return self._t


def _fake_resolve_factory(a_results=None, aaaa_results=None, a_exc=None, aaaa_exc=None):
    def _resolve(_self, name, rdtype):
        if rdtype == "A":
            if a_exc:
                raise a_exc
            return [_FakeRR(x) for x in (a_results or [])]
        if rdtype == "AAAA":
            if aaaa_exc:
                raise aaaa_exc
            return [_FakeRR(x) for x in (aaaa_results or [])]
        return []

    return _resolve


def test_dns_pass_with_a_record():
    with patch.object(
        dns.resolver.Resolver,
        "resolve",
        _fake_resolve_factory(a_results=["93.184.216.34"], aaaa_exc=dns.resolver.NoAnswer()),
    ):
        result = check_dns("example.com")
    assert result.status == Status.PASS
    assert any("93.184.216.34" in d for d in result.details)


def test_dns_pass_with_both_records():
    with patch.object(
        dns.resolver.Resolver,
        "resolve",
        _fake_resolve_factory(a_results=["1.1.1.1"], aaaa_results=["::1"]),
    ):
        result = check_dns("example.com")
    assert result.status == Status.PASS
    assert any("AAAA" in d for d in result.details)


def test_dns_nxdomain():
    with patch.object(
        dns.resolver.Resolver,
        "resolve",
        _fake_resolve_factory(a_exc=dns.resolver.NXDOMAIN(), aaaa_exc=dns.resolver.NXDOMAIN()),
    ):
        result = check_dns("nope.invalid.")
    assert result.status == Status.FAIL
    assert "NXDOMAIN" in result.message


def test_dns_timeout():
    with patch.object(
        dns.resolver.Resolver,
        "resolve",
        _fake_resolve_factory(a_exc=dns.exception.Timeout(), aaaa_exc=dns.exception.Timeout()),
    ):
        result = check_dns("slow.example.")
    assert result.status == Status.FAIL
    assert "timed out" in result.message.lower()
