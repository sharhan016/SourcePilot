const labels: Record<string, string> = {
  queued: "Queued",
  running: "In progress",
  waiting: "Waiting",
  completed: "Ready for review",
  failed: "Needs attention",
  cancelled: "Cancelled",
  research: "Researching suppliers",
  verification: "Verifying evidence",
  evaluation: "Comparing options",
  recommendation: "Preparing recommendation",
  review: "Ready for review",
};

export function readableStatus(status: string, stage?: string) {
  if (status === "running" && stage) return labels[stage] ?? "In progress";
  return labels[status] ?? status.replaceAll("_", " ");
}

export function Status({ status, stage }: { status: string; stage?: string }) {
  return (
    <span className={`status status--${status}`}>
      <i aria-hidden="true" />
      {readableStatus(status, stage)}
    </span>
  );
}

