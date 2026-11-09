const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function getHealth() {
  const resposta = await fetch(`${API_URL}/health`);
  if (!resposta.ok) throw new Error("API indisponível");
  return resposta.json();
}