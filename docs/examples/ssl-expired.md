# SSL Certificate Expired / Expiring

## Symptom

Browser shows **"Your connection is not private"** / `NET::ERR_CERT_DATE_INVALID`. Curl reports `SSL certificate problem: certificate has expired`. Monitoring is suddenly silent because the agent refuses to talk to an expired cert.

## What DeployDoctor shows

Expired:

```
╭─ SSL ─────────────────────────────────────────────────────╮
│ FAIL  Certificate expired 4 day(s) ago                    │
│       • Subject CN: example.com                           │
│       • Issuer: Let's Encrypt R3                          │
│       • Expires: 2026-05-19T08:14:02+00:00 (-4 days)      │
│       → Renew certificate (e.g. `sudo certbot renew`)     │
╰───────────────────────────────────────────────────────────╯
```

About to expire:

```
╭─ SSL ─────────────────────────────────────────────────────╮
│ WARN  Certificate expires in 12 day(s)                    │
│       • Subject CN: example.com                           │
│       • Issuer: Let's Encrypt R3                          │
│       → Schedule renewal (sudo certbot renew --dry-run)   │
╰───────────────────────────────────────────────────────────╯
```

`HTTPS` will usually also be `FAIL` with `SSL verification failure` when the cert is expired.

## Likely cause

- Automatic renewal stopped working — `certbot` timer disabled, cron removed, the renewal hook failed silently.
- The renewed cert exists on disk but nginx was never reloaded to pick it up.
- A wildcard cert was renewed only on one host of a multi-host fleet.
- A paid CA cert reached end of validity and nobody owns the calendar entry.

## Suggested fix

```bash
# Inspect the live cert that's actually being served (not the file on disk)
openssl s_client -connect example.com:443 -servername example.com </dev/null 2>/dev/null \
  | openssl x509 -noout -dates -subject -issuer

# Let's Encrypt: force a renewal now and reload nginx
sudo certbot renew --force-renewal
sudo systemctl reload nginx

# Confirm the timer that should have done this automatically is enabled
systemctl list-timers | grep -i certbot
sudo systemctl status certbot.timer

# Dry-run to prove future renewals will succeed
sudo certbot renew --dry-run
```

If the served cert and the cert on disk disagree after renewal, nginx was never reloaded — the daemon caches the cert at startup.
