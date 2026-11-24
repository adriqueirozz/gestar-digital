import { fmtDataHora, fmtRestante, maiuscula } from "../pages/pendenciasUtil.js";
import Botao from "./ui/Botao.jsx";

// Uma pendência: o que fazer, prazo (colorido conforme a situação) e o botão Concluir.
// A cor da borda e do prazo já diz se está em dia, perto de vencer ou vencida.
export default function ItemPendencia({ pendencia: p, podeEditar, ocupado, onConcluir }) {
  const concluida = p.status === "concluida";
  return (
    <li className={`pend-item ${p.status}`}>
      <span className="pend-texto">
        {p.descricao}
        <small>
          {concluida
            ? `Concluída às ${fmtDataHora(p.concluida_em)}${p.concluida_por ? ` por ${p.concluida_por}` : ""}`
            : `Prazo de ${p.prazo_horas}h${p.criada_por ? ` · criada por ${p.criada_por}` : ""}`}
        </small>
      </span>
      <span className="pend-acoes">
        <span className={`pend-prazo ${p.status}`}>{concluida ? "Concluída" : maiuscula(fmtRestante(p.restante_min))}</span>
        {podeEditar && !concluida && (
          <span className="no-print">
            <Botao pequeno disabled={ocupado} onClick={onConcluir}>Concluir</Botao>
          </span>
        )}
      </span>
    </li>
  );
}
