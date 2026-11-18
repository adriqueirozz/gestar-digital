import { useRef, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import Botao from "../components/ui/Botao.jsx";
import Tag from "../components/ui/Tag.jsx";
import { esquecerUsuario, getRecentes, NOME_PERFIL } from "../auth/sessao.js";
import { useSessao } from "../auth/useSessao.js";
import "./login.css";

const TOM_PERFIL = { enfermagem: "rosa", medico: "info", gestao: "roxo" };

export default function Login() {
  const { usuario, entrar } = useSessao();
  const navigate = useNavigate();
  const local = useLocation();
  const [params] = useSearchParams();

  const [login, setLogin] = useState(params.get("login") || "");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [recentes, setRecentes] = useState(getRecentes);
  const campoSenha = useRef(null);

  const destino = local.state?.de || "/";

  function escolher(u) {
    setLogin(u.login);
    setSenha("");
    setErro("");
    campoSenha.current?.focus();
  }

  function esquecer(u) {
    esquecerUsuario(u.login);
    setRecentes(getRecentes());
    if (login === u.login) setLogin("");
  }

  async function enviar(e) {
    e.preventDefault();
    if (!login.trim() || !senha) {
      setErro("Informe o login e a senha.");
      return;
    }
    setEnviando(true);
    setErro("");
    try {
      await entrar(login.trim(), senha);
      navigate(destino, { replace: true });
    } catch (falha) {
      setErro(falha.message);
      setSenha("");
      campoSenha.current?.focus();
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="login-tela">
      <section className="login-caixa" aria-labelledby="login-titulo">
        <div className="login-marca">Gestar Digital · COB</div>
        <h1 id="login-titulo">{usuario ? "Trocar de usuário" : "Entrar"}</h1>

        {usuario && (
          <p className="login-nota">
            Você está como <strong>{usuario.nome}</strong> ({NOME_PERFIL[usuario.perfil]}).{" "}
            <Link to="/">Voltar ao painel</Link>
          </p>
        )}

        {recentes.length > 0 && (
          <div className="login-recentes">
            <h2>Usuários deste computador</h2>
            <ul>
              {recentes.map((u) => (
                <li key={u.login} className={u.login === login ? "ativo" : undefined}>
                  <button type="button" className="login-recente" onClick={() => escolher(u)}>
                    <span className="login-recente-nome">{u.nome}</span>
                    <Tag tom={TOM_PERFIL[u.perfil] || "neutro"}>{NOME_PERFIL[u.perfil] || u.perfil}</Tag>
                  </button>
                  <button type="button" className="login-esquecer" onClick={() => esquecer(u)}
                          aria-label={`Remover ${u.nome} da lista`} title="Remover da lista">×</button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <form className="login-form" onSubmit={enviar} noValidate>
          <label className="login-campo">
            Login
            <input value={login} onChange={(e) => setLogin(e.target.value)} autoComplete="username"
                   autoCapitalize="none" spellCheck="false" autoFocus={!login} />
          </label>
          <label className="login-campo">
            Senha
            <input ref={campoSenha} type="password" value={senha} onChange={(e) => setSenha(e.target.value)}
                   autoComplete="current-password" autoFocus={Boolean(login)} />
          </label>
          {erro && <p className="login-erro" role="alert">{erro}</p>}
          <Botao type="submit" variante="primario" disabled={enviando}>
            {enviando ? "Entrando…" : "Entrar"}
          </Botao>
        </form>

        <p className="login-rodape">Computador compartilhado? Ao terminar, use <strong>Sair</strong> no seu nome, no topo da tela.</p>
      </section>
    </main>
  );
}
