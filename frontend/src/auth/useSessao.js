import { createContext, useContext } from "react";

export const SessaoContext = createContext(null);

/** { usuario, carregando, entrar(login, senha), sair() } */
export function useSessao() {
  return useContext(SessaoContext);
}
