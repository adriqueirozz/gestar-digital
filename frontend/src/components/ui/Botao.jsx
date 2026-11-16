export default function Botao({ variante = "secundario", pequeno = false, className = "", ...resto }) {
  const classes = ["btn", variante === "primario" ? "btn-primario" : "", pequeno ? "btn-sm" : "", className]
    .filter(Boolean)
    .join(" ");
  return <button type="button" className={classes} {...resto} />;
}