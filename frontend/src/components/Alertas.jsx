import Tag from "./ui/Tag.jsx";

// Sinalizações da paciente. Com `soAtencao`, mostra só as de atenção (vermelhas e amarelas):
// é o que precisa saltar aos olhos no painel. As demais continuam na ficha e na passagem de plantão.
export default function Alertas({ tags, soAtencao = false, limite }) {
  let lista = soAtencao ? tags.filter((t) => t.tom === "alerta" || t.tom === "aviso") : tags;
  if (limite) lista = lista.slice(0, limite);
  if (lista.length === 0) return null;
  return (
    <span className="tags">
      {lista.map((t) => (
        <Tag key={t.txt} tom={t.tom}>{t.txt}</Tag>
      ))}
    </span>
  );
}
