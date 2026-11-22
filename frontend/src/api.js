import { EVENTO_SESSAO_EXPIRADA, getToken, setToken } from "./auth/sessao.js";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Toda chamada à API leva o token do usuário logado (G-17).
// Se a API responder 401 (token vencido ou inválido), a sessão é encerrada e o app volta ao login.
async function requisitar(caminho, opcoes = {}) {
  const token = getToken();
  const headers = { ...(opcoes.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const resposta = await fetch(`${API_URL}${caminho}`, { ...opcoes, headers });
  if (resposta.status === 401 && token) {
    setToken(null);
    window.dispatchEvent(new Event(EVENTO_SESSAO_EXPIRADA));
  }
  return resposta;
}

export async function getHealth() {
  const resposta = await fetch(`${API_URL}/health`);
  if (!resposta.ok) throw new Error("API indisponível");
  return resposta.json();
}

export async function getPainel() {
  const resposta = await requisitar("/api/painel");
  if (!resposta.ok) throw new Error("Erro ao carregar o painel");
  return resposta.json();
}

export async function enviarPlanilha(arquivo) {
  const dados = new FormData();
  dados.append("arquivo", arquivo);
  const resposta = await requisitar("/api/importacoes", { method: "POST", body: dados });
  const corpo = await resposta.json();
  if (!resposta.ok) throw new Error(corpo.detail || "Erro ao importar");
  return corpo;
}

export async function getUltimaImportacao() {
  const resposta = await requisitar("/api/importacoes/ultima");
  if (!resposta.ok) throw new Error("Erro ao carregar a importação");
  return resposta.json();
}

async function chamar(metodo, caminho, corpo) {
  const resposta = await requisitar(caminho, {
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

// ---- autenticação (G-16/G-17) ----
// O login não passa por requisitar(): uma senha errada na troca de usuário não deve derrubar quem já está logado.
export async function entrar(login, senha) {
  let resposta;
  try {
    resposta = await fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ username: login, password: senha }),
    });
  } catch {
    throw new Error("Não foi possível falar com a API. Ela está rodando?");
  }
  const dados = await resposta.json().catch(() => null);
  if (!resposta.ok) throw new Error((dados && dados.detail) || "Não foi possível entrar.");
  return dados; // { access_token, token_type, usuario }
}


export async function getRelatorioMensal(mes) {
  const resposta = await requisitar(
    `/api/relatorios/mensal?mes=${encodeURIComponent(mes)}`
  );

  if (!resposta.ok) {
    const erro = await resposta.json().catch(() => null);
    throw new Error(erro?.detail || "Erro ao carregar relatório.");
  }

  return resposta.json();
}

async function baixarRelatorio(tipo, mes) {
  const resposta = await requisitar(
    `/api/relatorios/mensal/${tipo}?mes=${encodeURIComponent(mes)}`
  );

  if (!resposta.ok) {
    const erro = await resposta.json().catch(() => null);
    throw new Error(erro?.detail || "Erro ao exportar relatório.");
  }

  const arquivo = await resposta.blob();
  const url = window.URL.createObjectURL(arquivo);
  const link = document.createElement("a");

  link.href = url;
  link.download = `relatorio-${mes}.${tipo}`;

  document.body.appendChild(link);
  link.click();
  link.remove();

  window.URL.revokeObjectURL(url);
}

export const getUsuarioLogado = () => chamar("GET", "/api/auth/me");

export const getPaciente = (id) => chamar("GET", `/api/pacientes/${id}`);
export const alocarPaciente = (id, dados) => chamar("POST", `/api/pacientes/${id}/alocar`, dados);
export const registrarParto = (id, dados) => chamar("POST", `/api/pacientes/${id}/parto`, dados);
export const registrarSaida = (id, dados) => chamar("POST", `/api/pacientes/${id}/saida`, dados);
export const atualizarPaciente = (id, dados) => chamar("PATCH", `/api/pacientes/${id}/sinalizacoes`, dados);
export const getDestinos = () => chamar("GET", "/api/locais/destinos");
export const mudarSituacaoLeito = (codigo, situacao) => chamar("POST", `/api/locais/${codigo}/situacao`, { situacao });
export const editarMaca = (codigo, descricao) => chamar("PATCH", `/api/locais/${codigo}`, { descricao });

export const getPlantao = () => chamar("GET", "/api/pendencias/plantao");
export const criarPendencia = (dados) => chamar("POST", "/api/pendencias", dados);
export const concluirPendencia = (id) => chamar("POST", `/api/pendencias/${id}/concluir`);

export const exportarRelatorioPDF = (mes) => baixarRelatorio("pdf", mes);
export const exportarRelatorioCSV = (mes) => baixarRelatorio("csv", mes);
