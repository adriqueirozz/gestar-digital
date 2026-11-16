export default function Chip({ selecionado = false, children, ...resto }) {
  return (
    <button type="button" className="chip" aria-pressed={selecionado} {...resto}>
      {children}
    </button>
  );
}