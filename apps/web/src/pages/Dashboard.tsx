import { FormEvent, useCallback, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import { Status } from "../components/Status";
import { usePolling } from "../hooks";

const example = "Find 50 MacBook Pro 14-inch laptops for the company.";

export function Dashboard() {
  const loader = useCallback(() => api.listRequests(), []);
  const { data: requests = [], error, loading, refresh } = usePolling(loader);
  const [requestText, setRequestText] = useState(example);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string>();

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (requestText.trim().length < 10) return;
    setSubmitting(true);
    setSubmitError(undefined);
    try {
      await api.createRequest(requestText.trim());
      setRequestText("");
      await refresh();
    } catch (cause) {
      setSubmitError(cause instanceof Error ? cause.message : "Unable to create request");
    } finally {
      setSubmitting(false);
    }
  }

  const active = requests.filter((item) => !["completed", "failed", "cancelled"].includes(item.workflow.status));
  const recent = requests.filter((item) => ["completed", "failed", "cancelled"].includes(item.workflow.status));

  return (
    <>
      <section className="hero">
        <div className="eyebrow">Procurement intelligence / 01</div>
        <h1>Turn a requirement into a defensible shortlist.</h1>
        <p>
          SourcePilot researches the open web, verifies important claims, and compares offers.
          Every recommendation keeps its evidence attached.
        </p>
        <form className="request-composer" onSubmit={submit}>
          <label htmlFor="procurement-request">What does your company need?</label>
          <div className="composer-row">
            <textarea
              id="procurement-request"
              value={requestText}
              onChange={(event) => setRequestText(event.target.value)}
              placeholder="Find 50 MacBook Pro 14-inch laptops for the company."
              minLength={10}
              maxLength={2000}
              rows={3}
            />
            <button type="submit" disabled={submitting || requestText.trim().length < 10}>
              <span>{submitting ? "Starting…" : "Start sourcing"}</span>
              <b aria-hidden="true">↗</b>
            </button>
          </div>
          <small>Company policies and delivery context are applied automatically.</small>
          {submitError && <div className="alert">{submitError}</div>}
        </form>
      </section>

      <section className="workspace-grid">
        <div className="section-heading">
          <div>
            <span>Live desk</span>
            <h2>Active requests</h2>
          </div>
          <strong>{String(active.length).padStart(2, "0")}</strong>
        </div>
        <div className="request-list">
          {loading && <div className="empty">Loading procurement desk…</div>}
          {error && <div className="alert">{error}</div>}
          {!loading && active.length === 0 && (
            <div className="empty">No active work. Submit a requirement to begin research.</div>
          )}
          {active.map((item, index) => (
            <RequestRow key={item.id} request={item} index={index + 1} />
          ))}
        </div>
      </section>

      <section className="workspace-grid recent-section">
        <div className="section-heading">
          <div>
            <span>Archive</span>
            <h2>Recent requests</h2>
          </div>
          <strong>{String(recent.length).padStart(2, "0")}</strong>
        </div>
        <div className="request-list">
          {recent.length === 0 && <div className="empty">Completed recommendations appear here.</div>}
          {recent.map((item, index) => (
            <RequestRow key={item.id} request={item} index={index + 1} />
          ))}
        </div>
      </section>
    </>
  );
}

function RequestRow({ request, index }: { request: Awaited<ReturnType<typeof api.listRequests>>[number]; index: number }) {
  return (
    <article className="request-row">
      <span className="row-number">{String(index).padStart(2, "0")}</span>
      <div className="request-title">
        <Link to={`/requests/${request.id}`}>{request.original_request}</Link>
        <span>{new Date(request.created_at).toLocaleString()} · {request.company_location}</span>
      </div>
      <Status status={request.workflow.status} stage={request.workflow.current_stage} />
      <Link className="row-action" to={`/requests/${request.id}/execution`} aria-label="View execution">
        ↗
      </Link>
    </article>
  );
}

