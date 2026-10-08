import { useCallback, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api";
import { Status } from "../components/Status";
import { usePolling } from "../hooks";

export function RequestDetails() {
  const { id = "" } = useParams();
  const loader = useCallback(() => api.getRequest(id), [id]);
  const { data, error, loading, refresh } = usePolling(loader);
  const [reviewing, setReviewing] = useState(false);

  async function review(decision: "approved" | "rejected") {
    setReviewing(true);
    try {
      await api.review(id, decision);
      await refresh();
    } finally {
      setReviewing(false);
    }
  }

  if (loading && !data) return <div className="page-state">Loading procurement record…</div>;
  if (error && !data) return <div className="page-state alert">{error}</div>;
  if (!data) return null;

  return (
    <div className="detail-page">
      <div className="detail-kicker">
        <Link to="/">← Procurement desk</Link>
        <span>Request {data.id.slice(0, 8).toUpperCase()}</span>
      </div>
      <header className="detail-header">
        <div>
          <Status status={data.workflow.status} stage={data.workflow.current_stage} />
          <h1>{data.original_request}</h1>
          <p>{data.company_name} · {data.company_location}</p>
        </div>
        <Link className="secondary-action" to={`/requests/${id}/execution`}>View execution ↗</Link>
      </header>

      {data.recommendation ? (
        <section className="recommendation-panel">
          <div className="recommendation-lead">
            <span className="eyebrow">Recommendation / evidence-backed</span>
            <h2>{data.recommendation.reasoning_summary}</h2>
            {data.recommendation.total_cost && (
              <div className="total-cost">
                <span>Estimated total</span>
                <strong>{formatMoney(data.recommendation.total_cost, data.recommendation.currency)}</strong>
              </div>
            )}
          </div>
          <div className="approval-panel">
            <span>Human checkpoint</span>
            <p>No order is placed automatically. Confirm evidence and commercial terms first.</p>
            {data.recommendation.status === "ready" ? (
              <div className="approval-actions">
                <button disabled={reviewing} onClick={() => void review("approved")}>Approve shortlist</button>
                <button disabled={reviewing} className="reject" onClick={() => void review("rejected")}>Reject</button>
              </div>
            ) : (
              <Status status={data.recommendation.status} />
            )}
          </div>
        </section>
      ) : (
        <section className="in-progress-panel">
          <span className="pulse" />
          <div><strong>Work is underway</strong><p>Results will appear here as soon as verification and comparison complete.</p></div>
        </section>
      )}

      <section className="results-section">
        <div className="section-heading compact">
          <div><span>Market scan</span><h2>Supplier evidence</h2></div>
          <strong>{String(data.suppliers.length).padStart(2, "0")}</strong>
        </div>
        <div className="supplier-table" role="table" aria-label="Supplier results">
          <div className="supplier-head" role="row">
            <span>Supplier / product</span><span>Unit price</span><span>Availability</span><span>Evidence</span>
          </div>
          {data.suppliers.flatMap((supplier) => supplier.products.map((product) => (
            <div className="supplier-line" role="row" key={product.id}>
              <div><strong>{supplier.name}</strong><span>{product.name}</span></div>
              <span>{product.unit_price ? formatMoney(product.unit_price, product.currency) : "Not published"}</span>
              <span>{product.availability ?? "Unconfirmed"}</span>
              <a href={product.source_url} target="_blank" rel="noreferrer">{product.verification_status} ↗</a>
            </div>
          )))}
          {data.suppliers.length === 0 && <div className="empty">No supplier evidence has been persisted yet.</div>}
        </div>
      </section>
    </div>
  );
}

function formatMoney(value: string, currency: string | null) {
  return new Intl.NumberFormat(undefined, { style: "currency", currency: currency ?? "AED", maximumFractionDigits: 0 }).format(Number(value));
}
