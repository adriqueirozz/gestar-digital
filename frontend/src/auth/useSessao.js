import { createContext, useContext } from "react";

export const SessaoContext = createContext(null);

/** { usuario, carregando, entrar(login, senha), sair() } */
export function useSessao() {
  return useContext(SessaoContext);
}

/** true para Enfermagem e Médico; false para Gestão, que é somente leitura (G-19). */
export function usePodeEditar() {
  const { usuario } = useContext(SessaoContext);
  return Boolean(usuario && usuario.pode_editar);
}
