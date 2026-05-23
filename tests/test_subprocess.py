from deploydoctor.utils.subprocess import has_command, run


def test_has_command_true_for_python():
    # Both Windows ("python") and POSIX have a python binary; fall back if missing.
    assert has_command("python") or has_command("python3")


def test_has_command_false_for_nonsense():
    assert not has_command("definitely-not-a-real-binary-xyz-123")


def test_run_unknown_command_returns_error():
    res = run(["definitely-not-a-real-binary-xyz-123"])
    assert not res.found
    assert res.error
    assert not res.ok


def test_run_empty_args():
    res = run([])
    assert not res.found
    assert res.error == "empty args"
