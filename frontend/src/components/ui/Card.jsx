export default function Card({ titulo, children, ...resto }) {
  return (
    <div className="card" {...resto}>
      {titulo && <h2 className="card-titulo">{titulo}</h2>}
      {children}
    </div>
  );
}