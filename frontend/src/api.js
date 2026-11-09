const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function getHealth() {
  const resposta = await fetch(`${API_URL}/health`);
  if (!resposta.ok) throw new Error("API indisponível");
  return resposta.json();
}

export async function getPainel() {
  const resposta = await fetch(`${API_URL}/api/painel`);
  if (!resposta.ok) throw new Error("Erro ao carregar o painel");
  return resposta.json();
}

export async function enviarPlanilha(arquivo) {
  const dados = new FormData();
  dados.append("arquivo", arquivo);
  const resposta = await fetch(`${API_URL}/api/importacoes`, { method: "POST", body: dados });
  const corpo = await resposta.json();
  if (!resposta.ok) throw new Error(corpo.detail || "Erro ao importar");
  return corpo;
}

export async function getUltimaImportacao() {
  const resposta = await fetch(`${API_URL}/api/importacoes/ultima`);
  if (!resposta.ok) throw new Error("Erro ao carregar a importação");
  return resposta.json();
}