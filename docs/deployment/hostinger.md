# Hostinger deployment

SourcePilot deploys to `https://sourcepilot.sharhan.dev` through Hostinger's official
`hostinger/deploy-on-vps@v2` GitHub Action. The repository is public, so this deployment
does not require an SSH key or a repository deploy key.

## Deployment architecture

`compose.production.yaml` deploys four services:

- `postgres`: persistent PostgreSQL 16 storage;
- `api`: runs migrations and serves FastAPI internally on port 8000;
- `worker`: executes persisted procurement workflows independently of the API;
- `web`: builds the React application and serves it through Nginx on internal port 80.

Only the Nginx container is routed publicly. Nginx serves the single-page application and
proxies `/api/` and `/health` to the API over the private Compose network. Database, API,
and worker ports are not published.

Traefik discovers the web container through Docker labels and routes the
`sourcepilot.sharhan.dev` hostname over its existing `websecure` entrypoint using the
existing `letsencrypt` certificate resolver. This matches the working LedgerLens VPS
routing contract; SourcePilot does not create or replace the VPS Traefik project.

## GitHub configuration

The following repository secrets are required and are already named in the deployment
workflow:

| Secret | Purpose |
| --- | --- |
| `HOSTINGER_API_KEY` | Authenticates Hostinger's official deployment action |
| `HOSTINGER_VM_ID` | Selects the Hostinger virtual machine |
| `POSTGRES_PASSWORD` | Protects the persistent SourcePilot database |
| `OPENAI_API_KEY` | Runs the configured OpenAI model |
| `EXA_API_KEY` | Primary supplier research provider |
| `FIRECRAWL_API_KEY` | Search fallback provider |

Use a strong URL-safe `POSTGRES_PASSWORD` containing letters, numbers, `_`, and `-`.
SourcePilot includes it in an async PostgreSQL URL, so reserved URL characters would need
percent encoding.

The deploy job targets a GitHub environment named `production`. Creating that environment
is optional unless approval rules or environment-specific restrictions are desired;
repository secrets remain available to it.

## Cloudflare configuration

Create this DNS record in the `sharhan.dev` zone:

| Field | Value |
| --- | --- |
| Type | `A` |
| Name | `sourcepilot` |
| IPv4 address | The same Hostinger VPS public IPv4 used by LedgerLens |
| TTL | `Auto` |
| Proxy status for first deployment | `DNS only` |

Keep the record DNS-only for the first deployment so Traefik can complete the initial
Let's Encrypt certificate challenge without introducing another proxy layer. After
`https://sourcepilot.sharhan.dev/health` responds successfully and the certificate is
valid, Cloudflare proxying may be enabled.

When proxying is enabled, set Cloudflare SSL/TLS encryption mode to **Full (strict)**.
Do not use Flexible mode. No Cloudflare port forwarding rule is required because Traefik
already terminates HTTPS on the VPS.

## First deployment

1. Confirm the existing LedgerLens Traefik project is healthy in Hostinger Docker Manager.
2. Add the Cloudflare `A` record above and leave it DNS-only.
3. Confirm all six GitHub repository secrets exist.
4. Push the prepared commit to `main`, or run **Verify and deploy to Hostinger** manually.
5. Wait for `postgres`, `api`, `worker`, and `web` to start; PostgreSQL and API health checks
   must pass before dependent services start.
6. Open `https://sourcepilot.sharhan.dev/health` and confirm a JSON response with
   `"status": "ok"`.
7. Open `https://sourcepilot.sharhan.dev`, create a small procurement request, and confirm
   that the worker advances it through the persisted workflow.
8. Optionally enable Cloudflare proxying, then recheck both the health endpoint and UI.

The API applies Alembic migrations automatically on every API container start. The named
`sourcepilot_postgres` volume persists requests, events, suppliers, and recommendations
across application updates.

## Updating and rollback

Every push to `main` runs the complete verification suite and production deployment check
before Hostinger receives the Compose project. A failed verification does not deploy.

To roll back application code, revert the faulty commit on `main` and push the revert.
The workflow redeploys that repository state. Review database migrations before rollback:
startup migrates forward and does not automatically downgrade. Never delete the
`sourcepilot_postgres` volume during a normal update or rollback.

Inspect container health and logs through Hostinger Docker Manager. If Traefik obtains a
certificate but returns a gateway error, confirm the existing host-networked Traefik
process can reach the SourcePilot web container's Docker bridge address on port 80, using
the same VPS networking arrangement as LedgerLens.
