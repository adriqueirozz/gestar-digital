export const rotuloStatus = {
  em_dia: "Em dia",
  proxima: "Próxima do vencimento",
  vencida: "Vencida",
  concluida: "Concluída",
};

export const tomStatus = { em_dia: "ok", proxima: "aviso", vencida: "alerta", concluida: "neutro" };

function duracao(min) {
  if (min < 60) return `${min} min`;
  return `${Math.floor(min / 60)}h${String(min % 60).padStart(2, "0")}`;
}

// restante_min negativo = já venceu
export function fmtRestante(min) {
  return min < 0 ? `vencida há ${duracao(-min)}` : `vence em ${duracao(min)}`;
}
export const fmtDataHora = (iso) =>
  iso
    ? new Date(iso).toLocaleString("pt-BR", { timeZone: "America/Recife", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })
    : "—";

// "vence em 2h00" -> "Vence em 2h00"
export const maiuscula = (texto) => (texto ? texto[0].toUpperCase() + texto.slice(1) : texto);
