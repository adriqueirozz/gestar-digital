import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { enviarPlanilha, getUltimaImportacao } from "../api.js";
import Botao from "../components/ui/Botao.jsx";
import Card from "../components/ui/Card.jsx";
import Tag from "../components/ui/Tag.jsx";

const ROTULO = {
  prontuario_invalido: "Prontuário inválido",
  prontuario_duplicado: "Prontuário duplicado",
  campo_vazio: "Campo vazio",
  formato_invalido: "Formato inválido",
  leito_nao_reconhecido: "Leito não reconhecido",
  leito_inexistente: "Leito inexistente",
  leito_indisponivel: "Leito indisponível",
  leito_ocupado: "Leito ocupado",
  divergencia: "Divergência",
};
const TOM = {
  prontuario_invalido: "alerta",
  prontuario_duplicado: "alerta",
  leito_ocupado: "alerta",
  leito_inexistente: "alerta",
  leito_nao_reconhecido: "alerta",
};

function Numero({ rotulo, valor }) {
  return (
    <Card>
      <div style={{ fontSize: 12, fontWeight: 600, color: "var(--cor-texto-suave)" }}>{rotulo}</div>
      <strong style={{ fontSize: 28 }}>{valor}</strong>
    </Card>
  );
}

export default function Integracao() {
  const [arquivo, setArquivo] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState("");

  // mostra a última importação ao abrir a tela
  useEffect(() => {
    getUltimaImportacao().then(setResultado).catch(() => {});
  }, []);

  async function enviar() {
    setEnviando(true);
    setErro("");
    try {
      setResultado(await enviarPlanilha(arquivo));
    } catch (e) {
      setErro(e.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <h1 style={{ margin: 0 }}>Integração com a planilha</h1>

      <Card titulo="Importar planilha (CSV ou Excel)">
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
          <input
            type="file"
            accept=".csv,.xlsx"
            aria-label="Arquivo da planilha"
            onChange={(e) => setArquivo(e.target.files[0] || null)}
          />
          <Botao variante="primario" disabled={!arquivo || enviando} onClick={enviar}>
            {enviando ? "Importando..." : "Importar"}
          </Botao>
        </div>
        {erro && <p role="alert" style={{ color: "var(--alerta-tx)" }}>{erro}</p>}
        <p style={{ fontSize: 13, color: "var(--cor-texto-suave)", marginBottom: 0 }}>
          Colunas esperadas: leito, código do prontuário, data de entrada no COB, nome completo, GPA, IG,
          diagnóstico e OBS. Linhas com erro de digitação entram na fila e aparecem na conferência abaixo.
        </p>
      </Card>

      {resultado && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12 }}>
            <Numero rotulo="Linhas lidas" valor={resultado.linhas_lidas} />
            {resultado.novas !== undefined && (
              <>
                <Numero rotulo="Pacientes novas" valor={resultado.novas} />
                <Numero rotulo="Alocadas em leito" valor={resultado.alocadas} />
                <Numero rotulo="Na fila" valor={resultado.na_fila} />
              </>
            )}
            <Numero rotulo="Linhas com problema" valor={resultado.linhas_com_problema} />
          </div>

          <Card titulo={`Conferência (${resultado.arquivo})`}>
            {resultado.problemas.length === 0 ? (
              <p>Nenhum problema encontrado.</p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 520 }}>
                  <thead>
                    <tr style={{ textAlign: "left", fontSize: 12 }}>
                      <th style={{ padding: 8 }}>Linha</th>
                      <th style={{ padding: 8 }}>Valor na planilha</th>
                      <th style={{ padding: 8 }}>Problema</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resultado.problemas.map((p, i) => (
                      <tr key={i} style={{ borderTop: "1px solid var(--cor-borda)", verticalAlign: "top" }}>
                        <td style={{ padding: 8 }}>{p.linha}</td>
                        <td style={{ padding: 8 }}>{p.valor || "—"}</td>
                        <td style={{ padding: 8 }}>
                          <Tag tom={TOM[p.tipo] || "aviso"}>{ROTULO[p.tipo] || p.tipo}</Tag>
                          <div style={{ fontSize: 13, color: "var(--cor-texto-suave)", marginTop: 4 }}>{p.detalhe}</div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <Link to="/">Ver o painel atualizado →</Link>
        </>
      )}
    </div>
  );
}