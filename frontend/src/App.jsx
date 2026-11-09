import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import Login from "./pages/Login.jsx";
import Painel from "./pages/Painel.jsx";
import Pendencias from "./pages/Pendencias.jsx";
import Relatorio from "./pages/Relatorio.jsx";
import Integracao from "./pages/Integracao.jsx";

import Componentes from "./pages/Componentes.jsx";


export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Painel />} />
        <Route path="/pendencias" element={<Pendencias />} />
        <Route path="/relatorio" element={<Relatorio />} />
        <Route path="/integracao" element={<Integracao />} />
        <Route path="/componentes" element={<Componentes />} />
      </Route>
    </Routes>
  );
}