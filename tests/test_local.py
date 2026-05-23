import platform

import pytest

from deploydoctor.checks import local as local_mod
from deploydoctor.models import Status


def test_non_linux_skips(monkeypatch):
    monkeypatch.setattr(local_mod.platform, "system", lambda: "Windows")
    assert local_mod.check_nginx_installed().status == Status.SKIP
    assert local_mod.check_docker_installed().status == Status.SKIP
    assert local_mod.check_listening_ports().status == Status.SKIP
    assert local_mod.check_nginx_config().status == Status.SKIP
    assert local_mod.check_nginx_error_log().status == Status.SKIP
    assert local_mod.check_docker_containers().status == Status.SKIP


def test_run_local_checks_returns_six_results():
    results = local_mod.run_local_checks()
    assert len(results) == 6
    for r in results:
        assert r.name
        assert r.status is not None


@pytest.mark.skipif(platform.system() != "Linux", reason="Linux-only path")
def test_linux_missing_command_skips(monkeypatch):
    monkeypatch.setattr(local_mod, "has_command", lambda name: False)
    assert local_mod.check_nginx_installed().status == Status.SKIP
    assert local_mod.check_docker_installed().status == Status.SKIP
    assert local_mod.check_listening_ports().status == Status.SKIP
    assert local_mod.check_nginx_config().status == Status.SKIP
    assert local_mod.check_docker_containers().status == Status.SKIP
