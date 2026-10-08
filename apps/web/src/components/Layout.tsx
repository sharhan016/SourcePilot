import { createContext, useContext, useEffect, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";

import { api } from "../api";
import { usePolling } from "../hooks";
import type { CompanyContext, ProcurementRequest } from "../types";

type WorkspaceContextValue = {
  company: CompanyContext;
  requests: ProcurementRequest[];
  refreshRequests: () => Promise<void>;
};

const defaultCompany: CompanyContext = {
  company_name: "IT Essentials (ITE)",
  company_location: "Sharjah, United Arab Emirates",
  country: "United Arab Emirates",
  currency: "AED",
  procurement_region: "UAE",
  sourcing_regions: ["United Arab Emirates", "GCC"],
};

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("Workspace context is unavailable");
  return value;
}

export function Layout() {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const context = usePolling(api.getContext, 60_000);
  const requestList = usePolling(api.listRequests, 2_500);
  const company = context.data ?? defaultCompany;

  useEffect(() => {
    if (window.innerWidth < 820) setSidebarOpen(false);
  }, [location.pathname]);

  return (
    <WorkspaceContext.Provider
      value={{
        company,
        requests: requestList.data ?? [],
        refreshRequests: requestList.refresh,
      }}
    >
      <div className={`workspace-shell ${sidebarOpen ? "sidebar-is-open" : ""}`}>
        <button
          className="sidebar-toggle"
          type="button"
          aria-label={sidebarOpen ? "Close request history" : "Open request history"}
          aria-expanded={sidebarOpen}
          aria-controls="request-sidebar"
          onClick={() => setSidebarOpen((value) => !value)}
        >
          <span /><span /><span />
        </button>

        <aside className="request-sidebar" id="request-sidebar" aria-hidden={!sidebarOpen} inert={!sidebarOpen}>
          <div className="sidebar-top">
            <Link className="new-request" to="/" onClick={() => setSidebarOpen(false)}>
              <span aria-hidden="true">＋</span>
              New request
            </Link>
          </div>

          <nav className="request-history" aria-label="Previous procurement requests">
            <p>Requests</p>
            {requestList.loading && !(requestList.data?.length) && <span className="sidebar-note">Loading…</span>}
            {requestList.error && !(requestList.data?.length) && <span className="sidebar-note sidebar-note--error">Unavailable</span>}
            {(requestList.data ?? []).map((request) => {
              const active = location.pathname.startsWith(`/requests/${request.id}`);
              return (
                <Link
                  key={request.id}
                  className={`history-item ${active ? "active" : ""}`}
                  to={`/requests/${request.id}`}
                  onClick={() => window.innerWidth < 820 && setSidebarOpen(false)}
                  aria-current={active ? "page" : undefined}
                >
                  <span className="history-title">{request.original_request}</span>
                  <span
                    className={`history-status history-status--${request.workflow.status}`}
                    title={request.workflow.status}
                    aria-label={request.workflow.status}
                  />
                </Link>
              );
            })}
            {!requestList.loading && !(requestList.data?.length) && <span className="sidebar-note">No requests yet</span>}
          </nav>

          <div className="sidebar-company">
            <strong>{company.company_name}</strong>
            <span>{company.procurement_region} · {company.currency}</span>
          </div>
        </aside>

        {sidebarOpen && (
          <button className="sidebar-scrim" type="button" aria-label="Close request history" onClick={() => setSidebarOpen(false)} />
        )}

        <main className="workspace-main">
          <Outlet />
        </main>

        {!sidebarOpen && (
          <div className="company-corner">
            <strong>{company.company_name}</strong>
            <span>{company.procurement_region}</span>
          </div>
        )}
      </div>
    </WorkspaceContext.Provider>
  );
}
