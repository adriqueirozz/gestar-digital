import { Navigate, useLocation } from "react-router-dom";
import { useSessao } from "./useSessao.js";

// Sem usuário logado, manda para o login e volta para a mesma tela depois de entrar.
export default function RotaProtegida({ children }) {
  const { usuario, carregando } = useSessao();
  const local = useLocation();

  if (carregando) return <div className="tela-carregando">Carregando…</div>;
  if (!usuario) return <Navigate to="/login" replace state={{ de: local.pathname }} />;
  return children;
}
