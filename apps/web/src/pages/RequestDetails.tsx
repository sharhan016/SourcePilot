import { useCallback, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { api } from "../api";
import { RequestComposer } from "../components/RequestComposer";
import { readableStatus } from "../components/Status";
import { usePolling } from "../hooks";
import type { Execution, ExecutionEvent, Product, Recommendation, RequestDetail, Supplier, WorkflowTask } from "../types";

const stages = ["research", "verification", "evaluation", "recommendation"] as const;

export function RequestDetails({ executionOpen = false }: { executionOpen?: boolean }) {
  const { id = "" } = useParams();
  const detailLoader = useCallback(() => api.getRequest(id), [id]);
  const detail = usePolling(detailLoader, 2_000);
  const workflowId = detail.data?.workflow.id;
  const executionLoader = useCallback(
    () => workflowId ? api.getExecution(workflowId) : Promise.resolve(undefined),
    [workflowId],
  );
  const execution = usePolling<Execution | undefined>(executionLoader, 2_000);

  return (
    <section className="conversation-workspace">
      <div className="conversation-scroll">
        <div className="conversation-thread">
          {detail.loading && !detail.data && <LoadingTurn />}
          {detail.error && !detail.data && <ErrorTurn message={detail.error} />}
          {detail.data && (
            <ProcurementConversation
              detail={detail.data}
              execution={execution.data}
              loadError={detail.error ?? execution.error}
              defaultExecutionOpen={executionOpen}
              refresh={detail.refresh}
            />
          )}
        </div>
      </div>
      <div className="composer-dock">
        <RequestComposer />
        <p>Start another request at any time. Each run continues independently.</p>
      </div>
    </section>
  );
}

function ProcurementConversation({
  detail,
  execution,
  loadError,
  defaultExecutionOpen,
  refresh,
}: {
  detail: RequestDetail;
  execution?: Execution;
  loadError?: string;
  defaultExecutionOpen: boolean;
  refresh: () => Promise<void>;
}) {
  const offers = useMemo(
    () => detail.suppliers.flatMap((supplier) => supplier.products.map((product) => ({ supplier, product }))),
    [detail.suppliers],
  );

  return (
    <>
      <article className="conversation-turn conversation-turn--user">
        <div className="turn-label">You</div>
        <p>{detail.original_request}</p>
      </article>

      <article className="conversation-turn conversation-turn--assistant">
        <div className="assistant-mark" aria-hidden="true">✦</div>
        <div className="assistant-content">
          {loadError && <div className="inline-notice inline-notice--warning">Live updates paused. Showing the latest saved data.</div>}
          <WorkflowProgress detail={detail} execution={execution} />
          {offers.length > 0 && <Results detail={detail} offers={offers} />}
          {detail.recommendation && <RecommendationPanel requestId={detail.id} recommendation={detail.recommendation} refresh={refresh} />}
          {detail.workflow.status === "failed" && (
            <div className="inline-notice inline-notice--error">
              <strong>This run needs attention.</strong>
              <span>{detail.workflow.error ?? "The workflow stopped before completion. Available partial results are preserved above."}</span>
            </div>
          )}
          {execution && <ExecutionDetails execution={execution} defaultOpen={defaultExecutionOpen} />}
        </div>
      </article>
    </>
  );
}

function WorkflowProgress({ detail, execution }: { detail: RequestDetail; execution?: Execution }) {
  const tasks = execution?.tasks ?? [];
  const currentTask = tasks.find((task) => task.status === "running") ?? tasks.find((task) => task.agent_type === detail.workflow.current_stage);
  const currentStage = currentTask?.agent_type ?? detail.workflow.current_stage;
  const verifiedOffers = detail.suppliers.flatMap((supplier) => supplier.products).filter((product) => product.verification_status === "verified").length;

  return (
    <section className="workflow-progress" aria-label="Procurement workflow progress">
      <header className="workflow-heading">
        <div>
          <span className={`live-dot live-dot--${detail.workflow.status}`} />
          <strong>{workflowTitle(detail.workflow.status, currentStage)}</strong>
        </div>
        <span>{readableStatus(detail.workflow.status, currentStage)}</span>
      </header>

      <div className="stage-list">
        {stages.map((stage) => {
          const task = tasks.find((candidate) => candidate.agent_type === stage);
          const status = task?.status ?? inferStageStatus(stage, currentStage, detail.workflow.status);
          const prominent = status === "running" || (detail.workflow.status === "queued" && stage === "research");
          return (
            <div className={`stage-row stage-row--${status} ${prominent ? "stage-row--current" : ""}`} key={stage}>
              <span className="stage-indicator">{status === "completed" ? "✓" : stages.indexOf(stage) + 1}</span>
              <div>
                <strong>{capitalize(stage)}</strong>
                <p>{stageMessage(stage, status, detail, verifiedOffers, execution?.events ?? [])}</p>
              </div>
              {status === "running" && <span className="activity-pulse" aria-label="Active" />}
            </div>
          );
        })}
      </div>

      {currentStage === "verification" && detail.suppliers.length > 1 && (
        <div className="parallel-activity">
          <span>{detail.suppliers.length} suppliers in parallel verification</span>
          <div>
            {detail.suppliers.slice(0, 5).map((supplier) => <i key={supplier.id} title={supplier.name}>{initials(supplier.name)}</i>)}
            {detail.suppliers.length > 5 && <i>+{detail.suppliers.length - 5}</i>}
          </div>
        </div>
      )}
    </section>
  );
}

function Results({
  detail,
  offers,
}: {
  detail: RequestDetail;
  offers: Array<{ supplier: Supplier; product: Product }>;
}) {
  const [expanded, setExpanded] = useState(false);
  const evaluationBySource = new Map(
    (detail.recommendation?.evaluation_results ?? []).map((result) => [String(result.source_url ?? ""), result]),
  );
  const selectedSources = new Set(
    (detail.recommendation?.selected_options ?? []).map((option) => String(option.source_url ?? "")),
  );
  const visible = expanded ? offers : offers.slice(0, 5);

  return (
    <section className="result-block">
      <div className="section-heading">
        <div><h2>Supplier comparison</h2><span>{offers.length} offers</span></div>
        {offers.length > 5 && <button type="button" onClick={() => setExpanded((value) => !value)}>{expanded ? "Show less" : "View all"}</button>}
      </div>
      <div className="comparison-list" role="table" aria-label="Supplier and product comparison">
        <div className="comparison-head" role="row">
          <span>Supplier</span><span>Price</span><span>Availability</span><span>Delivery</span><span>Evidence</span>
        </div>
        {visible.map(({ supplier, product }) => {
          const evaluation = evaluationBySource.get(product.source_url);
          const missing = missingFields(product);
          const recommended = selectedSources.has(product.source_url);
          return (
            <div className={`comparison-row ${recommended ? "comparison-row--recommended" : ""}`} role="row" key={product.id}>
              <div className="supplier-cell">
                <strong>{supplier.name}{recommended && <em>Recommended</em>}</strong>
                <span>{product.name}</span>
                {missing.length > 0 && <small>Missing: {missing.join(", ")}</small>}
              </div>
              <div>
                <strong>{product.unit_price ? formatMoney(product.unit_price, product.currency) : "Not listed"}</strong>
                {typeof evaluation?.total_cost === "string" && <span>{formatMoney(evaluation.total_cost, String(evaluation.currency ?? product.currency ?? "AED"))} total</span>}
              </div>
              <div className="availability-cell">
                <strong>{product.availability ?? "Unconfirmed"}</strong>
                <span>{product.warranty ?? "Warranty unconfirmed"}</span>
              </div>
              <span>{product.delivery ?? "Unconfirmed"}</span>
              <a href={product.source_url} target="_blank" rel="noreferrer">{capitalize(product.verification_status)} ↗</a>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function RecommendationPanel({
  requestId,
  recommendation,
  refresh,
}: {
  requestId: string;
  recommendation: Recommendation;
  refresh: () => Promise<void>;
}) {
  const [reviewing, setReviewing] = useState(false);
  const [reviewError, setReviewError] = useState<string>();
  const shortlisted = recommendation.evaluation_results.filter((result) => result.qualifies === true).slice(0, 3);

  async function review(decision: "approved" | "rejected") {
    setReviewing(true);
    setReviewError(undefined);
    try {
      await api.review(requestId, decision);
      await refresh();
    } catch (cause) {
      setReviewError(cause instanceof Error ? cause.message : "Unable to save decision");
    } finally {
      setReviewing(false);
    }
  }

  return (
    <section className="recommendation-block">
      <div className="recommendation-kicker"><span>✦</span> Recommendation</div>
      <h2>{recommendation.reasoning_summary}</h2>
      {recommendation.total_cost && (
        <div className="recommendation-total">
          <span>Estimated total</span>
          <strong>{formatMoney(recommendation.total_cost, recommendation.currency)}</strong>
        </div>
      )}
      {shortlisted.length > 1 && (
        <div className="tradeoffs">
          {shortlisted.map((option) => (
            <div key={String(option.source_url)}>
              <strong>{String(option.supplier)}</strong>
              <span>{option.total_cost ? `${formatMoney(String(option.total_cost), String(option.currency ?? "AED"))} · ` : ""}{option.delivery ? String(option.delivery) : "Delivery unconfirmed"}</span>
            </div>
          ))}
        </div>
      )}
      {recommendation.status === "ready" ? (
        <div className="review-actions">
          <button type="button" disabled={reviewing} onClick={() => void review("approved")}>Approve</button>
          <button type="button" disabled={reviewing} onClick={() => void review("rejected")}>Reject</button>
        </div>
      ) : (
        <div className={`decision-state decision-state--${recommendation.status}`}>{capitalize(recommendation.status)}</div>
      )}
      {reviewError && <p className="composer-error" role="alert">{reviewError}</p>}
    </section>
  );
}

function ExecutionDetails({ execution, defaultOpen }: { execution: Execution; defaultOpen: boolean }) {
  return (
    <details className="execution-details" open={defaultOpen}>
      <summary>
        <span>Execution details</span>
        <small>{execution.events.length} events</small>
      </summary>
      <div className="event-list">
        {execution.events.map((event) => <EventRow event={event} key={event.id} />)}
        {execution.events.length === 0 && <p className="quiet-state">Events will appear as agents begin work.</p>}
      </div>
    </details>
  );
}

function EventRow({ event }: { event: ExecutionEvent }) {
  return (
    <div className="event-row">
      <time>{new Date(event.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</time>
      <strong>{capitalize(event.agent)}</strong>
      <span>{eventLabel(event)}</span>
      <i className={`event-state event-state--${event.status}`}>{capitalize(event.status)}</i>
    </div>
  );
}

function LoadingTurn() {
  return <div className="center-state"><span className="button-spinner button-spinner--dark" /> Loading request…</div>;
}

function ErrorTurn({ message }: { message: string }) {
  return <div className="center-state center-state--error"><strong>Unable to open this request.</strong><span>{message}</span></div>;
}

function workflowTitle(status: string, stage: string) {
  if (status === "completed") return "Recommendation ready";
  if (status === "failed") return "Workflow interrupted";
  if (status === "queued") return "Request queued";
  return `${capitalize(stage)} agent is working`;
}

function inferStageStatus(stage: typeof stages[number], current: string, workflowStatus: string) {
  const currentIndex = stages.indexOf(current as typeof stages[number]);
  const stageIndex = stages.indexOf(stage);
  if (workflowStatus === "completed" || current === "review") return "completed";
  if (stageIndex < currentIndex) return "completed";
  if (stage === current && workflowStatus === "failed") return "failed";
  if (stage === current && workflowStatus === "running") return "running";
  return "queued";
}

function stageMessage(
  stage: typeof stages[number],
  status: string,
  detail: RequestDetail,
  verifiedOffers: number,
  events: ExecutionEvent[],
) {
  if (status === "failed") return detail.workflow.error ?? "Stage failed.";
  if (status === "queued" || status === "waiting") return "Waiting";
  if (status === "running") {
    if (stage === "research") return "Researching suppliers…";
    if (stage === "verification") return "Verifying supplier information…";
    if (stage === "evaluation") return "Comparing price, availability, warranty, and delivery.";
    return "Preparing recommendations.";
  }
  if (stage === "research") return `${detail.suppliers.length} suppliers discovered.`;
  if (stage === "verification") return `${verifiedOffers} offers verified.`;
  if (stage === "evaluation") {
    const compared = completedCount(events, "evaluation", "compared");
    return compared === null ? "Offers compared." : `${compared} offers compared.`;
  }
  return "Recommendation prepared.";
}

function completedCount(events: ExecutionEvent[], agent: string, key: string) {
  const event = [...events].reverse().find((candidate) => candidate.agent === agent && candidate.event_type === "task_completed");
  const value = event?.metadata_json[key];
  return typeof value === "number" ? value : null;
}

function eventLabel(event: ExecutionEvent) {
  if (event.event_type === "task_started") return "Started work";
  if (event.event_type === "task_completed") return "Completed handoff";
  if (event.capability) return `${event.capability.replaceAll("_", " ")}${event.provider ? ` · ${event.provider}` : ""}`;
  return event.event_type.replaceAll("_", " ");
}

function missingFields(product: Product) {
  const missing: string[] = [];
  if (!product.unit_price) missing.push("price");
  if (!product.availability) missing.push("availability");
  if (!product.warranty) missing.push("warranty");
  if (!product.delivery) missing.push("delivery");
  return missing;
}

function initials(value: string) {
  return value.split(/\s+/).slice(0, 2).map((word) => word[0]).join("").toUpperCase();
}

function capitalize(value: string) {
  return value ? `${value[0].toUpperCase()}${value.slice(1).replaceAll("_", " ")}` : value;
}

function formatMoney(value: string, currency: string | null) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return `${currency ?? "AED"} ${value}`;
  return new Intl.NumberFormat("en-AE", {
    style: "currency",
    currency: currency ?? "AED",
    maximumFractionDigits: 0,
  }).format(amount);
}
