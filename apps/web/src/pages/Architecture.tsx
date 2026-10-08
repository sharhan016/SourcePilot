import { useEffect, useId, useRef } from "react";
import mermaid from "mermaid";

import { usePageMotion } from "../motion";

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
  { title: "Evidence to recommendation", code: `flowchart LR
RS[Research source] --> EX[Structured extraction]
EX --> EV[(Evidence)]
EV --> VE[Cross-check]
VE --> DT[Deterministic totals]
DT --> SH[Shortlist]
SH --> HR[Human review]` },
];

export function Architecture() {
  const pageRef = useRef<HTMLDivElement>(null);
  usePageMotion(pageRef);

  return (
    <div className="architecture-page" ref={pageRef}>
      <header className="architecture-hero" data-reveal>
        <h1>How SourcePilot works</h1>
        <p>Research, verification, evaluation, and approval stay separate.</p>
      </header>
      <div className="diagram-grid" data-reveal>
        {diagrams.map((diagram) => <Diagram key={diagram.title} {...diagram} />)}
      </div>
    </div>
  );
}

function Diagram({ title, code }: { title: string; code: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const id = useId().replaceAll(":", "");
  useEffect(() => {
    mermaid.initialize({ startOnLoad: false, theme: "base", themeVariables: { primaryColor: "#ebe5d8", primaryTextColor: "#171713", primaryBorderColor: "#171713", lineColor: "#e6532f", fontFamily: "Aptos, sans-serif" }, securityLevel: "strict" });
    void mermaid.render(`diagram-${id}`, code).then(({ svg }) => { if (ref.current) ref.current.innerHTML = svg; });
  }, [code, id]);
  return <article className="diagram-card" data-stack><h2>{title}</h2><div ref={ref} className="mermaid-output" /></article>;
}
