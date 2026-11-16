import { useEffect, useState } from "react";
import { getPainel } from "../api.js";
import Card from "../components/ui/Card.jsx";
import Chip from "../components/ui/Chip.jsx";
import Tag from "../components/ui/Tag.jsx";
import "./painel.css";

// perfil -> cor da etiqueta (o tom "rosa" precisa existir no ui.css)
const TOM_PERFIL = { gestante: "rosa", puerpera: "roxo", abortamento: "aviso" };
const NOME_PERFIL = { gestante: "Gestante", puerpera: "Puérpera", abortamento: "Abortamento" };
const TOM_PRIORIDADE = { Alta: "alerta", Média: "aviso", Normal: "neutro" };
const ROTULO_ESTADO = { livre: "Livre", limpeza: "Em limpeza", indisponivel: "Indisponível" };

const FILTROS = [
  ["todos", "Todos"],
  ["livre", "Livres"],
  ["ocupado", "Ocupados"],
  ["limpeza", "Em limpeza"],
  ["gestante", "Gestante"],
  ["puerpera", "Puérpera"],
  ["abortamento", "Abortamento"],
];

function formatarEspera(min) {
  if (min == null) return "hora de entrada não informada";
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  return `${h}h${String(min % 60).padStart(2, "0")}`;
}

function Etiquetas({ paciente, limite }) {
  return (
    <span className="tags">
      <Tag tom={TOM_PERFIL[paciente.perfil] || "neutro"}>{NOME_PERFIL[paciente.perfil] || paciente.perfil}</Tag>
      {paciente.tags.slice(0, limite).map((t) => (
        <Tag key={t.txt} tom={t.tom}>{t.txt}</Tag>
      ))}
    </span>
  );
}

function Kpi({ rotulo, destaque, children, nota }) {
  return (
    <div className={destaque ? "kpi-alerta" : undefined}>
      <Card>
        <div className="kpi">
          <div className="kpi-rotulo">{rotulo}</div>
          {children}
          {nota && <div className="kpi-nota">{nota}</div>}
        </div>
      </Card>
    </div>
  );
}

function Leito({ leito, apagado }) {
  const { situacao, paciente } = leito;
  const classe = `leito ${situacao} ${apagado ? "apagado" : ""}`;
  return (
    <div className={classe}>
      <span className="leito-rotulo">Leito {leito.letra}</span>
      {paciente ? (
        <>
          <span className="leito-nome">{paciente.nome}</span>
          <Etiquetas paciente={paciente} limite={2} />
        </>
      ) : (
        <span className="leito-estado">{ROTULO_ESTADO[situacao]}</span>
      )}
    </div>
  );
}

export default function Painel() {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(false);
  const [filtro, setFiltro] = useState("todos");

  useEffect(() => {
    getPainel().then(setDados).catch(() => setErro(true));
  }, []);

  if (erro) return <p>Não foi possível carregar o painel. A API está rodando?</p>;
  if (!dados) return <p>Carregando...</p>;

  const { ocupacao, sem_leito, aguardando, salas, pos_parto, enfermarias, fila, macas } = dados;

  // um leito fica "apagado" quando não combina com o filtro escolhido
  const combina = (leito) =>
    filtro === "todos" ||
    filtro === leito.situacao ||
    (leito.paciente && filtro === leito.paciente.perfil);

  return (
    <div className="painel">
      {ocupacao.alerta && (
        <div className="painel-alerta" role="alert">
          <span>
            Alerta de lotação: {ocupacao.ocupados}/{ocupacao.total} leitos ocupados ({ocupacao.percentual}%),
            acima do limite de {ocupacao.limite}%.
          </span>
          <span>
            {sem_leito} paciente(s) sem leito
            {aguardando ? ` e ${aguardando} aguardando alocação` : ""}.
          </span>
        </div>
      )}

      {/* indicadores */}
      <section className="kpis" aria-label="Indicadores">
        <Kpi
          rotulo="Ocupação de leitos"
          destaque={ocupacao.alerta}
          nota={`${ocupacao.total} leitos disponíveis · ${ocupacao.indisponiveis} indisponível(is)`}
        >
          <div className="kpi-valor">
            {ocupacao.ocupados}/{ocupacao.total} <small>{ocupacao.percentual}%</small>
          </div>
          <div className="barra"><div style={{ width: `${Math.min(ocupacao.percentual, 100)}%` }} /></div>
        </Kpi>
        <Kpi rotulo="Pacientes sem leito" nota={`Em macas · indicador de sobrecarga (+${aguardando} aguardando alocação)`}>
          <div className="kpi-valor">{sem_leito}</div>
        </Kpi>
        <Kpi rotulo="Salas em uso" nota="Nº de salas de parto a confirmar">
          <div className="kpi-valor menor">
            Parto {salas.parto_em_uso}/{salas.parto_total}<br />
            Cirurgia {salas.cirurgia_em_uso}/{salas.cirurgia_total}
          </div>
        </Kpi>
        <Kpi rotulo="Atenção pós-parto" nota={`Acima de 24h · ${pos_parto.perto_48h} perto de 48h · a decisão é da equipe`}>
          <div className="kpi-valor">{pos_parto.acima_24h}</div>
        </Kpi>
      </section>

      {/* filtros */}
      <section className="filtros" aria-label="Filtros">
        <span className="rotulo">Filtrar</span>
        {FILTROS.map(([valor, rotulo]) => (
          <Chip key={valor} selecionado={filtro === valor} onClick={() => setFiltro(valor)}>
            {rotulo}
          </Chip>
        ))}
      </section>

      <div className="painel-colunas">
        {/* fila */}
        <div className="col-fila">
          <Card>
            <div className="titulo-linha">
              <h2>Fila de espera por leito</h2>
              <span className="nota">ordenada por prioridade</span>
            </div>
            <p className="nota" style={{ marginTop: 0 }}>
              Prioridade combina tempo de espera, bolsa rota, comorbidade e parto em curso. Apenas apoio à decisão.
            </p>
            <div className="pilha">
              {fila.length === 0 && <div className="vazio">Ninguém aguardando alocação.</div>}
              {fila.map((p) => (
                <div className="fila-item" key={p.id}>
                  <div className="fila-topo">
                    <span className="fila-nome">{p.nome}</span>
                    <Tag tom={TOM_PRIORIDADE[p.prioridade]}>Prioridade {p.prioridade}</Tag>
                  </div>
                  <div className="fila-meta">
                    {p.gpa} · IG {p.ig}{p.diagnostico ? ` · ${p.diagnostico}` : ""}
                  </div>
                  <Etiquetas paciente={p} limite={3} />
                  <div className="fila-espera">
                    <b>{formatarEspera(p.espera_min)}</b>{p.espera_min != null && " de espera"}
                    <br /><span>{p.onde}</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* enfermarias */}
        <div className="col-mapa">
          <Card>
            <div className="titulo-linha">
              <h2>Enfermarias</h2>
              <div className="legenda">
                <span><i className="lg-livre" />Livre</span>
                <span><i className="lg-ocupado" />Ocupado</span>
                <span><i className="lg-limpeza" />Em limpeza</span>
                <span><i className="lg-indisp" />Indisponível</span>
              </div>
            </div>
            <div className="enfs">
              {enfermarias.map((enf) => (
                <div className="enf" key={enf.numero}>
                  <div className="enf-nome">Enfermaria {enf.numero}</div>
                  {enf.leitos.map((l) => (
                    <Leito key={l.codigo} leito={l} apagado={!combina(l)} />
                  ))}
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* salas e macas */}
        <div className="col-salas">
          <Card>
            <div className="titulo-linha"><h2>Salas</h2></div>
            <div className="pilha" style={{ gap: 10 }}>
              {[...dados.salas_parto, ...dados.salas_cirurgia].map((s) => (
                <div key={s.codigo} className={`sala ${s.paciente ? "ocupada" : "livre"}`}>
                  <span className="sala-nome">{s.nome}</span>
                  {s.paciente ? <b>{s.paciente.nome}</b> : <b>Livre</b>}
                </div>
              ))}
              <p className="subtitulo">Apoio</p>
              <div className="tags">
                {dados.apoio.map((a) => (
                  <Tag key={a.codigo} tom={a.paciente ? "info" : "neutro"}>
                    {a.nome}: {a.paciente ? a.paciente.nome : "livre"}
                  </Tag>
                ))}
              </div>
            </div>
          </Card>

          <Card>
            <div className="titulo-linha">
              <h2>Macas e corredores</h2>
              <Tag tom="alerta">{sem_leito} sem leito</Tag>
            </div>
            <div className="pilha" style={{ gap: 10 }}>
              {macas.length === 0 && <div className="vazio">Nenhuma paciente em maca.</div>}
              {macas.map((m) => (
                <div className="maca" key={m.nome}>
                  <b>{m.nome}</b>
                  <span>{m.local}</span>
                  <small>{m.espera_min == null ? "hora de entrada não informada" : `em maca há ${formatarEspera(m.espera_min)}`}</small>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}