import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getPainel } from "../api.js";
import { usePodeEditar } from "../auth/useSessao.js";
import Alertas from "../components/Alertas.jsx";
import Botao from "../components/ui/Botao.jsx";
import Card from "../components/ui/Card.jsx";
import Chip from "../components/ui/Chip.jsx";
import { ModalAlocar, ModalLeito, ModalMaca, ModalPaciente } from "./ModaisPainel.jsx";
import "./painel.css";

const NOME_PERFIL = { gestante: "Gestante", puerpera: "Puérpera", abortamento: "Abortamento" };
const ROTULO_ESTADO = { livre: "Livre", ocupado: "Ocupado", limpeza: "Em limpeza", indisponivel: "Indisponível" };
const CLASSE_PRIORIDADE = { Alta: "alta", Média: "media", Normal: "normal" };
// filtro por situação: o chip também serve de legenda (amostra da cor) e mostra a contagem
const SITUACOES = [["livre", "Livres"], ["ocupado", "Ocupados"], ["limpeza", "Em limpeza"]];

function formatarEspera(min) {
  if (min == null) return "sem hora de entrada";
  if (min < 60) return `${min} min de espera`;
  return `${Math.floor(min / 60)}h${String(min % 60).padStart(2, "0")} de espera`;
}

// "1, 2 e 3"
const juntar = (lista) => (lista.length <= 1 ? lista.join("") : `${lista.slice(0, -1).join(", ")} e ${lista.at(-1)}`);

function Indicador({ rotulo, valor, extra, destaque, titulo, children }) {
  return (
    <div className={`indicador${destaque ? " destaque" : ""}`} title={titulo}>
      <span className="indicador-rotulo">{rotulo}</span>
      <span className="indicador-valor">
        {valor}
        {extra && <small>{extra}</small>}
      </span>
      {children}
    </div>
  );
}

function Leito({ leito, apagado, clicavel, onClick }) {
  const { situacao, paciente } = leito;
  const classes = ["leito", situacao, paciente && `perfil-${paciente.perfil}`, apagado && "apagado", !clicavel && "sem-acao"];
  return (
    <button type="button" className={classes.filter(Boolean).join(" ")} onClick={onClick} tabIndex={clicavel ? 0 : -1}
      aria-label={paciente ? `Leito ${leito.letra}, ${paciente.nome}` : `Leito ${leito.letra}, ${ROTULO_ESTADO[situacao]}`}>
      <span className="leito-letra" aria-hidden="true">{leito.letra}</span>
      {paciente ? (
        <span className="leito-corpo">
          <span className="leito-nome">{paciente.nome}</span>
          <span className="leito-detalhe">
            <span className="leito-perfil">{NOME_PERFIL[paciente.perfil] || paciente.perfil}</span>
            <Alertas tags={paciente.tags} soAtencao limite={2} />
          </span>
        </span>
      ) : (
        <span className="leito-estado">{ROTULO_ESTADO[situacao]}</span>
      )}
    </button>
  );
}

// Salas de um tipo: as ocupadas aparecem com o nome da paciente; as livres ficam resumidas numa linha.
function GrupoSalas({ titulo, salas, prefixo = "", onAbrir }) {
  const ocupadas = salas.filter((s) => s.paciente);
  const livres = salas.filter((s) => !s.paciente).map((s) => (prefixo && s.nome.startsWith(prefixo) ? s.nome.slice(prefixo.length) : s.nome));
  return (
    <div className="grupo-salas">
      <div className="grupo-salas-topo">
        <h3>{titulo}</h3>
        <span>{ocupadas.length} de {salas.length} em uso</span>
      </div>
      {ocupadas.map((s) => (
        <button type="button" key={s.codigo} className="sala-ocupada" onClick={() => onAbrir(s.paciente.id)}>
          <span>{s.nome}</span>
          <b>{s.paciente.nome}</b>
        </button>
      ))}
      {livres.length > 0 && (
        <p className="salas-livres">{ocupadas.length === 0 ? (livres.length > 1 ? "Todas livres" : "Livre") : `Livres: ${juntar(livres)}`}</p>
      )}
    </div>
  );
}

export default function Painel() {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(false);
  const [situacao, setSituacao] = useState("todos");
  const [perfil, setPerfil] = useState("todos");
  // modal aberto: null | {tipo: "paciente", id} | {tipo: "alocar", paciente} | {tipo: "leito", leito} | {tipo: "maca", maca}
  const [modal, setModal] = useState(null);
  const podeEditar = usePodeEditar();

  const recarregar = () => getPainel().then((d) => { setDados(d); setErro(false); }).catch(() => setErro(true));
  useEffect(() => { recarregar(); }, []);

  if (erro && !dados) return <p className="tela-carregando">Não foi possível carregar o painel. Verifique a conexão e tente de novo.</p>;
  if (!dados) return <p className="tela-carregando">Carregando…</p>;

  const { ocupacao, sem_leito, pos_parto, pendencias, enfermarias, fila, macas } = dados;
  const fechar = () => setModal(null);
  const abrirPaciente = (id) => setModal({ tipo: "paciente", id });
  const macaDe = Object.fromEntries(macas.map((m) => [m.id, m]));

  const leitos = enfermarias.flatMap((e) => e.leitos);
  const contagem = Object.fromEntries(SITUACOES.map(([v]) => [v, leitos.filter((l) => l.situacao === v).length]));
  const combina = (l) =>
    (situacao === "todos" || l.situacao === situacao) && (perfil === "todos" || l.paciente?.perfil === perfil);

  const aoClicarLeito = (l) => {
    if (l.paciente) abrirPaciente(l.paciente.id);
    else if (podeEditar) setModal({ tipo: "leito", leito: l }); // Gestão não muda o status do leito
  };

  return (
    <div className="painel">
      {ocupacao.alerta && (
        <div className="painel-alerta" role="alert">
          <b>Lotação acima do limite:</b> {ocupacao.ocupados} de {ocupacao.total} leitos ocupados ({ocupacao.percentual}%;
          limite de {ocupacao.limite}%).
        </div>
      )}

      <section className="resumo" aria-label="Resumo do COB">
        <Indicador rotulo="Leitos ocupados" valor={`${ocupacao.ocupados}/${ocupacao.total}`} extra={`${ocupacao.percentual}%`}
          destaque={ocupacao.alerta}
          titulo={`${ocupacao.total} leitos disponíveis e ${ocupacao.indisponiveis} indisponível(is). Alerta a partir de ${ocupacao.limite}%.`}>
          <div className="barra" aria-hidden="true"><div style={{ width: `${Math.min(ocupacao.percentual, 100)}%` }} /></div>
        </Indicador>
        <Indicador rotulo="Aguardando leito" valor={fila.length} extra={sem_leito ? `${sem_leito} em maca` : null}
          titulo="Pacientes na fila: recém-chegadas sem local e pacientes em maca." />
        <Link to="/pendencias" className="indicador-link" title="Abrir a passagem de plantão">
          <Indicador rotulo="Pendências vencidas" valor={pendencias.vencidas}
            extra={pendencias.proximas ? `${pendencias.proximas} vencendo` : null} destaque={pendencias.vencidas > 0} />
        </Link>
        <Indicador rotulo="Pós-parto há mais de 24h" valor={pos_parto.acima_24h}
          extra={pos_parto.perto_48h ? `${pos_parto.perto_48h} perto de 48h` : null}
          titulo="Puérperas no COB há mais de 24h do parto. A decisão de transferir é da equipe." />
      </section>

      <div className="painel-colunas">
        <div className="col-fila">
          <Card>
            <div className="titulo-linha">
              <h2>Fila de espera <span className="contador">{fila.length}</span></h2>
            </div>
            <p className="nota fila-nota">Ordem sugerida pela prioridade. A decisão é da equipe.</p>
            <ul className="fila">
              {fila.length === 0 && <li className="vazio">Ninguém aguardando leito.</li>}
              {fila.map((p) => {
                const maca = macaDe[p.id];
                return (
                  <li className={`fila-item prio-${CLASSE_PRIORIDADE[p.prioridade] || "normal"}`} key={p.id}>
                    <div className="fila-info">
                      <button type="button" className="link fila-nome" onClick={() => abrirPaciente(p.id)}>{p.nome}</button>
                      <div className="fila-meta">
                        <b className="fila-prio">Prioridade {p.prioridade.toLowerCase()}</b> · {formatarEspera(p.espera_min)}
                      </div>
                      <div className="fila-meta">
                        {NOME_PERFIL[p.perfil] || p.perfil} · {maca ? `Maca: ${maca.local}` : "Sem local"}
                        {maca && podeEditar && (
                          <> · <button type="button" className="link link-acao" onClick={() => setModal({ tipo: "maca", maca })}>
                            editar local</button></>
                        )}
                      </div>
                      <Alertas tags={p.tags} soAtencao />
                    </div>
                    {podeEditar && (
                      <Botao variante="primario" onClick={() => setModal({ tipo: "alocar", paciente: { id: p.id, nome: p.nome } })}>
                        Alocar
                      </Botao>
                    )}
                  </li>
                );
              })}
            </ul>
          </Card>
        </div>

        <div className="col-mapa">
          <Card>
            <div className="titulo-linha mapa-topo">
              <h2>Leitos</h2>
              <div className="mapa-filtros" role="group" aria-label="Filtrar leitos">
                <Chip pequeno selecionado={situacao === "todos"} onClick={() => setSituacao("todos")}>Todos</Chip>
                {SITUACOES.map(([valor, rotulo]) => (
                  <Chip key={valor} pequeno selecionado={situacao === valor}
                    onClick={() => setSituacao(situacao === valor ? "todos" : valor)}>
                    <i className={`amostra amostra-${valor}`} aria-hidden="true" />
                    {rotulo} <span className="chip-num">{contagem[valor]}</span>
                  </Chip>
                ))}
                <select className="filtro-perfil" value={perfil} onChange={(e) => setPerfil(e.target.value)} aria-label="Filtrar por perfil">
                  <option value="todos">Todos os perfis</option>
                  {Object.entries(NOME_PERFIL).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
                </select>
              </div>
            </div>
            <div className="enfs">
              {enfermarias.map((enf) => (
                <section className="enf" key={enf.numero} aria-label={`Enfermaria ${enf.numero}`}>
                  <h3 className="enf-nome">Enf. {enf.numero}</h3>
                  {enf.leitos.map((l) => (
                    <Leito key={l.codigo} leito={l} apagado={!combina(l)} clicavel={Boolean(l.paciente) || podeEditar}
                      onClick={() => aoClicarLeito(l)} />
                  ))}
                </section>
              ))}
            </div>
          </Card>
        </div>

        <div className="col-salas">
          <Card>
            <div className="titulo-linha"><h2>Salas</h2></div>
            <GrupoSalas titulo="Parto" salas={dados.salas_parto} prefixo="Sala de parto " onAbrir={abrirPaciente} />
            <GrupoSalas titulo="Centro cirúrgico" salas={dados.salas_cirurgia} prefixo="Centro cirúrgico " onAbrir={abrirPaciente} />
            <GrupoSalas titulo="Apoio" salas={dados.apoio} onAbrir={abrirPaciente} />
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
