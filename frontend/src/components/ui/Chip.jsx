export default function Chip({ selecionado = false, pequeno = false, className = "", children, ...resto }) {
  const classes = ["chip", pequeno ? "chip-sm" : "", className].filter(Boolean).join(" ");
  return (
    <button type="button" className={classes} aria-pressed={selecionado} {...resto}>
      {children}
    </button>
  );
}
