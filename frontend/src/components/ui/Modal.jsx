import { useEffect } from "react";
import Botao from "./Botao.jsx";

export default function Modal({ aberto, titulo, subtitulo, onFechar, largura = 620, children }) {
  useEffect(() => {
    if (!aberto) return;
    const aoTeclar = (e) => e.key === "Escape" && onFechar();
    document.addEventListener("keydown", aoTeclar);
    return () => document.removeEventListener("keydown", aoTeclar);
  }, [aberto, onFechar]);

  if (!aberto) return null;

  return (
    <div className="modal-fundo" onClick={onFechar}>
      <div
        className="modal"
        style={{ maxWidth: largura }}
        role="dialog"
        aria-modal="true"
        aria-label={titulo}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-topo">
          <div>
            <h2 className="modal-titulo">{titulo}</h2>
            {subtitulo && <div className="modal-sub">{subtitulo}</div>}
          </div>
          <Botao pequeno onClick={onFechar}>Fechar</Botao>
        </div>
        <div className="modal-corpo">{children}</div>
      </div>
    </div>
  );
}