import { useEffect, useState } from "react";
import { concluirPendencia, criarPendencia, getPlantao } from "../api.js";
import { usePodeEditar } from "../auth/useSessao.js";
import Botao from "../components/ui/Botao.jsx";
import Card from "../components/ui/Card.jsx";
import Chip from "../components/ui/Chip.jsx";
import Modal from "../components/ui/Modal.jsx";
import Tag from "../components/ui/Tag.jsx";
import { fmtRestante, rotuloStatus, tomStatus } from "./pendenciasUtil.js";
import "./modais.css";
import "./pendencias.css";

const TOM_PERFIL = { gestante: "rosa", puerpera: "roxo", abortamento: "aviso" };
const NOME_PERFIL = { gestante: "Gestante", puerpera: "Puérpera", abortamento: "Abortamento" };
const FILTROS = [["todas", "Todas as pacientes"], ["com", "Só com pendência"], ["vencidas", "Só vencidas"]];

const hora = (iso) =>
  new Date(iso).toLocaleString("pt-BR", { timeZone: "America/Recife", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });

function ModalPendencia({ paciente, onFechar, onSalvo }) {
  const [descricao, setDescricao] = useState("");
  const [prazo, setPrazo] = useState(12);
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);

  async function salvar() {
    setSalvando(true);
    setErro("");
    try {
      await criarPendencia({ paciente_id: paciente.id, descricao, prazo_horas: prazo });
      onSalvo();
      onFechar();
    } catch (e) {
      setErro(e.message);
      setSalvando(false);
    }
  }

  return (
    <Modal aberto titulo="Nova pendência" subtitulo={paciente.nome} onFechar={onFechar} largura={520}>
      <div className="modal-corpo">
        {erro && <p className="erro" role="alert">{erro}</p>}
        <label className="campo">
          O que precisa ser feito?
          <input value={descricao} maxLength={200} onChange={(e) => setDescricao(e.target.value)} placeholder="ex.: coletar exames" autoFocus />
        </label>
        <div>
          <h3 className="secao-titulo">Prazo</h3>
          <div className="grade-chips">
            <Chip selecionado={prazo === 12} onClick={() => setPrazo(12)}>12 horas</Chip>
            <Chip selecionado={prazo === 24} onClick={() => setPrazo(24)}>24 horas</Chip>
          </div>
        </div>
        <div className="linha-acoes">
          <Botao variante="primario" disabled={!descricao.trim() || salvando} onClick={salvar}>Criar pendência</Botao>
          <Botao onClick={onFechar}>Cancelar</Botao>
        </div>
      </div>
    </Modal>
  );
}

export default function Pendencias() {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState("");
  const [filtro, setFiltro] = useState("todas");
  const [nova, setNova] = useState(null);
  const podeEditar = usePodeEditar();

  const carregar = () =>
    getPlantao().then((d) => { setDados(d); setErro(""); }).catch((e) => setErro(e.message));
  useEffect(() => { carregar(); }, []);

  async function concluir(id) {
    try {
      await concluirPendencia(id);
      await carregar();
    } catch (e) {
      setErro(e.message);
    }
  }

  if (!dados) return <p>{erro || "Carregando..."}</p>;

  const { resumo, itens } = dados;
  const visiveis = itens.filter(
    (i) =>
      filtro === "todas" ||
      (filtro === "com" && i.pendencias.some((p) => p.status !== "concluida")) ||
      (filtro === "vencidas" && i.pendencias.some((p) => p.status === "vencida"))
  );

  // agrupa por local mantendo a ordem que veio da API
  const grupos = [];
  for (const item of visiveis) {
    const ultimo = grupos[grupos.length - 1];
    if (ultimo && ultimo.nome === item.grupo) ultimo.itens.push(item);
    else grupos.push({ nome: item.grupo, itens: [item] });
  }

  return (
    <div className="plantao">
      <div className="plantao-topo">
        <h1>Passagem de plantão</h1>
        <div className="no-print"><Botao onClick={() => window.print()}>Imprimir</Botao></div>
      </div>
      <p className="so-impressao">Gerado em {hora(dados.gerado_em)} · Gestar Digital · COB HC-UFPE</p>
      {erro && <p className="erro" role="alert">{erro}</p>}

      <div className="resumo-plantao">
        <Card><div className="kpi"><div className="kpi-rotulo">Vencidas</div><div className="kpi-valor">{resumo.vencidas}</div></div></Card>
        <Card><div className="kpi"><div className="kpi-rotulo">Próximas do vencimento</div><div className="kpi-valor">{resumo.proximas}</div></div></Card>
        <Card><div className="kpi"><div className="kpi-rotulo">Em dia</div><div className="kpi-valor">{resumo.em_dia}</div></div></Card>
        <Card><div className="kpi"><div className="kpi-rotulo">Concluídas (12h)</div><div className="kpi-valor">{resumo.concluidas}</div></div></Card>
      </div>

      <div className="filtros no-print">
        <span className="rotulo">Mostrar</span>
        {FILTROS.map(([valor, rotulo]) => (
          <Chip key={valor} selecionado={filtro === valor} onClick={() => setFiltro(valor)}>{rotulo}</Chip>
        ))}
      </div>

      {grupos.length === 0 && <div className="vazio">Nenhuma paciente para este filtro.</div>}
      {grupos.map((g) => (
        <section className="grupo-plantao" key={g.nome}>
          <h2>{g.nome}</h2>
          {g.itens.map((i) => (
            <div className="pac-plantao" key={i.id}>
              <div className="pac-topo">
                <div>
                  <div className="pac-nome">{i.nome} <span className="pac-meta">· {i.local}</span></div>
                  <div className="pac-meta">{i.gpa} · IG {i.ig}{i.diagnostico ? ` · ${i.diagnostico}` : ""}</div>
                </div>
                <span className="tags">
                  <Tag tom={TOM_PERFIL[i.perfil] || "neutro"}>{NOME_PERFIL[i.perfil] || i.perfil}</Tag>
                  {i.tags.map((t) => <Tag key={t.txt} tom={t.tom}>{t.txt}</Tag>)}
                </span>
              </div>

              {i.pendencias.length === 0 ? (
                <div className="sem-pend">Sem pendências.</div>
              ) : (
                <ul className="pend-lista">
                  {i.pendencias.map((p) => (
                    <li key={p.id} className={`pend-item ${p.status}`}>
                      <span className="pend-texto">
                        {p.descricao}
                        <small>
                          {p.status === "concluida"
                            ? `concluída às ${hora(p.concluida_em)}${p.concluida_por ? ` por ${p.concluida_por}` : ""}`
                            : `${fmtRestante(p.restante_min)} · prazo ${p.prazo_horas}h${p.criada_por ? ` · criada por ${p.criada_por}` : ""}`}
                        </small>
                      </span>
                      <span className="pend-acoes">
                        <Tag tom={tomStatus[p.status]}>{rotuloStatus[p.status]}</Tag>
                        {podeEditar && p.status !== "concluida" && (
                          <span className="no-print"><Botao onClick={() => concluir(p.id)}>Concluir</Botao></span>
                        )}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              {podeEditar && (
                <div className="no-print">
                  <Botao onClick={() => setNova({ id: i.id, nome: i.nome })}>+ Pendência</Botao>
                </div>
              )}
            </div>
          ))}
        </section>
      ))}

      {nova && <ModalPendencia paciente={nova} onFechar={() => setNova(null)} onSalvo={carregar} />}
    </div>
  );
}