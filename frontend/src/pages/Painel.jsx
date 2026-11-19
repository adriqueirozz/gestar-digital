import { useEffect, useState } from "react";
import { getPainel } from "../api.js";
import Botao from "../components/ui/Botao.jsx";
import Card from "../components/ui/Card.jsx";
import Chip from "../components/ui/Chip.jsx";
import Tag from "../components/ui/Tag.jsx";
import { ModalAlocar, ModalLeito, ModalMaca, ModalPaciente } from "./ModaisPainel.jsx";
import "./painel.css";
import { Link } from "react-router-dom";
import { usePodeEditar } from "../auth/useSessao.js";

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

function Leito({ leito, apagado, onClick }) {
  const { situacao, paciente } = leito;
  return (
    <button type="button" className={`leito ${situacao} ${apagado ? "apagado" : ""}`} onClick={onClick}
      aria-label={paciente ? `Leito ${leito.letra}, ${paciente.nome}` : `Leito ${leito.letra}, ${ROTULO_ESTADO[situacao]}`}>
      <span className="leito-rotulo">Leito {leito.letra}</span>
      {paciente ? (
        <>
          <span className="leito-nome">{paciente.nome}</span>
          <Etiquetas paciente={paciente} limite={2} />
        </>
      ) : (
        <span className="leito-estado">{ROTULO_ESTADO[situacao]}</span>
      )}
    </button>
  );
}

export default function Painel() {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(false);
  const [filtro, setFiltro] = useState("todos");
  // modal aberto: null | {tipo: "paciente", id} | {tipo: "alocar", paciente} | {tipo: "leito", leito} | {tipo: "maca", maca}
  const [modal, setModal] = useState(null);
  const podeEditar = usePodeEditar();

  const recarregar = () => getPainel().then((d) => { setDados(d); setErro(false); }).catch(() => setErro(true));
  useEffect(() => { recarregar(); }, []);

  if (erro && !dados) return <p>Não foi possível carregar o painel. A API está rodando?</p>;
  if (!dados) return <p>Carregando...</p>;

  const { ocupacao, sem_leito, aguardando, salas, pos_parto, pendencias, enfermarias, fila, macas } = dados;
  const fechar = () => setModal(null);
  const abrirPaciente = (id) => setModal({ tipo: "paciente", id });

  const combina = (leito) =>
    filtro === "todos" || filtro === leito.situacao || (leito.paciente && filtro === leito.paciente.perfil);

  const aoClicarLeito = (l) => {
    if (l.paciente) abrirPaciente(l.paciente.id);
    else if (podeEditar) setModal({ tipo: "leito", leito: l }); // Gestão não muda o status do leito
  };

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

      <section className="kpis" aria-label="Indicadores">
        <Kpi rotulo="Ocupação de leitos" destaque={ocupacao.alerta}
          nota={`${ocupacao.total} leitos disponíveis · ${ocupacao.indisponiveis} indisponível(is)`}>
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
          <Link to="/pendencias" className="kpi-link">
          <Kpi rotulo="Pendências vencidas" destaque={pendencias.vencidas > 0}
            nota={`${pendencias.proximas} próximas do vencimento · ver passagem de plantão`}>
            <div className="kpi-valor">{pendencias.vencidas}</div>
          </Kpi>
        </Link>
        <Kpi rotulo="Atenção pós-parto" nota={`Acima de 24h · ${pos_parto.perto_48h} perto de 48h · a decisão é da equipe`}>
          <div className="kpi-valor">{pos_parto.acima_24h}</div>
        </Kpi>
      </section>

      <section className="filtros" aria-label="Filtros">
        <span className="rotulo">Filtrar</span>
        {FILTROS.map(([valor, rotulo]) => (
          <Chip key={valor} selecionado={filtro === valor} onClick={() => setFiltro(valor)}>{rotulo}</Chip>
        ))}
      </section>

      <div className="painel-colunas">
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
                    <button type="button" className="link fila-nome" onClick={() => abrirPaciente(p.id)}>{p.nome}</button>
                    <Tag tom={TOM_PRIORIDADE[p.prioridade]}>Prioridade {p.prioridade}</Tag>
                  </div>
                  <div className="fila-meta">
                    {p.gpa} · IG {p.ig}{p.diagnostico ? ` · ${p.diagnostico}` : ""}
                  </div>
                  <Etiquetas paciente={p} limite={3} />
                  <div className="fila-rodape">
                    <div className="fila-espera">
                      <b>{formatarEspera(p.espera_min)}</b>{p.espera_min != null && " de espera"}
                      <br /><span>{p.onde}</span>
                    </div>
                    {podeEditar && (
                      <Botao variante="primario" onClick={() => setModal({ tipo: "alocar", paciente: { id: p.id, nome: p.nome } })}>
                        Alocar
                      </Botao>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

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
                    <Leito key={l.codigo} leito={l} apagado={!combina(l)} onClick={() => aoClicarLeito(l)} />
                  ))}
                </div>
              ))}
            </div>
          </Card>
        </div>

        <div className="col-salas">
          <Card>
            <div className="titulo-linha"><h2>Salas</h2></div>
            <div className="pilha" style={{ gap: 10 }}>
              {[...dados.salas_parto, ...dados.salas_cirurgia].map((s) => (
                <button type="button" key={s.codigo} className={`sala ${s.paciente ? "ocupada" : "livre"}`}
                  onClick={s.paciente ? () => abrirPaciente(s.paciente.id) : undefined}>
                  <span className="sala-nome">{s.nome}</span>
                  <b>{s.paciente ? s.paciente.nome : "Livre"}</b>
                </button>
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
                <div className="maca" key={m.codigo}>
                  <div className="maca-linha">
                    <button type="button" className="link maca-nome" onClick={() => abrirPaciente(m.id)}>{m.nome}</button>
                    {podeEditar && <Botao onClick={() => setModal({ tipo: "maca", maca: m })}>Editar local</Botao>}
                  </div>
                  <span>{m.local}</span>
                  <small>{m.espera_min == null ? "hora de entrada não informada" : `em maca há ${formatarEspera(m.espera_min)}`}</small>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {modal?.tipo === "paciente" && (
        <ModalPaciente id={modal.id} onFechar={fechar} onMudou={recarregar}
          onAlocar={(paciente) => setModal({ tipo: "alocar", paciente })} />
      )}
      {modal?.tipo === "alocar" && <ModalAlocar paciente={modal.paciente} onFechar={fechar} onMudou={recarregar} />}
      {modal?.tipo === "leito" && <ModalLeito leito={modal.leito} onFechar={fechar} onMudou={recarregar} />}
      {modal?.tipo === "maca" && <ModalMaca maca={modal.maca} onFechar={fechar} onMudou={recarregar} />}
    </div>
  );
}