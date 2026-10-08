import { NavLink, Outlet } from "react-router-dom";

export function Layout() {
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
          <strong>Acme Operations · Bengaluru</strong>
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

