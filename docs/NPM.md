# Nginx Proxy Manager — reference routing

This document is part of the required installation procedure in the root `README.md`.
It recreates the reverse-proxy topology of the reference deployment without copying the NPM database or certificates.

## Before creating proxy hosts

1. Point your public wildcard DNS record (`*.example.com`) to the Docker host public IP. The included Cloudflare DDNS container keeps it updated when configured.
2. Forward TCP ports **80** and **443** from the router to the Docker host.
3. In Nginx Proxy Manager, obtain a Let's Encrypt certificate covering your hostnames (a wildcard certificate is convenient).
4. For every host below enable **Block Common Exploits**, **Force SSL** and **HSTS**. Enable WebSocket support only where the table says `yes`.
5. Replace `example.com` with your own domain everywhere.

## Proxy hosts

| Public hostname | Scheme | Forward host | Port | WebSocket |
|---|---|---|---:|---|
| `aiostreams.example.com` | `http` | `aiostreams` | 4444 | no |
| `aiometadata.example.com` | `http` | `aiometadata` | 1337 | yes |
| `mfp.example.com` | `http` | `mediaflow-proxy-light` | 8888 | no |
| `headscale.example.com` | `http` | `headscale` | 8080 | yes |
| `portainer.example.com` | `http` | `portainer` | 9000 | no |
| `stremthru.example.com` | `http` | `gluetun` | 9090 | no |
| `seanime.example.com` | `http` | `gluetun` | 43211 | yes |
| `shared-seanime.example.com` | `http` | `gluetun` | 43311 | yes |
| `cometnet.example.com` | `http` | `gluetun` | 8765 | yes |
| `streamv.example.com` | `http` | `gluetun` | 7860 | no |

`Comet` itself remains available on the LAN at `http://SERVER_LAN_IP:2020` in the reference stack. AIOStreams reaches it internally through `http://gluetun:2020`; a public Comet proxy host is not required.

## Headscale + Headplane + OAuth2 Proxy

The public hostname `headscale.example.com` serves two different applications:

- `/` is Headscale itself (`headscale:8080`);
- `/admin` and `/oauth2/` are routed through `oauth2-proxy:4180`, which authenticates the user and then forwards to Headplane.

Create the normal `headscale.example.com -> headscale:8080` Proxy Host first, enable WebSockets, SSL, Force SSL and HSTS, then paste the following in its **Advanced** field after replacing the hostname:

```nginx
location = /admin/logout.data {
    add_header X-Remix-Redirect "https://headscale.example.com/oauth2/sign_in?rd=%2Fadmin" always;
    add_header X-Remix-Reload-Document "true" always;
    return 204;
}

location = /oauth2/callback {
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Scheme $scheme;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Real-IP $remote_addr;

    proxy_intercept_errors on;
    error_page 403 =302 /oauth2/sign_in?rd=%2Fadmin;

    proxy_pass http://oauth2-proxy:4180;
}

location /oauth2/ {
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Scheme $scheme;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $http_connection;
    proxy_http_version 1.1;
    proxy_pass http://oauth2-proxy:4180;
}

location /admin {
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Scheme $scheme;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $http_connection;
    proxy_http_version 1.1;
    proxy_pass http://oauth2-proxy:4180;
}
```

The Headplane configuration intentionally keeps its own OIDC block disabled; authentication is performed by OAuth2 Proxy in front of Headplane, matching the reference architecture.

## Verification

After creating the hosts:

```bash
curl -I https://aiostreams.example.com
curl -I https://mfp.example.com
curl -I https://headscale.example.com
curl -I https://headscale.example.com/admin
```

Expected behavior:

- the first three hosts answer through NPM over HTTPS;
- `/admin` redirects to Google/OAuth2 Proxy when no valid session is present;
- Seanime and CometNet WebSocket connections remain stable through NPM.
