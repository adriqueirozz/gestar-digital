import { useEffect, useState } from "react";
import { concluirPendencia, criarPendencia, getPlantao } from "../api.js";
import { usePodeEditar } from "../auth/useSessao.js";
import Alertas from "../components/Alertas.jsx";
import ItemPendencia from "../components/ItemPendencia.jsx";
import Botao from "../components/ui/Botao.jsx";
import Chip from "../components/ui/Chip.jsx";
import Modal from "../components/ui/Modal.jsx";
import { fmtDataHora } from "./pendenciasUtil.js";
import "./modais.css";
import "./pendencias.css";

const NOME_PERFIL = { gestante: "Gestante", puerpera: "Puérpera", abortamento: "Abortamento" };
const plural = (n, um, varios) => `${n} ${n === 1 ? um : varios}`;

function ModalPendencia({ paciente, onFechar, onSalvo }) {
  const [descricao, setDescricao] = useState("");
  const [prazo, setPrazo] = useState(12);
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);

  async function salvar(e) {
    e.preventDefault();
    setSalvando(true);
    setErro("");
    try {
      await criarPendencia({ paciente_id: paciente.id, descricao, prazo_horas: prazo });
      onSalvo();
      onFechar();
    } catch (falha) {
      setErro(falha.message);
      setSalvando(false);
    }
  }

  return (
    <Modal aberto titulo="Nova pendência" subtitulo={paciente.nome} onFechar={onFechar} largura={520}>
      <form className="modal-corpo" onSubmit={salvar}>
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
          <Botao type="submit" variante="primario" disabled={!descricao.trim() || salvando}>Criar pendência</Botao>
          <Botao onClick={onFechar}>Cancelar</Botao>
        </div>
      </form>
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

  if (!dados) return <p className="tela-carregando">{erro || "Carregando…"}</p>;

  const { resumo, itens } = dados;
  const abertas = (i) => i.pendencias.some((p) => p.status !== "concluida");
  const vencidas = (i) => i.pendencias.some((p) => p.status === "vencida");
  // os filtros já mostram quantas pacientes há em cada um
  const FILTROS = [
    ["todas", "Todas as pacientes", itens.length],
    ["com", "Com pendência", itens.filter(abertas).length],
    ["vencidas", "Com vencida", itens.filter(vencidas).length],
  ];
  const visiveis = itens.filter((i) => filtro === "todas" || (filtro === "com" && abertas(i)) || (filtro === "vencidas" && vencidas(i)));

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
        <div>
          <h1>Passagem de plantão</h1>
          {/* resumo numa linha só: o que exige atenção vem primeiro e colorido */}
          <p className="plantao-resumo">
            <span className={resumo.vencidas ? "resumo-vencida" : undefined}>{plural(resumo.vencidas, "vencida", "vencidas")}</span>
            {" · "}
            <span className={resumo.proximas ? "resumo-proxima" : undefined}>{plural(resumo.proximas, "vencendo em breve", "vencendo em breve")}</span>
            {" · "}{resumo.em_dia} em dia · {plural(resumo.concluidas, "concluída", "concluídas")} nas últimas 12h
          </p>
        </div>
        <div className="no-print"><Botao onClick={() => window.print()}>Imprimir</Botao></div>
      </div>
      <p className="so-impressao">Gerado em {fmtDataHora(dados.gerado_em)} · Gestar Digital · COB HC-UFPE</p>
      {erro && <p className="erro" role="alert">{erro}</p>}

      <div className="filtros no-print" role="group" aria-label="Mostrar">
        {FILTROS.map(([valor, rotulo, n]) => (
          <Chip key={valor} pequeno selecionado={filtro === valor} onClick={() => setFiltro(valor)}>
            {rotulo} <span className="chip-num">{n}</span>
          </Chip>
        ))}
      </div>

      {grupos.length === 0 && <div className="vazio">Nenhuma paciente para este filtro.</div>}
      {grupos.map((g) => (
        <section className="grupo-plantao" key={g.nome}>
          <h2>{g.nome}</h2>
          {g.itens.map((i) => (
            <article className="pac-plantao" key={i.id}>
              <div className="pac-topo">
                <div className="pac-id">
                  <div className="pac-nome">{i.nome} <span className="pac-local">{i.local}</span></div>
                  <div className="pac-meta">
                    {NOME_PERFIL[i.perfil] || i.perfil} · {i.gpa} · IG {i.ig}{i.diagnostico ? ` · ${i.diagnostico}` : ""}
                  </div>
                  <Alertas tags={i.tags} />
                </div>
                {podeEditar && (
                  <span className="no-print">
                    <Botao pequeno onClick={() => setNova({ id: i.id, nome: i.nome })}>+ Pendência</Botao>
                  </span>
                )}
              </div>

              {i.pendencias.length > 0 ? (
                <ul className="pend-lista">
                  {i.pendencias.map((p) => (
                    <ItemPendencia key={p.id} pendencia={p} podeEditar={podeEditar} onConcluir={() => concluir(p.id)} />
                  ))}
                </ul>
              ) : (
                <p className="sem-pend so-impressao">Sem pendências.</p>
              )}
            </article>
          ))}
        </section>
      ))}

      {nova && <ModalPendencia paciente={nova} onFechar={() => setNova(null)} onSalvo={carregar} />}
    </div>
  );
}
