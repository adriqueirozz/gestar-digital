import { useCallback, useEffect, useMemo, useState } from "react";
import { entrar as apiEntrar, getUsuarioLogado } from "../api.js";
import { EVENTO_SESSAO_EXPIRADA, getToken, lembrarUsuario, setToken } from "./sessao.js";
import { SessaoContext } from "./useSessao.js";

export default function SessaoProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  // com token guardado, confirma na API quem é o usuário antes de mostrar as telas
  const [carregando, setCarregando] = useState(() => Boolean(getToken()));

  useEffect(() => {
    if (!getToken()) return;
    getUsuarioLogado()
      .then(setUsuario)
      .catch(() => setUsuario(null))
      .finally(() => setCarregando(false));
  }, []);

  useEffect(() => {
    const aoExpirar = () => setUsuario(null);
    window.addEventListener(EVENTO_SESSAO_EXPIRADA, aoExpirar);
    return () => window.removeEventListener(EVENTO_SESSAO_EXPIRADA, aoExpirar);
  }, []);

  const entrar = useCallback(async (login, senha) => {
    const resposta = await apiEntrar(login, senha);
    setToken(resposta.access_token);
    lembrarUsuario(resposta.usuario);
    setUsuario(resposta.usuario);
    return resposta.usuario;
  }, []);

  const sair = useCallback(() => {
    setToken(null);
    setUsuario(null);
  }, []);

  const valor = useMemo(() => ({ usuario, carregando, entrar, sair }), [usuario, carregando, entrar, sair]);
  return <SessaoContext.Provider value={valor}>{children}</SessaoContext.Provider>;
}
