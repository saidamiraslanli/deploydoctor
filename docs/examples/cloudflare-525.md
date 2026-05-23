# Cloudflare 525 SSL Handshake Failure

## Symptom

Your site is proxied through Cloudflare. Visitors see a Cloudflare error page. DeployDoctor reports:

```
╭─ HTTP ─────────────────────────────────────────────────────╮
│ FAIL  Cloudflare 525 SSL handshake failed: Cloudflare      │
│       could reach the origin, but TLS negotiation between  │
│       Cloudflare and the origin server failed.             │
│       • Server: cloudflare                                 │
│       → sudo nginx -T | grep -E 'listen 443|ssl_certificate'│
│       → sudo nginx -t                                      │
│       → openssl s_client -connect yourdomain.com:443 ...  │
│       → Cloudflare dashboard → SSL/TLS: check mode         │
│       → sudo tail -n 50 /var/log/nginx/error.log           │
╰────────────────────────────────────────────────────────────╯
╭─ SSL ──────────────────────────────────────────────────────╮
│ PASS  Valid certificate (86 days remaining)                 │
╰────────────────────────────────────────────────────────────╯
```

Note: SSL check passes because DeployDoctor connects directly to port 443, bypassing Cloudflare. The 525 is a Cloudflare-to-origin TLS failure, not a browser-to-Cloudflare failure.

## Likely cause

Cloudflare's SSL/TLS mode is set to **Full** or **Full (strict)**, which means Cloudflare tries to open a TLS connection to your origin server. One of these is broken:

- Nginx is not listening on port 443 with SSL enabled.
- The SSL certificate or key path in nginx config is wrong or the file is missing.
- The origin certificate is self-signed and mode is **Full (strict)**.
- Nginx was reloaded with a broken SSL config and silently fell back.

## Fix commands

Run on the origin server (not through Cloudflare):

```bash
# 1. Confirm nginx is listening on 443 with SSL
sudo nginx -T | grep -E "listen 443|ssl_certificate"

# 2. Test nginx config syntax
sudo nginx -t

# 3. Test the TLS handshake directly from your origin server
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# 4. Check nginx error log for SSL errors
sudo tail -n 50 /var/log/nginx/error.log
```

In the Cloudflare dashboard → **SSL/TLS → Overview**:

| Mode | Requirement |
|------|-------------|
| **Off** | No TLS to origin — Cloudflare sends plain HTTP |
| **Flexible** | No TLS to origin — Cloudflare sends plain HTTP |
| **Full** | TLS to origin required; self-signed cert OK |
| **Full (strict)** | TLS to origin required; cert must be publicly trusted or a Cloudflare Origin Certificate |

If your origin cert is self-signed, switch to **Full** (not strict). If you want **Full (strict)**, install a valid cert (Let's Encrypt, Cloudflare Origin Certificate, etc.).

## Common nginx SSL block

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ...
}
```

After fixing, reload nginx:

```bash
sudo nginx -t && sudo systemctl reload nginx
```
