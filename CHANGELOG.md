# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.1.0

- Initial public release
- DNS checks (A / AAAA, NXDOMAIN, timeout)
- HTTP/HTTPS checks (status, redirect chain, timing, refused/timeout/SSL-verify/4xx/5xx/502-503-504 classification)
- Cloudflare 525 SSL handshake failure detection with origin TLS troubleshooting suggestions
- SSL certificate checks (issuer, subject CN, expiry, days remaining; warn under 30 days, fail when expired)
- Port reachability checks (TCP probe of 80 / 443)
- Local Linux diagnostics (`nginx -t`, `ss -tulpn`, `docker ps`, `/var/log/nginx/error.log` tail) with clean skips on non-Linux or missing tools
- Rich terminal report with `PASS` / `WARN` / `FAIL` / `SKIP` markers, summary, most-likely issue, and suggested next commands
- Stable exit codes (`0` pass, `1` warn, `2` fail) for CI / cron / monitoring use
- Typer CLI: `check`, `remote`, `local`, `version`
