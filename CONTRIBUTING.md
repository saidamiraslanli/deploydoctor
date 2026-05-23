# Contributing to DeployDoctor

Thanks for considering a contribution. This project stays intentionally small — a focused, no-magic CLI. Improvements that fit that bar are very welcome.

## Setup

```bash
git clone https://github.com/saidamiraslanli/deploydoctor.git
cd deploydoctor
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Python 3.11+ is required.

## Run the test suite

```bash
pytest
```

## Lint

```bash
ruff check .
ruff check . --fix    # auto-fix what is fixable
```

CI runs both on every push / pull request — please make sure they pass locally first.

## Adding a new check

A check is a function that returns a `CheckResult`. To add one:

1. Create a module under [`deploydoctor/checks/`](deploydoctor/checks/), e.g. `deploydoctor/checks/redis.py`.
2. Export a function returning a `CheckResult` from [`deploydoctor/models.py`](deploydoctor/models.py):

   ```python
   from deploydoctor.models import CheckResult, Status

   def check_redis(host: str, port: int = 6379, timeout: float = 3.0) -> CheckResult:
       try:
           ...
       except Exception as e:
           return CheckResult(name="Redis", status=Status.FAIL, message=str(e))
       return CheckResult(name="Redis", status=Status.PASS, message="Reachable")
   ```

3. Wire it into [`deploydoctor/cli.py`](deploydoctor/cli.py) (or `checks/local.py` for host-side checks).
4. Add a test under [`tests/`](tests/) that mocks external I/O — checks must never require live infrastructure to pass CI.

### Rules every check must follow

- **Defensive** — wrap external I/O; convert any exception into a `CheckResult`. Never let one check crash the report.
- **Timeouts everywhere** — no unbounded blocking calls.
- **Safe subprocess** — `shell=False`, args as a list. Use [`deploydoctor/utils/subprocess.py`](deploydoctor/utils/subprocess.py).
- **Cross-platform** — host-only checks must `SKIP` cleanly on Windows / macOS.
- **Actionable** — on `FAIL` / `WARN`, include `suggestions` the user can copy-paste.

## Pull request expectations

- One topic per PR. Smaller is better.
- `pytest` and `ruff check .` pass locally.
- New behavior has a test.
- Update [`CHANGELOG.md`](CHANGELOG.md) under an `## Unreleased` heading.
- No new runtime dependencies without a clear reason — stdlib first.
- Describe the *why* in the PR body, not just the *what*.

## Reporting issues

Use the bug-report template. Include:

- DeployDoctor version (`deploydoctor version`)
- Python version (`python --version`)
- OS
- The exact command run and the full output

## License

By contributing, you agree your contribution is licensed under the [MIT License](LICENSE).
