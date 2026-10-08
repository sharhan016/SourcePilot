import { FormEvent, KeyboardEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";
import { useWorkspace } from "./Layout";

type RequestComposerProps = {
  centered?: boolean;
};

export function RequestComposer({ centered = false }: RequestComposerProps) {
  const navigate = useNavigate();
  const { refreshRequests } = useWorkspace();
  const [value, setValue] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string>();

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    const requestText = value.trim();
    if (requestText.length < 10 || submitting) return;
    setSubmitting(true);
    setError(undefined);
    try {
      const request = await api.createRequest(requestText);
      setValue("");
      await refreshRequests();
      navigate(`/requests/${request.id}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to create request");
    } finally {
      setSubmitting(false);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submit();
    }
  }

  return (
    <form className={`workspace-composer ${centered ? "workspace-composer--centered" : ""}`} onSubmit={submit}>
      <div className="composer-field">
        <label className="sr-only" htmlFor={centered ? "initial-request" : "next-request"}>Procurement request</label>
        <textarea
          id={centered ? "initial-request" : "next-request"}
          value={value}
          rows={1}
          minLength={10}
          maxLength={2000}
          placeholder="What are you looking for?"
          aria-invalid={Boolean(error)}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          type="submit"
          aria-label="Send procurement request"
          disabled={submitting || value.trim().length < 10}
        >
          {submitting ? <span className="button-spinner" /> : <span aria-hidden="true">↑</span>}
        </button>
      </div>
      {error && <p className="composer-error" role="alert">{error}</p>}
    </form>
  );
}
