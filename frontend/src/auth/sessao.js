// Guarda o token e a lista de usuários recentes deste computador (G-17).
// Nunca guarda senha. O localStorage pode estar bloqueado: toda leitura/escrita é protegida.

const CHAVE_TOKEN = "gestar.token";
const CHAVE_RECENTES = "gestar.recentes";
const MAX_RECENTES = 6;

export const EVENTO_SESSAO_EXPIRADA = "gestar:sessao-expirada";

export const NOME_PERFIL = { enfermagem: "Enfermagem", medico: "Médico", gestao: "Gestão" };

function ler(chave) {
  try {
    return localStorage.getItem(chave);
  } catch {
    return null;
  }
}

function gravar(chave, valor) {
  try {
    if (valor == null) localStorage.removeItem(chave);
    else localStorage.setItem(chave, valor);
  } catch {
    /* sem armazenamento: a sessão dura só enquanto a página estiver aberta */
  }
}

let tokenEmMemoria = ler(CHAVE_TOKEN);

export function getToken() {
  return tokenEmMemoria;
}

export function setToken(token) {
  tokenEmMemoria = token || null;
  gravar(CHAVE_TOKEN, tokenEmMemoria);
}

export function getRecentes() {
  try {
    const lista = JSON.parse(ler(CHAVE_RECENTES) || "[]");
    return Array.isArray(lista) ? lista : [];
  } catch {
    return [];
  }
}

export function lembrarUsuario({ login, nome, perfil }) {
  const lista = [{ login, nome, perfil }, ...getRecentes().filter((u) => u.login !== login)];
  gravar(CHAVE_RECENTES, JSON.stringify(lista.slice(0, MAX_RECENTES)));
}

export function esquecerUsuario(login) {
  gravar(CHAVE_RECENTES, JSON.stringify(getRecentes().filter((u) => u.login !== login)));
}
