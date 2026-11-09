import { useEffect, useState } from "react";
import { getPainel } from "../api.js";
import Card from "../components/ui/Card.jsx";
import Tag from "../components/ui/Tag.jsx";

const ESTILO = {
  livre: { background: "var(--leito-livre-bg)", border: "1px dashed var(--leito-livre-borda)" },
  ocupado: { background: "#fff", border: "1px solid var(--leito-ocupado-borda)" },
  limpeza: { background: "var(--leito-limpeza-bg)", border: "1px solid var(--leito-limpeza-borda)" },
  indisponivel: { background: "var(--leito-indisp-bg)", border: "1px solid #aab4b1" },
};
const ROTULO = { livre: "Livre", limpeza: "Em limpeza", indisponivel: "Indisponível" };
const TOM = { gestante: "info", puerpera: "roxo", abortamento: "aviso" };

export default function Painel() {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(false);

  useEffect(() => {
    getPainel().then(setDados).catch(() => setErro(true));
  }, []);

  if (erro) return <p>Não foi possível carregar o painel. A API está rodando?</p>;
  if (!dados) return <p>Carregando...</p>;

  const { ocupacao, sem_leito, enfermarias, fila } = dados;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
        <Card titulo="Ocupação de leitos">
          <strong style={{ fontSize: 32 }}>{ocupacao.ocupados}/{ocupacao.total}</strong> {ocupacao.percentual}%
        </Card>
        <Card titulo="Pacientes sem leito">
          <strong style={{ fontSize: 32 }}>{sem_leito}</strong>
        </Card>
        <Card titulo="Aguardando alocação">
          <strong style={{ fontSize: 32 }}>{fila.length}</strong>
        </Card>
      </div>

      <Card titulo="Enfermarias">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 12 }}>
          {enfermarias.map((enf) => (
            <div key={enf.numero}>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Enfermaria {enf.numero}</div>
              {enf.leitos.map((l) => (
                <div key={l.codigo} style={{ ...ESTILO[l.situacao], borderRadius: 10, padding: 10, marginBottom: 8, minHeight: 64 }}>
                  <div style={{ fontSize: 12 }}>{l.codigo}</div>
                  {l.paciente ? (
                    <>
                      <div style={{ fontWeight: 700 }}>{l.paciente.nome}</div>
                      <Tag tom={TOM[l.paciente.perfil]}>{l.paciente.perfil}</Tag>
                    </>
                  ) : (
                    <div style={{ fontWeight: 600 }}>{ROTULO[l.situacao]}</div>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
      </Card>

      <Card titulo="Fila de espera">
        {fila.map((p) => (
          <div key={p.nome} style={{ padding: "6px 0" }}>
            <strong>{p.nome}</strong> <Tag tom={TOM[p.perfil]}>{p.perfil}</Tag> · {p.espera_min == null ? "hora de entrada não informada" : `${p.espera_min} min de espera`}
          </div>
        ))}
      </Card>
    </div>
  );
}