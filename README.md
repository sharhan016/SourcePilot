# SourcePilot

SourcePilot is a production-oriented procurement workspace that turns a plain-language
request into a persistent, evidence-backed supplier recommendation. Specialized agents
coordinate external research, verification, deterministic evaluation, and a concise
recommendation while irreversible purchasing remains behind human approval.

The first supported vertical slice is: **“Find 50 MacBook Pro 14-inch laptops for the
company.”** SourcePilot is category-neutral below that workflow, so the orchestration
model can be reused for later procurement categories.

> Development is managed with the Vertex Harness. `.vertex/project.json` is the durable
> work ledger; verification evidence is recorded through `vertex verify`.

## Repository layout

```text
apps/api/       FastAPI, domain, persistence, agents, providers, orchestration
apps/web/       React + TypeScript procurement workspace
infrastructure/ Docker images and local runtime
docs/           Architecture and operating guidance
tests/          Backend, orchestration, provider, and contract verification
```

The full setup and operating guide is completed with the integrated milestone.

