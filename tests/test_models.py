from deploydoctor.models import CheckResult, Report, Status


def test_check_result_defaults():
    r = CheckResult(name="X", status=Status.PASS)
    assert r.passed
    assert not r.failed
    assert not r.warned
    assert not r.skipped
    assert r.details == []
    assert r.suggestions == []


def test_check_result_flags():
    assert CheckResult("a", Status.WARN).warned
    assert CheckResult("a", Status.FAIL).failed
    assert CheckResult("a", Status.SKIP).skipped


def test_report_counts_and_summary():
    rep = Report(domain="example.com")
    rep.add(CheckResult("DNS", Status.PASS, "ok"))
    rep.add(CheckResult("HTTPS", Status.FAIL, "boom", suggestions=["curl -v example.com"]))
    rep.add(CheckResult("Ports", Status.WARN, "partial", suggestions=["check fw"]))
    rep.add(CheckResult("Local", Status.SKIP, "skipped"))
    assert rep.passed_count == 1
    assert rep.failed_count == 1
    assert rep.warn_count == 1
    assert rep.skipped_count == 1
    assert rep.most_likely_issue is not None
    assert rep.most_likely_issue.startswith("HTTPS")
    # Both warn and fail suggestions should appear, deduped, preserving order.
    assert rep.next_commands == ["curl -v example.com", "check fw"]


def test_report_most_likely_falls_back_to_warn():
    rep = Report(domain="x")
    rep.add(CheckResult("DNS", Status.PASS))
    rep.add(CheckResult("HTTP", Status.WARN, "redirect"))
    assert rep.most_likely_issue.startswith("HTTP")


def test_report_no_issue_when_all_pass():
    rep = Report(domain="x")
    rep.add(CheckResult("DNS", Status.PASS))
    assert rep.most_likely_issue is None
    assert rep.next_commands == []


def test_next_commands_dedup():
    rep = Report(domain="x")
    rep.add(CheckResult("A", Status.FAIL, suggestions=["cmd1", "cmd2"]))
    rep.add(CheckResult("B", Status.WARN, suggestions=["cmd2", "cmd3"]))
    assert rep.next_commands == ["cmd1", "cmd2", "cmd3"]
