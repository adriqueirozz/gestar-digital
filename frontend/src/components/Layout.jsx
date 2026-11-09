import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { getHealth } from "../api.js";

const LINKS = [
  { to: "/", label: "Painel" },
  { to: "/pendencias", label: "Pendências" },
  { to: "/relatorio", label: "Relatório" },
  { to: "/integracao", label: "Integração" },
];

export default function Layout() {
  const [apiOnline, setApiOnline] = useState(null);

  useEffect(() => {
    getHealth()
      .then(() => setApiOnline(true))
      .catch(() => setApiOnline(false));
  }, []);

  return (
    <div className="app">
      <header className="topo">
        <strong>Gestar Digital · COB</strong>
        <span className={`api ${apiOnline ? "ok" : "off"}`}>
          {apiOnline === null ? "verificando API..." : apiOnline ? "API online" : "API offline"}
        </span>
      </header>

      <nav className="menu" aria-label="Principal">
        {LINKS.map((l) => (
          <NavLink key={l.to} to={l.to} end={l.to === "/"}>
            {l.label}
          </NavLink>
        ))}
      </nav>

      <main className="conteudo">
        <Outlet />
      </main>
    </div>
  );
}