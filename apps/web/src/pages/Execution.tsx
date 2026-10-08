import { useCallback } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api";
import { Status, readableStatus } from "../components/Status";
import { usePolling } from "../hooks";

export function Execution() {
  const { id = "" } = useParams();
  const requestLoader = useCallback(() => api.getRequest(id), [id]);
  const request = usePolling(requestLoader);
  const workflowId = request.data?.workflow.id;
  const executionLoader = useCallback(
    () => workflowId ? api.getExecution(workflowId) : Promise.reject(new Error("Workflow is loading")),
    [workflowId],
  );
  const execution = usePolling(executionLoader);

  if (!request.data || !execution.data) return <div className="page-state">Loading execution record…</div>;

  return (
    <div className="execution-page">
      <div className="detail-kicker"><Link to={`/requests/${id}`}>← Recommendation</Link><span>Operational view</span></div>
      <header className="execution-header">
        <div><span className="eyebrow">Workflow / {workflowId?.slice(0, 8)}</span><h1>Execution ledger</h1></div>
        <Status status={execution.data.workflow.status} stage={execution.data.workflow.current_stage} />
      </header>
      <p className="execution-intro">High-level operational progress is shown here. Private prompts and model deliberation are never recorded.</p>
      <section className="stage-rail">
        {execution.data.tasks.map((task, index) => (
          <article key={task.id} className={`stage-card stage-card--${task.status}`}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <div><h2>{task.agent_type} agent</h2><p>{readableStatus(task.status, task.agent_type)}</p></div>
            <i aria-hidden="true">{task.status === "completed" ? "✓" : "·"}</i>
          </article>
        ))}
      </section>
      <section className="event-ledger">
        <div className="section-heading compact"><div><span>Receipts</span><h2>Execution events</h2></div><strong>{execution.data.events.length}</strong></div>
        {execution.data.events.map((event) => (
          <div className="event-line" key={event.id}>
            <time>{new Date(event.timestamp).toLocaleTimeString()}</time>
            <strong>{event.agent}</strong>
            <span>{event.event_type.replaceAll("_", " ")}</span>
            <span>{event.capability ?? "workflow"}{event.provider ? ` / ${event.provider}` : ""}</span>
            <Status status={event.status} />
            <small>{event.duration_ms === null ? "—" : `${event.duration_ms} ms`}</small>
          </div>
        ))}
        {execution.data.events.length === 0 && <div className="empty">Events will appear when the worker begins execution.</div>}
      </section>
    </div>
  );
}

