import { useEffect, useId, useRef } from "react";
import mermaid from "mermaid";

const diagrams = [
  { title: "High-level architecture", code: `flowchart LR
UI[React workspace] --> API[FastAPI]
API --> DB[(PostgreSQL)]
Worker[Async worker] --> DB
Worker --> Agents[Specialized agents]
Agents --> Caps[Capabilities]
Caps --> Providers[External providers]` },
  { title: "Procurement workflow", code: `stateDiagram-v2
[*] --> Queued
Queued --> Research
Research --> Verification
Verification --> Evaluation
Evaluation --> Recommendation
Recommendation --> HumanReview
HumanReview --> Approved
HumanReview --> Rejected` },
  { title: "Agent orchestration", code: `flowchart TD
O[Orchestrator] --> R[Research agent]
O --> V[Verification agent]
O --> E[Evaluation agent]
O --> C[Recommendation agent]
R -->|structured candidates| V
V -->|verified claims| E
E -->|deterministic ranking| C` },
  { title: "Tool and provider boundary", code: `flowchart LR
A[Agent] --> I[Typed capability]
I --> X{Configured adapter}
X --> Exa
X --> Firecrawl
I --> P[Policy: timeout / retry / cache]
P --> Ev[Execution event]` },
  { title: "Controlled parallelism", code: `flowchart TD
Q[Supplier candidates] --> S[Concurrency semaphore]
S --> A[Verify supplier A]
S --> B[Verify supplier B]
S --> C[Verify supplier C]
A --> J[Partial-result join]
B --> J
C --> J
J --> Eval[Evaluation continues]` },
  { title: "Evidence to recommendation", code: `flowchart LR
RS[Research source] --> EX[Structured extraction]
EX --> EV[(Evidence)]
EV --> VE[Cross-check]
VE --> DT[Deterministic totals]
DT --> SH[Shortlist]
SH --> HR[Human review]` },
];

export function Architecture() {
  return (
    <div className="architecture-page">
      <header className="architecture-hero">
        <span className="eyebrow">System dossier / v0.1</span>
        <h1>Designed for evidence,<br />not theatre.</h1>
        <p>SourcePilot separates orchestration, reasoning, deterministic business rules, provider integrations, and durable state. Agents have narrow jobs; the system keeps the receipts.</p>
      </header>
      <section className="principles-strip">
        <span>Persistent by default</span><span>Provider independent</span><span>Bounded concurrency</span><span>Human authority</span>
      </section>
      <section className="architecture-copy">
        <h2>How the system holds together</h2>
        <p>The API accepts work and returns immediately. A database-backed worker claims isolated workflows, resumes completed stages after interruption, and coordinates specialized agents. Every capability invocation is typed, timeout-controlled, retry-bounded, and recorded without secrets or hidden reasoning.</p>
      </section>
      <div className="diagram-grid">
        {diagrams.map((diagram, index) => <Diagram key={diagram.title} index={index + 1} {...diagram} />)}
      </div>
      <section className="decision-grid">
        <article><span>01 / State</span><h2>Recovery is a data problem.</h2><p>Requests, stages, task dependencies, evidence, and recommendations live in PostgreSQL. On restart, the worker marks interrupted work as waiting and continues from completed boundaries.</p></article>
        <article><span>02 / Research</span><h2>Providers are replaceable.</h2><p>Exa and Firecrawl normalize into one search document contract. OpenAI and OpenRouter implement one LLM interface. Agent code does not branch on vendor names.</p></article>
        <article><span>03 / Trust</span><h2>Claims stay attached to sources.</h2><p>First-party and third-party evidence retain URLs, retrieval time, structured claims, and verification state. Conflicts and unavailable values remain visible instead of being guessed away.</p></article>
        <article><span>04 / Control</span><h2>Math is not delegated.</h2><p>LLMs interpret unstructured pages. Application code handles quantities, totals, filters, ordering, transitions, retry limits, and approval rules.</p></article>
        <article><span>05 / Failure</span><h2>One supplier cannot sink the run.</h2><p>Independent verification uses bounded parallel tasks and gathers partial results. Provider fallbacks and explicit unavailable states let evaluation continue honestly.</p></article>
        <article><span>06 / Safety</span><h2>Recommendation is the finish line.</h2><p>The current workflow never orders. Approval is an explicit state transition, preserving a clean seam for a future purchasing agent without weakening human control.</p></article>
      </section>
    </div>
  );
}

function Diagram({ title, code, index }: { title: string; code: string; index: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const id = useId().replaceAll(":", "");
  useEffect(() => {
    mermaid.initialize({ startOnLoad: false, theme: "base", themeVariables: { primaryColor: "#ebe5d8", primaryTextColor: "#171713", primaryBorderColor: "#171713", lineColor: "#e6532f", fontFamily: "Aptos, sans-serif" }, securityLevel: "strict" });
    void mermaid.render(`diagram-${id}`, code).then(({ svg }) => { if (ref.current) ref.current.innerHTML = svg; });
  }, [code, id]);
  return <article className="diagram-card"><header><span>{String(index).padStart(2, "0")}</span><h2>{title}</h2></header><div ref={ref} className="mermaid-output" /></article>;
}

