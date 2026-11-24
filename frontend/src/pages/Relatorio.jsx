
import { useEffect, useState } from "react";

import {
  getRelatorioMensal,
  exportarRelatorioPDF,
} from "../api.js";

import "./relatorio.css";


const MESES = [
  "Janeiro",
  "Fevereiro",
  "Março",
  "Abril",
  "Maio",
  "Junho",
  "Julho",
  "Agosto",
  "Setembro",
  "Outubro",
  "Novembro",
  "Dezembro",
];


function formatarMes(mes) {
  const [ano, numero] = mes.split("-");

  return `${MESES[Number(numero) - 1]} / ${ano}`;
}


function formatarHoras(valor) {
  if (valor == null) return "—";

  const horas = Math.floor(valor);
  const minutos = Math.round((valor - horas) * 60);

  return `${horas}h${String(minutos).padStart(2, "0")}`;
}


function formatarEspera(minutos) {
  if (minutos == null) return "—";

  const horas = Math.floor(minutos / 60);
  const restante = minutos % 60;

  return horas > 0
    ? `${horas}h${String(restante).padStart(2, "0")}`
    : `${restante} min`;
}


function Indicador({ titulo, itens }) {
  return (
    <section className="relatorio-card">
      <h2>{titulo}</h2>

      <div className="relatorio-indicadores">
        {itens.map((item) => (
          <div className="relatorio-indicador" key={item.label}>
            <strong>{item.valor ?? "—"}</strong>
            <span>{item.label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}


function gerarPrevia(dados) {
  return [
    ["atendidas", dados.atendimentos.atendidas],
    ["internadas atualmente", dados.atendimentos.internadas],
    ["altas", dados.saidas.altas],
    ["transferencias", dados.saidas.transferencias],
    ["alojamento", dados.saidas.alojamento],
    ["nascimentos", dados.nascimentos.total],
    ["parto_normal", dados.nascimentos.normal],
    ["cesareas", dados.nascimentos.cesarea],
    ["forceps", dados.nascimentos.forceps],
    ["obitos_neonatais", dados.obitos.neonatais],
    ["obitos_maternos", "Não disponível"],
    ["permanencia_media_horas", dados.permanencia.media_horas],
    ["ocupacao_atual_percentual", dados.permanencia.ocupacao_atual],
    ["pacientes_em_maca", dados.macas.atendidas],
    ["espera_media_minutos", dados.macas.espera_media_minutos],
  ];
}


function gerarConteudoCSV(dados) {
  const linhas = [
    ["métrica", "valor"],
    ...gerarPrevia(dados),
  ];

  const escapar = (valor) => {
    const texto = String(valor ?? "Não disponível");

    if (/[;"\r\n]/.test(texto)) {
      return `"${texto.replace(/"/g, '""')}"`;
    }

    return texto;
  };

  return "\uFEFF" +
    linhas
      .map((linha) => linha.map(escapar).join(";"))
      .join("\r\n");
}


function baixarCSV(dados, mes) {
  const conteudo = gerarConteudoCSV(dados);

  const arquivo = new Blob(
    [conteudo],
    { type: "text/csv;charset=utf-8;" }
  );

  const url = window.URL.createObjectURL(arquivo);
  const link = document.createElement("a");

  link.href = url;
  link.download = `relatorio-${mes}.csv`;

  document.body.appendChild(link);
  link.click();
  link.remove();

  window.URL.revokeObjectURL(url);
}


export default function Relatorio() {
  const hoje = new Date();

  const [mes, setMes] = useState(
    `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, "0")}`
  );

  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [exportando, setExportando] = useState("");

  useEffect(() => {
    let ativo = true;

    getRelatorioMensal(mes)
      .then((resultado) => {
        if (ativo) setDados(resultado);
      })
      .catch((erroApi) => {
        if (ativo) setErro(erroApi.message);
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });

    return () => {
      ativo = false;
    };
  }, [mes]);

  // Limpa a tela ao trocar de mês; o efeito acima só busca os dados novos.
  function trocarMes(novoMes) {
    setMes(novoMes);
    setCarregando(true);
    setErro("");
    setDados(null);
  }


  
  async function exportar(tipo) {
    setExportando(tipo);
    setErro("");

    try {
      if (tipo === "pdf") {
        await exportarRelatorioPDF(mes);
      } else {
        // Utiliza o mesmo snapshot carregado na tela.
        baixarCSV(dados, mes);
      }
    } catch (erroApi) {
      setErro(erroApi.message);
    } finally {
      setExportando("");
    }
  }

  return (
    <div className="relatorio">

      <header className="relatorio-topo">

        <div>
          <h1>Relatório mensal</h1>

          <p>
            Prévia das métricas geradas a partir dos registros do Gestar.
            Dados consolidados do período selecionado.
          </p>
        </div>

        <div className="relatorio-acoes">

          <label className="relatorio-seletor">
            <span>Mês</span>

            <input
              type="month"
              value={mes}
              onChange={(evento) => trocarMes(evento.target.value)}
            />
          </label>

          <button
            className="relatorio-botao"
            type="button"
            onClick={() => exportar("pdf")}
            disabled={!dados || carregando || !!exportando}
          >
            {exportando === "pdf"
              ? "Gerando PDF..."
              : "Exportar PDF resumido"}
          </button>

          <button
            className="relatorio-botao relatorio-botao-escuro"
            type="button"
            onClick={() => exportar("csv")}
            disabled={!dados || carregando || !!exportando}
          >
            {exportando === "csv"
              ? "Exportando..."
              : "Exportar CSV"}
          </button>

        </div>

      </header>


      {erro && (
        <div className="relatorio-erro" role="alert">
          {erro}
        </div>
      )}


      {carregando && (
        <div className="relatorio-estado">
          Carregando relatório...
        </div>
      )}


      {!carregando && dados && (

        <>

          <div className="relatorio-grade">

            <Indicador
              titulo="Atendimentos"
              itens={[
                {
                  label: "atendidas",
                  valor: dados.atendimentos.atendidas,
                },
                {
                  label: "internadas atualmente",
                  valor: dados.atendimentos.internadas,
                },
              ]}
            />


            <Indicador
              titulo="Desfechos de saída"
              itens={[
                {
                  label: "altas",
                  valor: dados.saidas.altas,
                },
                {
                  label: "transferências",
                  valor: dados.saidas.transferencias,
                },
                {
                  label: "alojamento",
                  valor: dados.saidas.alojamento,
                },
              ]}
            />


            <Indicador
              titulo="Nascimentos"
              itens={[
                {
                  label: "total",
                  valor: dados.nascimentos.total,
                },
                {
                  label: "parto vaginal",
                  valor: dados.nascimentos.normal,
                },
                {
                  label: "cesárea",
                  valor: dados.nascimentos.cesarea,
                },
              ]}
            />


            <Indicador
              titulo="Óbitos"
              itens={[
                {
                  label: "recém-nascidos",
                  valor: dados.obitos.neonatais,
                },
                {
                  label: "maternos",
                  valor: "N/D",
                },
              ]}
            />


            <Indicador
              titulo="Permanência e ocupação"
              itens={[
                {
                  label: "permanência média (h)",
                  valor: formatarHoras(
                    dados.permanencia.media_horas
                  ),
                },
                {
                  label: "ocupação atual",
                  valor: `${dados.permanencia.ocupacao_atual}%`,
                },
              ]}
            />


            <Indicador
              titulo="Pacientes em maca"
              itens={[
                {
                  label: "atendidas em maca",
                  valor: dados.macas.atendidas,
                },
                {
                  label: "espera média",
                  valor: formatarEspera(
                    dados.macas.espera_media_minutos
                  ),
                },
              ]}
            />

          </div>


          <section className="relatorio-csv">

            <h2>Prévia do arquivo CSV</h2>

            <div className="relatorio-csv-conteudo">

              <div className="relatorio-csv-linha">
                métrica;valor
              </div>

              {gerarPrevia(dados).map(([metrica, valor]) => (

                <div
                  className="relatorio-csv-linha"
                  key={metrica}
                >
                  {metrica};{valor ?? "Não disponível"}
                </div>

              ))}

            </div>

          </section>


          <p className="relatorio-rodape">
            Período: {formatarMes(mes)} ·
            Indicadores calculados com base nos registros disponíveis.
          </p>

        </>

      )}

    </div>
  );
}
