import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getRecentes, NOME_PERFIL } from "../auth/sessao.js";
import { useSessao } from "../auth/useSessao.js";

// Nome e perfil no cabeçalho, com troca rápida de usuário (3 computadores compartilhados no posto).
export default function MenuUsuario() {
  const { usuario, sair } = useSessao();
  const navigate = useNavigate();
  const [aberto, setAberto] = useState(false);
  const caixa = useRef(null);

  useEffect(() => {
    if (!aberto) return;
    const aoClicarFora = (e) => caixa.current && !caixa.current.contains(e.target) && setAberto(false);
    const aoTeclar = (e) => e.key === "Escape" && setAberto(false);
    document.addEventListener("mousedown", aoClicarFora);
    document.addEventListener("keydown", aoTeclar);
    return () => {
      document.removeEventListener("mousedown", aoClicarFora);
      document.removeEventListener("keydown", aoTeclar);
    };
  }, [aberto]);

  if (!usuario) return null;

  const outros = aberto ? getRecentes().filter((u) => u.login !== usuario.login) : [];

  function trocarPara(login) {
    setAberto(false);
    navigate(login ? `/login?login=${encodeURIComponent(login)}` : "/login");
  }

  function encerrar() {
    setAberto(false);
    sair();
    navigate("/login", { replace: true });
  }

  return (
    <div className="menu-usuario" ref={caixa}>
      <button type="button" className="menu-usuario-botao" aria-haspopup="menu" aria-expanded={aberto}
              onClick={() => setAberto((a) => !a)}>
        <span className="menu-usuario-nome">{usuario.nome}</span>
        <span className="menu-usuario-perfil">{NOME_PERFIL[usuario.perfil] || usuario.perfil}</span>
        {!usuario.pode_editar && <span className="menu-usuario-leitura">Somente leitura</span>}
        <span aria-hidden="true">▾</span>
      </button>

      {aberto && (
        <div className="menu-usuario-lista" role="menu">
          {outros.length > 0 && <div className="menu-usuario-titulo">Trocar para</div>}
          {outros.map((u) => (
            <button key={u.login} type="button" role="menuitem" onClick={() => trocarPara(u.login)}>
              {u.nome} <small>{NOME_PERFIL[u.perfil] || u.perfil}</small>
            </button>
          ))}
          <button type="button" role="menuitem" onClick={() => trocarPara(null)}>Outro usuário…</button>
          <button type="button" role="menuitem" className="menu-usuario-sair" onClick={encerrar}>Sair</button>
        </div>
      )}
    </div>
  );
}
