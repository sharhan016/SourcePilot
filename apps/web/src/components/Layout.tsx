import { NavLink, Outlet } from "react-router-dom";

import { api } from "../api";
import { usePolling } from "../hooks";

const defaultContext = {
  company_name: "IT Essentials (ITE)",
  company_location: "Sharjah, United Arab Emirates",
};

export function Layout() {
  const { data: context = defaultContext } = usePolling(api.getContext, 60_000);

  return (
    <div className="shell">
      <header className="masthead">
        <NavLink to="/" className="brand" aria-label="SourcePilot home">
          <span className="brand-mark">SP</span>
          <span>SourcePilot</span>
        </NavLink>
        <nav aria-label="Main navigation">
          <NavLink to="/">Procurement</NavLink>
          <NavLink to="/architecture">Architecture</NavLink>
        </nav>
        <div className="company-context">
          <span>Company context</span>
          <strong>{context.company_name} · {context.company_location}</strong>
        </div>
      </header>
      <main>
        <Outlet />
      </main>
      <footer>
        <span>SourcePilot / evidence before action</span>
        <span>Purchasing requires human approval</span>
      </footer>
    </div>
  );
}
