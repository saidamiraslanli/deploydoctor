# DeployDoctor

[![CI](https://github.com/saidamiraslanli/deploydoctor/actions/workflows/ci.yml/badge.svg)](https://github.com/saidamiraslanli/deploydoctor/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code style: Ruff](https://img.shields.io/badge/lint-ruff-000)](https://github.com/astral-sh/ruff)
[![Tests: pytest](https://img.shields.io/badge/tests-pytest-success)](https://docs.pytest.org/)

**When your site is down at 2 a.m., DeployDoctor is the one command that tells you what is actually broken.**

`deploydoctor` is a small, no-magic CLI that runs the checks you would otherwise run by hand when a deployment goes sideways — DNS, HTTP/HTTPS, TLS certificates, port reachability, and the usual suspects on the host itself (`nginx -t`, `ss -tulpn`, `docker ps`, nginx error logs).

Output is a single readable Rich report with `PASS` / `WARN` / `FAIL` / `SKIP` markers, a summary, the **most likely issue**, and a set of copy-pasteable next commands.

## Demo

![DeployDoctor demo](docs/assets/demo.gif)

## Install

From GitHub (recommended until PyPI release):

```bash
pipx install git+https://github.com/saidamiraslanli/deploydoctor.git
```

Or with pip:

```bash
pip install git+https://github.com/saidamiraslanli/deploydoctor.git
```

Development (editable install with linter + tests):

```bash
git clone https://github.com/saidamiraslanli/deploydoctor.git
cd deploydoctor
pip install -e ".[dev]"
```

Python 3.11+.

## Quick usage

```bash
deploydoctor check example.com       # full diagnosis: remote + local
deploydoctor remote example.com      # external-only: DNS, HTTP, HTTPS, SSL, ports
deploydoctor local                   # this host: nginx, docker, ss -tulpn
deploydoctor version
deploydoctor --help

# Also runnable as a module
python -m deploydoctor check example.com
```

A bare hostname (`example.com`) or a full URL (`https://example.com/foo`) both work — the host is extracted automatically.

## Example output

```
─────────── DeployDoctor Report for example.com ───────────

╭─ DNS ─────────────────────────────────────────────────────╮
│ PASS  Resolved 1 A / 1 AAAA record(s)                     │
│       • A: 93.184.216.34                                  │
│       • AAAA: 2606:2800:220:1:248:1893:25c8:1946          │
╰───────────────────────────────────────────────────────────╯
╭─ HTTPS ───────────────────────────────────────────────────╮
│ FAIL  502 gateway error                                   │
│       → Possible cause: reverse proxy cannot reach        │
│         upstream app                                      │
│       → sudo systemctl status nginx                       │
│       → sudo tail -n 50 /var/log/nginx/error.log          │
│       → ss -tulpn                                         │
╰───────────────────────────────────────────────────────────╯
╭─ SSL ─────────────────────────────────────────────────────╮
│ WARN  Certificate expires in 12 day(s)                    │
│       • Subject CN: example.com                           │
│       • Issuer: Let's Encrypt R3                          │
│       → Schedule renewal (sudo certbot renew --dry-run)   │
╰───────────────────────────────────────────────────────────╯

                     Summary
┌────────┬──────────┬────────┬─────────┐
│ Passed │ Warnings │ Failed │ Skipped │
├────────┼──────────┼────────┼─────────┤
│   3    │    1     │   1    │    0    │
└────────┴──────────┴────────┴─────────┘
```

More worked examples in [`docs/examples/`](docs/examples/):

- [`502-bad-gateway.md`](docs/examples/502-bad-gateway.md) — reverse proxy can't reach upstream app
- [`ssl-expired.md`](docs/examples/ssl-expired.md) — certificate expired or about to expire
- [`nginx-upstream-down.md`](docs/examples/nginx-upstream-down.md) — nginx is up, the app behind it isn't
- [`cloudflare-525.md`](docs/examples/cloudflare-525.md) — Cloudflare can't complete TLS handshake with origin

## What problems it detects

| Layer | Detected |
|-------|----------|
| **DNS** | NXDOMAIN, missing A/AAAA, resolver timeouts |
| **HTTP / HTTPS** | connection refused, connect/read timeouts, too many redirects, SSL verification failures, 4xx, 5xx, 502 / 503 / 504 gateway errors, Cloudflare 525 SSL handshake failures, redirect chains |
| **SSL / TLS** | expired certs, certs expiring within 30 days, verify failures, missing chain, hosts without TLS |
| **Ports** | 80 / 443 closed, filtered, refused, or timing out from outside |
| **Local host (Linux)** | nginx config syntax (`nginx -t`), listening sockets (`ss -tulpn`), nginx error log tail, running Docker containers, missing tools |

## Local vs remote mode

DeployDoctor exposes two scopes deliberately:

- **`remote <domain>`** — *outside view*. Everything runs over the network: DNS, HTTP, HTTPS, SSL, port probes. Safe to run from a laptop or from a monitoring host. Does not touch the deployment host.
- **`local`** — *inside view*. Inspects the host you run it on: is nginx installed, is its config valid, what is listening, what does the error log say, what Docker containers are running. Linux-only by design; cleanly `SKIP`s on Windows / macOS or when commands and permissions are missing.
- **`check <domain>`** — runs both back-to-back, which is what you want when SSHed into the box that serves the domain.

This split exists so you can use the tool from anywhere without the local checks polluting the report with noise.

## CI exit codes

| Code | Meaning             |
|------|---------------------|
| `0`  | All checks passed   |
| `1`  | At least one WARN   |
| `2`  | At least one FAIL   |

Friendly for cron, CI, uptime scripts:

```bash
deploydoctor remote example.com || curl -X POST https://my-alert-hook
```

```yaml
# GitHub Actions example
- name: Post-deploy smoke check
  run: deploydoctor remote example.com
```

## Roadmap

- HTTP/2 + HTTP/3 capability probe
- TLS handshake details (protocol, cipher, OCSP stapling)
- Configurable check timeouts via CLI flag
- JSON output mode (`--json`) for piping into other tools
- systemd unit health checks (`is-active`, `is-failed`)
- Apache / Caddy parity for local config tests
- `deploydoctor watch` for continuous monitoring

## Troubleshooting

- **`nginx -t` reports permission denied** — run with `sudo`; DeployDoctor will surface `SKIP` rather than fail.
- **All local checks `SKIP`** — local checks are gated to Linux. Run on the deployment host.
- **SSL check is `SKIP`** — port 443 refused; the domain likely doesn't serve TLS.
- **DNS `timeout`** — typically a firewall blocking UDP/53 on the host running the CLI.

## Contributing

Pull requests welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for setup, lint / test commands, and the rules every new check must follow.

Quick start:

```bash
git clone https://github.com/saidamiraslanli/deploydoctor.git
cd deploydoctor
pip install -e ".[dev]"
pytest
ruff check .
```

## License

[MIT](LICENSE).
