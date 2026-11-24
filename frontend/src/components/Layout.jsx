import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { getHealth } from "../api.js";
import MenuUsuario from "./MenuUsuario.jsx";

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
      {/* uma faixa só: marca, menu e usuário (no celular o menu vai para a barra de baixo) */}
      <header className="topo">
        <strong className="marca">Gestar Digital <span>COB</span></strong>
        <nav className="menu" aria-label="Principal">
          {LINKS.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.to === "/"}>
              {l.label}
            </NavLink>
          ))}
        </nav>
        <MenuUsuario />
      </header>

      {/* a situação da API só aparece quando há problema */}
      {apiOnline === false && (
        <div className="aviso-conexao" role="alert">
          Sem conexão com o servidor. Os dados podem estar desatualizados.
        </div>
      )}

      <main className="conteudo">
        <Outlet />
      </main>
    </div>
  );
}
