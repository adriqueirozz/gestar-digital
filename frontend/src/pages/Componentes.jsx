import { useState } from "react";
import Botao from "../components/ui/Botao.jsx";
import Tag from "../components/ui/Tag.jsx";
import Chip from "../components/ui/Chip.jsx";
import Card from "../components/ui/Card.jsx";
import Modal from "../components/ui/Modal.jsx";

export default function Componentes() {
  const [filtro, setFiltro] = useState("Todos");
  const [aberto, setAberto] = useState(false);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <h1>Guia de estilo</h1>

      <Card titulo="Botões">
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Botao variante="primario">Alocar</Botao>
          <Botao>Registrar saída</Botao>
          <Botao pequeno>Concluir</Botao>
          <Botao disabled>Desabilitado</Botao>
        </div>
      </Card>

      <Card titulo="Tags">
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <Tag tom="info">Gestante</Tag>
          <Tag tom="roxo">Puérpera</Tag>
          <Tag tom="aviso">Abortamento</Tag>
          <Tag tom="alerta">Bolsa rota 19h · ATB</Tag>
          <Tag tom="ok">Em dia</Tag>
          <Tag>Reserva sang.</Tag>
        </div>
      </Card>

      <Card titulo="Chips (filtros)">
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {["Todos", "Livres", "Ocupados", "Em limpeza"].map((f) => (
            <Chip key={f} selecionado={filtro === f} onClick={() => setFiltro(f)}>{f}</Chip>
          ))}
        </div>
      </Card>

      <Card titulo="Modal">
        <Botao variante="primario" onClick={() => setAberto(true)}>Abrir modal</Botao>
      </Card>

      <Modal aberto={aberto} titulo="Alocar / mover" subtitulo="Paciente de exemplo" onFechar={() => setAberto(false)}>
        <p>Conteúdo do modal.</p>
        <Botao variante="primario" onClick={() => setAberto(false)}>Confirmar</Botao>
      </Modal>
    </div>
  );
}