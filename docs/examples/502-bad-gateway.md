# 502 Bad Gateway

## Symptom

Browser shows **"502 Bad Gateway"**. DNS resolves, the cert is valid, and the homepage returns immediately — but with `502`.

## What DeployDoctor shows

```
deploydoctor check example.com
```

```
╭─ HTTPS ───────────────────────────────────────────────────╮
│ FAIL  502 gateway error                                   │
│       • Final URL: https://example.com/                   │
│       • Time: 41 ms                                       │
│       • Server: nginx                                     │
│       → Possible cause: reverse proxy cannot reach        │
│         upstream app                                      │
│       → sudo systemctl status nginx                       │
│       → sudo tail -n 50 /var/log/nginx/error.log          │
│       → ss -tulpn                                         │
╰───────────────────────────────────────────────────────────╯

╭─ Listening ports ─────────────────────────────────────────╮
│ PASS  Found 6 line(s) of listening sockets                │
│       • LISTEN 0 511 *:80 ...                             │
│       • LISTEN 0 511 *:443 ...                            │
│       (no socket on the app port — 3000 / 8000 / 8080)    │
╰───────────────────────────────────────────────────────────╯
```

## Likely cause

`nginx` is up and accepting connections, but the upstream it proxies to is not. Either the app process crashed, never started, is listening on the wrong interface, or the firewall between proxy and app is blocking it.

The fast response time (single-digit to low-tens of ms) is the giveaway — nginx gave up on the upstream immediately rather than waiting.

## Suggested fix

```bash
# 1. Confirm nginx itself is healthy
sudo systemctl status nginx
sudo nginx -t

# 2. Find what nginx actually said
sudo tail -n 100 /var/log/nginx/error.log
# Look for: "connect() failed (111: Connection refused)"
#        or: "no live upstreams while connecting to upstream"

# 3. Check the upstream is actually running and bound
ss -tulpn | grep -E ':(3000|8000|8080)\b'
sudo systemctl status my-app.service     # or your container/process manager

# 4. If using Docker
docker ps
docker logs --tail=200 my-app

# 5. Restart the upstream once you've found why it died
sudo systemctl restart my-app.service
```

If the upstream listens on `127.0.0.1:3000` but nginx is configured for `localhost:3000`, an IPv6/IPv4 mismatch can produce the same error — pin one explicitly.
