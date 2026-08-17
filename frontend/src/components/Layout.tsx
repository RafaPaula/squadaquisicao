import { NavLink, Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-brand">
          <span className="app-brand-mark">DB1</span>
          <span>
            Talent Mirror <span className="app-brand-sub">· Banco de Currículos</span>
          </span>
        </div>
        <nav className="app-nav">
          <NavLink to="/categorizar" className={({ isActive }) => (isActive ? "active" : "")}>
            Categorizar
          </NavLink>
          <NavLink to="/revisar" className={({ isActive }) => (isActive ? "active" : "")}>
            Revisar por categoria
          </NavLink>
          <NavLink to="/funil" className={({ isActive }) => (isActive ? "active" : "")}>
            Funil de Vagas
          </NavLink>
        </nav>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
