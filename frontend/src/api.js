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

async function chamar(metodo, caminho, corpo) {
  const resposta = await fetch(`${API_URL}${caminho}`, {
    method: metodo,
    headers: corpo ? { "Content-Type": "application/json" } : undefined,
    body: corpo ? JSON.stringify(corpo) : undefined,
  });
  let dados = null;
  try {
    dados = await resposta.json();
  } catch {
    /* resposta sem corpo */
  }
  if (!resposta.ok) {
    const detalhe = dados && dados.detail;
    throw new Error(typeof detalhe === "string" ? detalhe : "Não foi possível concluir a ação.");
  }
  return dados;
}

export const getPaciente = (id) => chamar("GET", `/api/pacientes/${id}`);
export const alocarPaciente = (id, dados) => chamar("POST", `/api/pacientes/${id}/alocar`, dados);
export const registrarParto = (id, dados) => chamar("POST", `/api/pacientes/${id}/parto`, dados);
export const registrarSaida = (id, dados) => chamar("POST", `/api/pacientes/${id}/saida`, dados);
export const atualizarPaciente = (id, dados) => chamar("PATCH", `/api/pacientes/${id}/sinalizacoes`, dados);
export const getDestinos = () => chamar("GET", "/api/locais/destinos");
export const mudarSituacaoLeito = (codigo, situacao) => chamar("POST", `/api/locais/${codigo}/situacao`, { situacao });
export const editarMaca = (codigo, descricao) => chamar("PATCH", `/api/locais/${codigo}`, { descricao });