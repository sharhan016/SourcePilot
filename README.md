# SourcePilot

SourcePilot is a production-oriented procurement workspace that turns a plain-language
requirement into a persistent, evidence-backed supplier recommendation. Specialized
agents coordinate external research, verification, deterministic evaluation, and a
concise shortlist while purchasing remains behind explicit human approval.

The default demo organization is **IT Essentials (ITE)** in Sharjah, United Arab
Emirates. Its primary scenario is: **“Source 50 business laptops for IT Essentials'
Sharjah office with UAE warranty and delivery.”** AED is the comparison currency,
the UAE is the primary procurement region, and the wider GCC is available for sourcing.
These values are configuration, not architectural constraints; the workflow and
capability boundaries remain geography- and category-neutral.

Development is managed with the **Vertex Harness**. The committed
`.vertex/project.json` is the durable milestone ledger, and each completed milestone
has executable verification evidence.

## What is implemented

- FastAPI API with Pydantic contracts and thin route handlers
- async SQLAlchemy persistence and an Alembic schema migration
- database-backed workflow/task states and restart recovery
- Research, Verification, Evaluation, and Recommendation agents
- bounded parallel verification, timeouts, bounded retry, fallback, and partial failure
- typed capability layer over real Exa and Firecrawl search adapters
- one LLM contract for OpenAI and OpenRouter
- structured supplier, product, evidence, event, and recommendation records
- deterministic quantities, totals, qualification, and ranking
- React/TypeScript dashboard, result, execution, and architecture routes
- explicit approve/reject checkpoint; SourcePilot never places an order
- Docker Compose services for PostgreSQL, API, worker, and frontend

SourcePilot does not ship mock supplier results in its runtime path. Without configured
provider credentials, a workflow fails explicitly rather than inventing evidence.

## Prerequisites

- Python 3.11+
- Node.js 22+
- PostgreSQL 16, or Docker with Compose
- at least one search credential: Exa or Firecrawl
- one LLM credential: OpenAI or OpenRouter

## Configuration

Copy the template and edit local values. Never commit the resulting `.env`.

```console
cp .env.example .env
```

Key switches are:

| Concern | Variable | Values |
| --- | --- | --- |
| LLM adapter | `LLM_PROVIDER` | `openai` or `openrouter` |
| LLM model | `LLM_MODEL` | a model available from the selected provider |
| Search adapter | `SEARCH_PROVIDER` | `exa` or `firecrawl` |
| Company | `COMPANY_NAME`, `COMPANY_LOCATION`, `COMPANY_COUNTRY` | organization context |
| Currency | `DEFAULT_CURRENCY` | ISO 4217 code such as `AED` |
| Geography | `PROCUREMENT_REGION`, `SOURCING_REGIONS` | primary and permitted sourcing regions |
| Tool concurrency | `MAX_CONCURRENT_TOOLS` | positive integer |
| Workflow concurrency | `MAX_CONCURRENT_WORKFLOWS` | positive integer |
| Retries | `PROVIDER_MAX_RETRIES` | bounded non-negative integer |

Set `OPENAI_API_KEY` or `OPENROUTER_API_KEY`, and `EXA_API_KEY` or
`FIRECRAWL_API_KEY`, for the selected providers. A configured secondary search key is
used as a fallback. Agents never reference provider names directly. Company, currency,
delivery location, and sourcing geography are passed into each new procurement request
from configuration so another organization can replace the UAE demo without code changes.

## Run with Docker

```console
cp .env.example .env
docker compose up --build
```

The API applies the Alembic migration before starting. Open:

- workspace: `http://localhost:5173`
- API documentation: `http://localhost:8000/docs`
- health check: `http://localhost:8000/health`

Stop with `docker compose down`. Add `-v` only when you intentionally want to erase the
local PostgreSQL volume.

## Local development

```console
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
npm install --prefix apps/web
```

Start PostgreSQL, set `DATABASE_URL`, then migrate and run each process:

```console
alembic -c apps/api/alembic.ini upgrade head
uvicorn sourcepilot.main:app --app-dir apps/api --reload
python -m sourcepilot.worker
npm --prefix apps/web run dev
```

The API responds to request creation with `202 Accepted`; the worker independently
claims queued workflows. A second request can be submitted while the first runs.

## Verification

```console
make verify
```

This runs Python linting, backend/domain/orchestration/provider tests, frontend
component tests, a strict TypeScript check, a production build, and Python bytecode
compilation. The optional browser smoke test requires Playwright and exercises desktop
and mobile layouts with API interception:

```console
python /path/to/with_server.py \
  --server "npm --prefix apps/web run dev -- --host 127.0.0.1" --port 5173 \
  -- python tests/browser_smoke.py
```

## Vertex Harness workflow

Use the installed Vertex CLI from the repository root:

```console
vertex doctor .
vertex status .
vertex evidence . --task SP-5
vertex checkpoint list .
vertex index .
```

If verification is interrupted, run `vertex recover .`, inspect side effects, resume
the blocked task, and rerun verification. Do not edit `.vertex/project.json` manually.

## Database and recovery

Alembic owns schema creation. To upgrade an existing database:

```console
alembic -c apps/api/alembic.ini upgrade head
```

On worker startup, workflows left `running` by an interruption become `waiting` with a
recovery note. Completed tasks remain complete; the orchestrator resumes only eligible
work. Failed providers and unavailable claims are retained as explicit state.

## API surface

- `POST /api/v1/requests`
- `GET /api/v1/context`
- `GET /api/v1/requests`
- `GET /api/v1/requests/{id}`
- `GET /api/v1/requests/{id}/suppliers`
- `GET /api/v1/requests/{id}/recommendation`
- `POST /api/v1/requests/{id}/recommendation/review`
- `GET /api/v1/workflows/{id}`

## Architecture

The live `/architecture` route contains six Mermaid diagrams and implementation notes.
The engineering narrative, boundaries, and recovery model are also documented in
[`docs/architecture.md`](docs/architecture.md).
