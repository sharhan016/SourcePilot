import { useCallback, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api";
import { Status, readableStatus } from "../components/Status";
import { usePolling } from "../hooks";
import { usePageMotion } from "../motion";

export function Execution() {
  const pageRef = useRef<HTMLDivElement>(null);
  usePageMotion(pageRef);
  const [showAllEvents, setShowAllEvents] = useState(false);
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
  const visibleEvents = showAllEvents
    ? execution.data.events
    : execution.data.events.slice(-8);

  return (
    <div className="execution-page" ref={pageRef}>
      <div className="detail-kicker"><Link to={`/requests/${id}`}>← Request</Link><Status status={execution.data.workflow.status} stage={execution.data.workflow.current_stage} /></div>
      <header className="execution-header" data-reveal>
        <h1>Run</h1>
      </header>
      <section className="stage-rail" data-reveal>
        {execution.data.tasks.map((task) => (
          <article key={task.id} className={`stage-card stage-card--${task.status}`} data-stack>
            <div><h2>{task.agent_type} agent</h2><p>{task.status === "completed" ? "Complete" : readableStatus(task.status, task.agent_type)}</p></div>
            <i aria-hidden="true">{task.status === "completed" ? "✓" : "·"}</i>
          </article>
        ))}
      </section>
      <section className="event-ledger" data-reveal>
        <div className="list-heading"><h2>Events</h2><span>{execution.data.events.length}</span></div>
        {visibleEvents.map((event) => (
          <div className="event-line" key={event.id}>
            <time>{new Date(event.timestamp).toLocaleTimeString()}</time>
            <strong>{event.agent}</strong>
            <span>{event.event_type.replaceAll("_", " ")}</span>
            <span>{event.capability ?? "workflow"}{event.provider ? ` / ${event.provider}` : ""}</span>
            <Status status={event.status} />
            <small>{event.duration_ms === null ? "—" : `${event.duration_ms} ms`}</small>
          </div>
        ))}
        {execution.data.events.length === 0 && <div className="empty">No events yet.</div>}
        {execution.data.events.length > 8 && (
          <button className="text-button" onClick={() => setShowAllEvents((value) => !value)}>
            {showAllEvents ? "Show latest" : `Show all ${execution.data.events.length}`}
          </button>
        )}
      </section>
    </div>
  );
}
