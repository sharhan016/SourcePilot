#!/usr/bin/env bash
set -euo pipefail

required_files=(
  compose.production.yaml
  infrastructure/docker/web.production.Dockerfile
  infrastructure/nginx/sourcepilot.conf
  .github/workflows/deploy-hostinger.yml
  docs/deployment/hostinger.md
)

for file in "${required_files[@]}"; do
  test -f "${file}" || { echo "missing deployment file: ${file}" >&2; exit 1; }
done

if docker compose version >/dev/null 2>&1; then
  compose=(docker compose)
elif docker-compose version >/dev/null 2>&1; then
  compose=(docker-compose)
else
  echo "Docker Compose is required to validate the Hostinger contract" >&2
  exit 1
fi

compose_output="$(mktemp -t sourcepilot-compose.XXXXXX.json)"
trap 'rm -f "${compose_output}"' EXIT

POSTGRES_PASSWORD=validation-password \
OPENAI_API_KEY=validation-openai-key \
EXA_API_KEY=validation-exa-key \
FIRECRAWL_API_KEY=validation-firecrawl-key \
  "${compose[@]}" -f compose.production.yaml config --format json > "${compose_output}"

python3 - "${compose_output}" <<'PY'
import json
from pathlib import Path
import sys

with open(sys.argv[1], encoding="utf-8") as source:
    compose = json.load(source)

services = compose["services"]
assert set(services) == {"api", "postgres", "web", "worker"}
assert all(not service.get("ports") for service in services.values())
assert services["web"]["build"]["args"]["VITE_API_URL"] == "/api/v1"
assert services["web"]["labels"]["traefik.http.routers.sourcepilot.rule"] == (
    "Host(`sourcepilot.sharhan.dev`)"
)
assert services["web"]["labels"][
    "traefik.http.services.sourcepilot.loadbalancer.server.port"
] == "80"
assert "traefik.docker.network" not in services["web"]["labels"]
assert set(compose["networks"]) == {"application"}
assert not any(network.get("external") for network in compose["networks"].values())

api_environment = services["api"]["environment"]
worker_environment = services["worker"]["environment"]
assert api_environment == worker_environment
assert api_environment["APP_ENV"] == "production"
assert api_environment["CORS_ORIGINS"] == '["https://sourcepilot.sharhan.dev"]'
assert api_environment["OPENAI_API_KEY"] == "validation-openai-key"
assert api_environment["EXA_API_KEY"] == "validation-exa-key"
assert api_environment["FIRECRAWL_API_KEY"] == "validation-firecrawl-key"
assert "validation-password" in api_environment["DATABASE_URL"]
assert services["postgres"]["environment"]["POSTGRES_PASSWORD"] == "validation-password"
assert any(
    volume["target"] == "/var/lib/postgresql/data"
    for volume in services["postgres"]["volumes"]
)
assert Path(services["api"]["build"]["context"]) == Path.cwd()
assert services["api"]["build"]["dockerfile"] == "infrastructure/docker/api.Dockerfile"
PY

VITE_API_URL=/api/v1 npm --prefix apps/web run build >/dev/null
if grep -R -n -E "http://localhost:8000|http://127\.0\.0\.1:8000" apps/web/dist; then
  echo "production frontend artifact contains a loopback API address" >&2
  exit 1
fi

grep -q 'uses: hostinger/deploy-on-vps@v2' .github/workflows/deploy-hostinger.yml
for secret in \
  HOSTINGER_API_KEY HOSTINGER_VM_ID POSTGRES_PASSWORD \
  OPENAI_API_KEY EXA_API_KEY FIRECRAWL_API_KEY; do
  grep -q "secrets\.${secret}" .github/workflows/deploy-hostinger.yml || {
    echo "deployment workflow does not pass ${secret}" >&2
    exit 1
  }
done

grep -q 'proxy_pass http://api:8000' infrastructure/nginx/sourcepilot.conf
echo "Hostinger deployment contract validated"
