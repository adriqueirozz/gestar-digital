import { useEffect, useState } from "react";
import {
  alocarPaciente, atualizarPaciente, concluirPendencia, criarPendencia, editarMaca, getDestinos,
  getPaciente, mudarSituacaoLeito, registrarParto, registrarSaida,
} from "../api.js";
import ItemPendencia from "../components/ItemPendencia.jsx";
import Botao from "../components/ui/Botao.jsx";
import Chip from "../components/ui/Chip.jsx";
import Modal from "../components/ui/Modal.jsx";
import Tag from "../components/ui/Tag.jsx";
import { usePodeEditar } from "../auth/useSessao.js";
import "./modais.css";

const FUSO = "America/Recife";
const NOME_PERFIL = { gestante: "Gestante", puerpera: "Puérpera", abortamento: "Abortamento" };
const TOM_PERFIL = { gestante: "rosa", puerpera: "roxo", abortamento: "aviso" };
const MOTIVO = { alocacao: "Alocada", movimentacao: "Movida", saida: "Saída" };
const DESFECHO = { casa: "Alta", alojamento: "Alojamento conjunto", transferencia: "Transferência" };
// "normal" é o código interno do parto vaginal
const TIPO_PARTO = { normal: "parto vaginal", cesarea: "cesárea" };
const NASCIMENTO = { vivo: "nascido vivo", natimorto: "natimorto" };
const MARCAS = [
  ["parindo", "Em trabalho de parto"], ["comorbidade", "Comorbidade"], ["atb", "ATB"],
  ["reserva_sanguinea", "Reserva sanguínea"], ["tarh", "TARH"],
];

const agoraLocal = () => new Date().toLocaleString("sv-SE", { timeZone: FUSO }).slice(0, 16).replace(" ", "T");
const fmt = (iso) =>
  iso ? new Date(iso).toLocaleString("pt-BR", { timeZone: FUSO, day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—";
const fmtEspera = (min) => (min == null ? "—" : min < 60 ? `${min} min` : `${Math.floor(min / 60)}h${String(min % 60).padStart(2, "0")}`);

// executa uma ação e guarda a mensagem de erro para mostrar no modal
function useAcao() {
  const [erro, setErro] = useState("");
  const [ocupado, setOcupado] = useState(false);
  async function executar(fn) {
    setOcupado(true);
    setErro("");
    try {
      await fn();
    } catch (e) {
      setErro(e.message);
    } finally {
      setOcupado(false);
    }
  }
  return { erro, ocupado, executar };
}

function Campo({ rotulo, children }) {
  return (
    <label className="campo">
      {rotulo}
      {children}
    </label>
  );
}

// Horário do registro: por padrão "agora"; o campo de data e hora só aparece se a pessoa quiser mudar.
function Horario({ valor, onMudar }) {
  const [editando, setEditando] = useState(false);
  if (!editando) {
    return (
      <p className="horario">
        Horário: <b>agora, {valor.slice(11)}</b>{" "}
        <button type="button" className="link link-acao" onClick={() => setEditando(true)}>alterar</button>
      </p>
    );
  }
  return (
    <Campo rotulo="Data e hora">
      <input type="datetime-local" value={valor} max={agoraLocal()} onChange={(e) => onMudar(e.target.value)} autoFocus />
    </Campo>
  );
}

/* ------------------------------------------------------------------ ficha da paciente */
export function ModalPaciente({ id, onFechar, onMudou, onAlocar }) {
  const [p, setP] = useState(null);
  const [acao, setAcao] = useState(null); // null | "parto" | "saida"
  const [bolsa, setBolsa] = useState("");
  const [alergia, setAlergia] = useState("");
  const [parto, setParto] = useState({ tipo: "normal", nascimento: "vivo", data_hora: agoraLocal() });
  const [saida, setSaida] = useState({ desfecho: "casa", data_hora: agoraLocal() });
  const { erro, ocupado, executar } = useAcao();
  const podeEditar = usePodeEditar();

  async function carregar() {
    const dados = await getPaciente(id);
    setP(dados);
    setBolsa(dados.bolsa_rota_horas ?? "");
    setAlergia(dados.alergia ?? "");
  }
  useEffect(() => {
    executar(carregar);
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const salvar = (dados) =>
    executar(async () => {
      await atualizarPaciente(id, dados);
      await carregar();
      onMudou();
    });

  // abre/fecha o formulário de parto ou saída, sempre com o horário de agora
  function alternar(qual) {
    if (acao === qual) return setAcao(null);
    if (qual === "parto") setParto({ ...parto, data_hora: agoraLocal() });
    if (qual === "saida") setSaida({ ...saida, data_hora: agoraLocal() });
    setAcao(qual);
  }

  const ativa = p && p.status === "ativa";
  const local = p && (p.localizacao ? p.localizacao.nome : ativa ? "Aguardando leito" : null);
  // perfil e situação ficam na mesma linha do prontuário, sem ocupar uma linha só para eles
  const subtitulo = p && (
    <span className="ficha-sub">
      {[`Prontuário ${p.prontuario ?? "—"}`, local].filter(Boolean).join(" · ")}
      <Tag tom={TOM_PERFIL[p.perfil] || "neutro"}>{NOME_PERFIL[p.perfil] || p.perfil}</Tag>
      {p.status === "saiu" && <Tag tom="neutro">Saiu: {DESFECHO[p.desfecho] || p.desfecho}</Tag>}
    </span>
  );

  return (
    <Modal aberto titulo={p ? p.nome : "Paciente"} subtitulo={subtitulo} onFechar={onFechar} largura={680}>
      {!p ? (
        <p>{erro || "Carregando..."}</p>
      ) : (
        <div className="modal-corpo ficha">
          {erro && <p className="erro" role="alert">{erro}</p>}

          {/* ações principais primeiro */}
          {ativa && podeEditar && (
            <div className="linha-acoes">
              <Botao variante="primario" onClick={() => onAlocar({ id: p.id, nome: p.nome })}>
                {p.localizacao ? "Mover" : "Alocar"}
              </Botao>
              {!p.parto && <Botao aria-expanded={acao === "parto"} onClick={() => alternar("parto")}>Registrar parto</Botao>}
              <Botao aria-expanded={acao === "saida"} onClick={() => alternar("saida")}>Registrar saída</Botao>
            </div>
          )}

          {acao === "parto" && (
            <div className="caixa">
              <div className="campos-linha">
                <Campo rotulo="Tipo de parto">
                  <select value={parto.tipo} onChange={(e) => setParto({ ...parto, tipo: e.target.value })}>
                    <option value="normal">Parto vaginal</option><option value="cesarea">Cesárea</option>
                  </select>
                </Campo>
                <Campo rotulo="Nascimento">
                  <select value={parto.nascimento} onChange={(e) => setParto({ ...parto, nascimento: e.target.value })}>
                    <option value="vivo">Vivo</option><option value="natimorto">Natimorto</option>
                  </select>
                </Campo>
              </div>
              <Horario valor={parto.data_hora} onMudar={(v) => setParto({ ...parto, data_hora: v })} />
              <div className="linha-acoes">
                <Botao variante="primario" disabled={ocupado}
                  onClick={() => executar(async () => { await registrarParto(id, parto); setAcao(null); await carregar(); onMudou(); })}>
                  Confirmar parto
                </Botao>
                <Botao onClick={() => setAcao(null)}>Cancelar</Botao>
              </div>
            </div>
          )}

          {acao === "saida" && (
            <div className="caixa">
              <Campo rotulo="Desfecho">
                <select value={saida.desfecho} onChange={(e) => setSaida({ ...saida, desfecho: e.target.value })}>
                  {Object.entries(DESFECHO).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
                </select>
              </Campo>
              <Horario valor={saida.data_hora} onMudar={(v) => setSaida({ ...saida, data_hora: v })} />
              <p className="nota">O leito vai para limpeza automaticamente.</p>
              <div className="linha-acoes">
                <Botao variante="primario" disabled={ocupado}
                  onClick={() => executar(async () => { await registrarSaida(id, saida); onMudou(); onFechar(); })}>
                  Confirmar saída
                </Botao>
                <Botao onClick={() => setAcao(null)}>Cancelar</Botao>
              </div>
            </div>
          )}

          {/* só mostra o que tem valor */}
          <dl className="dados">
            <div><dt>GPA · IG</dt><dd>{p.gpa || "—"} · {p.ig || "—"}</dd></div>
            <div><dt>Diagnóstico</dt><dd>{p.diagnostico || "—"}</dd></div>
            <div><dt>Entrada no COB</dt><dd>{fmt(p.chegada_em)}{p.chegada_tem_hora ? "" : " (sem hora)"}</dd></div>
            {p.espera_min != null && <div><dt>Tempo no COB</dt><dd>{fmtEspera(p.espera_min)}</dd></div>}
            {p.parto && (
              <div>
                <dt>Pós-parto</dt>
                <dd>{p.parto.horas}h · {TIPO_PARTO[p.parto.tipo] || p.parto.tipo}, {NASCIMENTO[p.parto.nascimento] || p.parto.nascimento}
                  {p.parto.registrado_por && <small>registrado por {p.parto.registrado_por}</small>}</dd>
              </div>
            )}
            {p.observacoes && <div className="dados-largo"><dt>Observações da planilha</dt><dd>{p.observacoes}</dd></div>}
          </dl>

          {ativa && !podeEditar && <SinalizacoesLeitura p={p} />}

          {ativa && podeEditar && (
            <section className="ficha-secao" aria-labelledby="titulo-sinalizacoes">
              <h3 className="secao-titulo" id="titulo-sinalizacoes">Sinalizações</h3>
              <div className="grade-chips">
                {MARCAS.map(([campo, rotulo]) => (
                  <Chip key={campo} pequeno selecionado={!!p[campo]} disabled={ocupado}
                    onClick={() => salvar({ [campo]: !p[campo] })}>
                    {p[campo] ? "✓ " : ""}{rotulo}
                  </Chip>
                ))}
              </div>
              <div className="campos-linha">
                <Campo rotulo="Alergia">
                  <input value={alergia} onChange={(e) => setAlergia(e.target.value)}
                    onBlur={() => alergia !== (p.alergia ?? "") && salvar({ alergia })} placeholder="nenhuma" />
                </Campo>
                <Campo rotulo="Bolsa rota há (horas)">
                  <input type="number" min="0" max="240" value={bolsa} onChange={(e) => setBolsa(e.target.value)}
                    onBlur={() => String(bolsa) !== String(p.bolsa_rota_horas ?? "") && salvar({ bolsa_rota_horas: bolsa === "" ? null : Number(bolsa) })}
                    placeholder="sem bolsa rota" />
                </Campo>
                <Campo rotulo="Perfil">
                  <select value={p.perfil} disabled={ocupado} onChange={(e) => salvar({ perfil: e.target.value })}>
                    {Object.entries(NOME_PERFIL).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
                  </select>
                </Campo>
              </div>
              {p.bolsa_rota_horas != null && p.bolsa_rota_horas >= 18 && (
                <p className="erro">Bolsa rota há {p.bolsa_rota_horas}h: acima de 18h, avaliar ATB (decisão da equipe).</p>
              )}
            </section>
          )}

          {ativa && (
            <PendenciasDaPaciente
              pacienteId={p.id}
              pendencias={p.pendencias}
              podeEditar={podeEditar}
              aoMudar={async () => { await carregar(); onMudou(); }}
            />
          )}

          {/* histórico fica recolhido: é consulta, não ação */}
          <details className="ficha-historico">
            <summary>Histórico de movimentações ({p.historico.length})</summary>
            <ul className="historico">
              {p.historico.length === 0 && <li>Nenhuma movimentação registrada.</li>}
              {p.historico.map((h, i) => (
                <li key={i}>
                  <b>{MOTIVO[h.motivo] || h.motivo}</b> · {h.origem ? `${h.origem} → ` : ""}{h.destino || "fora do COB"}
                  <br /><small>{fmt(h.data_hora)}{h.usuario ? ` · por ${h.usuario}` : ""}{h.observacao ? ` · ${h.observacao}` : ""}</small>
                </li>
              ))}
            </ul>
          </details>
        </div>
      )}
    </Modal>
  );
}

/* ------------------------------------------------------------------ sinalizações (somente leitura) */
function SinalizacoesLeitura({ p }) {
  const ativas = MARCAS.filter(([campo]) => p[campo]).map(([, rotulo]) => rotulo);
  return (
    <section className="ficha-secao">
      <h3 className="secao-titulo">Sinalizações</h3>
      <div className="marcas">
        {ativas.length === 0 && !p.alergia && p.bolsa_rota_horas == null && <span className="nota">Nenhuma sinalização.</span>}
        {ativas.map((r) => <Tag key={r} tom="info">{r}</Tag>)}
        {p.alergia && <Tag tom="alerta">Alergia: {p.alergia}</Tag>}
        {p.bolsa_rota_horas != null && <Tag tom="aviso">Bolsa rota há {p.bolsa_rota_horas}h</Tag>}
      </div>
      {p.bolsa_rota_horas != null && p.bolsa_rota_horas >= 18 && (
        <p className="erro">Bolsa rota há {p.bolsa_rota_horas}h: acima de 18h, avaliar ATB (decisão da equipe).</p>
      )}
    </section>
  );
}

/* ------------------------------------------------------------------ alocar / mover */
// leitos livres agrupados por enfermaria: "Enf. 4  [A] [B]"
function agruparLeitos(leitos) {
  const grupos = [];
  for (const l of leitos) {
    const enf = l.codigo.slice(1, -1);
    const ultimo = grupos[grupos.length - 1];
    if (ultimo && ultimo.enf === enf) ultimo.leitos.push(l);
    else grupos.push({ enf, leitos: [l] });
  }
  return grupos;
}

export function ModalAlocar({ paciente, onFechar, onMudou }) {
  const [dest, setDest] = useState(null);
  const [escolhido, setEscolhido] = useState(null);
  const [localMaca, setLocalMaca] = useState("");
  const [dataHora, setDataHora] = useState(agoraLocal());
  const [obs, setObs] = useState("");
  const [comObs, setComObs] = useState(false);
  const { erro, ocupado, executar } = useAcao();

  useEffect(() => {
    executar(async () => setDest(await getDestinos()));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const outros = dest
    ? [["Salas de parto", dest.salas_parto], ["Cirurgia / curetagem", dest.salas_cirurgia], ["Apoio", dest.apoio]]
    : [];
  const opcao = (l, rotulo, aria) => (
    <Chip key={l.codigo} selecionado={escolhido === l.codigo} onClick={() => setEscolhido(l.codigo)} aria-label={aria}>{rotulo}</Chip>
  );

  return (
    <Modal aberto titulo="Alocar / mover" subtitulo={paciente.nome} onFechar={onFechar} largura={680}>
      <div className="modal-corpo">
        {erro && <p className="erro" role="alert">{erro}</p>}
        {!dest && !erro && <p>Carregando destinos...</p>}

        {dest && (
          <section>
            <h3 className="secao-titulo">Leitos livres</h3>
            {dest.leitos.length === 0 ? (
              <p className="nota">Nenhum leito livre.</p>
            ) : (
              <div className="grade-enfermarias">
                {agruparLeitos(dest.leitos).map((g) => (
                  <div className="destino-enf" key={g.enf}>
                    <span>Enf. {g.enf}</span>
                    {g.leitos.map((l) => opcao(l, l.codigo.slice(-1), `Enfermaria ${g.enf}, leito ${l.codigo.slice(-1)}`))}
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
        {outros.map(([titulo, itens]) => itens.length > 0 && (
          <section key={titulo}>
            <h3 className="secao-titulo">{titulo}</h3>
            <div className="grade-chips">{itens.map((l) => opcao(l, l.nome))}</div>
          </section>
        ))}
        {dest && (
          <section>
            <h3 className="secao-titulo">Sem leito</h3>
            <div className="grade-chips">
              <Chip selecionado={escolhido === "NOVA_MACA"} onClick={() => setEscolhido("NOVA_MACA")}>Maca</Chip>
            </div>
          </section>
        )}
        {escolhido === "NOVA_MACA" && (
          <Campo rotulo="Onde fica a maca?">
            <input value={localMaca} onChange={(e) => setLocalMaca(e.target.value)} placeholder="ex.: corredor próximo à enfermaria 3" autoFocus />
          </Campo>
        )}

        <div className="detalhes-registro">
          <Horario valor={dataHora} onMudar={setDataHora} />
          {comObs ? (
            <Campo rotulo="Observação">
              <input value={obs} onChange={(e) => setObs(e.target.value)} autoFocus />
            </Campo>
          ) : (
            <button type="button" className="link link-acao" onClick={() => setComObs(true)}>+ Adicionar observação</button>
          )}
        </div>

        <div className="linha-acoes">
          <Botao variante="primario" disabled={!escolhido || ocupado}
            onClick={() => executar(async () => {
              await alocarPaciente(paciente.id, { destino: escolhido, data_hora: dataHora, observacao: obs, local_maca: localMaca });
              onMudou();
              onFechar();
            })}>
            Confirmar
          </Botao>
          <Botao onClick={onFechar}>Cancelar</Botao>
        </div>
      </div>
    </Modal>
  );
}

/* ------------------------------------------------------------------ leito sem paciente */
export function ModalLeito({ leito, onFechar, onMudou }) {
  const { erro, ocupado, executar } = useAcao();
  const mudar = (situacao) =>
    executar(async () => {
      await mudarSituacaoLeito(leito.codigo, situacao);
      onMudou();
      onFechar();
    });
  const ROTULO = { livre: "Livre", limpeza: "Em limpeza", indisponivel: "Indisponível" };
  const titulo = `Enf. ${leito.codigo.slice(1, -1)} · Leito ${leito.codigo.slice(-1)}`;

  return (
    <Modal aberto titulo={titulo} subtitulo={ROTULO[leito.situacao]} onFechar={onFechar} largura={460}>
      <div className="modal-corpo">
        {erro && <p className="erro" role="alert">{erro}</p>}
        <div className="linha-acoes">
          {leito.situacao === "limpeza" && <Botao variante="primario" disabled={ocupado} onClick={() => mudar("normal")}>Limpeza concluída: liberar leito</Botao>}
          {leito.situacao === "indisponivel" && <Botao variante="primario" disabled={ocupado} onClick={() => mudar("normal")}>Tornar disponível</Botao>}
          {leito.situacao === "livre" && (
            <>
              <Botao disabled={ocupado} onClick={() => mudar("limpeza")}>Marcar em limpeza</Botao>
              <Botao disabled={ocupado} onClick={() => mudar("indisponivel")}>Marcar indisponível</Botao>
            </>
          )}
        </div>
        {leito.situacao === "livre" && <p className="nota">Para ocupar este leito, use Alocar na fila de espera.</p>}
      </div>
    </Modal>
  );
}

/* ------------------------------------------------------------------ local da maca */
export function ModalMaca({ maca, onFechar, onMudou }) {
  const [local, setLocal] = useState(maca.local || "");
  const { erro, ocupado, executar } = useAcao();
  return (
    <Modal aberto titulo="Local da maca" subtitulo={maca.nome} onFechar={onFechar} largura={460}>
      <div className="modal-corpo">
        {erro && <p className="erro" role="alert">{erro}</p>}
        <Campo rotulo="Onde fica a maca?">
          <input value={local} onChange={(e) => setLocal(e.target.value)} placeholder="ex.: corredor próximo à enfermaria 3" autoFocus />
        </Campo>
        <div className="linha-acoes">
          <Botao variante="primario" disabled={ocupado}
            onClick={() => executar(async () => { await editarMaca(maca.codigo, local); onMudou(); onFechar(); })}>
            Salvar
          </Botao>
          <Botao onClick={onFechar}>Cancelar</Botao>
        </div>
      </div>
    </Modal>
  );
}

/* ------------------------------------------------------------------ pendências da paciente */
function PendenciasDaPaciente({ pacienteId, pendencias, podeEditar, aoMudar }) {
  const [descricao, setDescricao] = useState("");
  const [prazo, setPrazo] = useState(12);
  const { erro, ocupado, executar } = useAcao();

  function adicionar(e) {
    e.preventDefault();
    if (!descricao.trim()) return;
    executar(async () => {
      await criarPendencia({ paciente_id: pacienteId, descricao, prazo_horas: prazo });
      setDescricao("");
      await aoMudar();
    });
  }

  return (
    <section className="ficha-secao" aria-labelledby="titulo-pendencias">
      <h3 className="secao-titulo" id="titulo-pendencias">Pendências</h3>
      {erro && <p className="erro" role="alert">{erro}</p>}
      {pendencias.length === 0 && !podeEditar && <p className="nota">Nenhuma pendência aberta.</p>}
      {pendencias.length > 0 && (
        <ul className="pend-lista">
          {pendencias.map((x) => (
            <ItemPendencia key={x.id} pendencia={x} podeEditar={podeEditar} ocupado={ocupado}
              onConcluir={() => executar(async () => { await concluirPendencia(x.id); await aoMudar(); })} />
          ))}
        </ul>
      )}
      {podeEditar && (
        <form className="pend-nova" onSubmit={adicionar}>
          <input value={descricao} maxLength={200} onChange={(e) => setDescricao(e.target.value)}
            placeholder="Nova pendência (ex.: coletar exames)" aria-label="Nova pendência" />
          <select value={prazo} onChange={(e) => setPrazo(Number(e.target.value))} aria-label="Prazo">
            <option value={12}>em 12h</option>
            <option value={24}>em 24h</option>
          </select>
          <Botao type="submit" disabled={!descricao.trim() || ocupado}>Adicionar</Botao>
        </form>
      )}
    </section>
  );
}
