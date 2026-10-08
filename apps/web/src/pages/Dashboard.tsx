import { RequestComposer } from "../components/RequestComposer";

export function Dashboard() {
  return (
    <section className="empty-workspace">
      <div className="initial-prompt">
        <RequestComposer centered />
        <p>Try: Source 25 business laptops with UAE warranty and delivery.</p>
      </div>
    </section>
  );
}
