# Nginx Up, App Down

## Symptom

`curl https://example.com/` returns `502` or `504` from nginx, but the host itself looks healthy from the outside — DNS resolves, port 443 is open, the cert is valid. The application behind nginx is the part that has fallen over.

## What DeployDoctor shows

```
deploydoctor check example.com
```

```
╭─ HTTPS ───────────────────────────────────────────────────╮
│ FAIL  502 gateway error                                   │
│       → Possible cause: reverse proxy cannot reach        │
│         upstream app                                      │
╰───────────────────────────────────────────────────────────╯
╭─ Ports ───────────────────────────────────────────────────╮
│ PASS  All probed ports open                               │
│       • Port 80: open                                     │
│       • Port 443: open                                    │
╰───────────────────────────────────────────────────────────╯
╭─ Nginx config test ───────────────────────────────────────╮
│ PASS  nginx config syntax is OK                           │
╰───────────────────────────────────────────────────────────╯
╭─ Listening ports ─────────────────────────────────────────╮
│ PASS  Found 5 line(s) of listening sockets                │
│       • LISTEN 0 511 *:80                                 │
│       • LISTEN 0 511 *:443                                │
│       (no socket bound on the upstream app port)          │
╰───────────────────────────────────────────────────────────╯
╭─ Docker containers ───────────────────────────────────────╮
│ PASS  0 running container(s)                              │
╰───────────────────────────────────────────────────────────╯
╭─ Nginx error log ─────────────────────────────────────────╮
│ WARN  showing last 30 line(s) (errors present)            │
│       • connect() failed (111: Connection refused) while  │
│         connecting to upstream, upstream: ...             │
╰───────────────────────────────────────────────────────────╯
```

The pattern: edge layer (DNS, ports, TLS, nginx config) is all `PASS`. The upstream socket is missing. The error log explicitly says so. No docker container is running.

## Likely cause

The application service has crashed, exited cleanly, or was never restarted after a deploy. `nginx -t` passes because *its* config is fine; nginx has nothing to talk to.

Common variants:

- `systemd` unit went into `failed` state after the last restart.
- The Docker container exited (`docker ps -a` shows it, `docker ps` doesn't).
- Out-of-memory kill — check `dmesg` for `oom-killer`.
- A migration on boot failed; the container is in a restart loop.
- The app is bound to `127.0.0.1` but nginx is trying to reach it via the host's external IP (or vice versa).

## Suggested fix

```bash
# What is the app supposed to be? (systemd unit, container, supervisor, ...)
sudo systemctl status my-app.service
journalctl -u my-app.service --since "1 hour ago" --no-pager

# Container variant
docker ps -a                              # see exited containers
docker logs --tail=200 my-app
docker inspect my-app | grep -E 'Status|Error|RestartCount'

# OOM check
sudo dmesg -T | grep -i -E 'killed process|out of memory' | tail

# Bring it back
sudo systemctl restart my-app.service
# or
docker start my-app
# or
docker compose up -d

# Confirm something is actually listening on the upstream port
ss -tulpn | grep -E ':(3000|8000|8080)\b'

# Re-run DeployDoctor — every check should be green now
deploydoctor check example.com
```

If the service restarts cleanly and crashes again within seconds, treat the journal / docker logs as the source of truth and fix the underlying error before re-running.
