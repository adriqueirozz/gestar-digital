import { useEffect, useState } from "react";
import {
  alocarPaciente, atualizarPaciente, editarMaca, getDestinos, getPaciente,
  mudarSituacaoLeito, registrarParto, registrarSaida,
} from "../api.js";
import Botao from "../components/ui/Botao.jsx";
import Chip from "../components/ui/Chip.jsx";
import Modal from "../components/ui/Modal.jsx";
import Tag from "../components/ui/Tag.jsx";
import "./modais.css";

const FUSO = "America/Recife";
const NOME_PERFIL = { gestante: "Gestante", puerpera: "Puérpera", abortamento: "Abortamento" };
const TOM_PERFIL = { gestante: "rosa", puerpera: "roxo", abortamento: "aviso" };
const MOTIVO = { alocacao: "Alocada", movimentacao: "Movida", saida: "Saída" };
const DESFECHO = { casa: "Alta para casa", alojamento: "Alojamento conjunto", transferencia: "Transferência" };
const MARCAS = [
  ["parindo", "Parindo"], ["comorbidade", "Comorbidade"], ["atb", "ATB"],
  ["reserva_sanguinea", "Reserva sanguínea"], ["tarh", "TARH"],
];

export const agoraLocal = () => new Date().toLocaleString("sv-SE", { timeZone: FUSO }).slice(0, 16).replace(" ", "T");
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

/* ------------------------------------------------------------------ ficha da paciente */
export function ModalPaciente({ id, onFechar, onMudou, onAlocar }) {
  const [p, setP] = useState(null);
  const [acao, setAcao] = useState(null); // null | "parto" | "saida"
  const [bolsa, setBolsa] = useState("");
  const [alergia, setAlergia] = useState("");
  const [parto, setParto] = useState({ tipo: "normal", nascimento: "vivo", data_hora: agoraLocal() });
  const [saida, setSaida] = useState({ desfecho: "casa", data_hora: agoraLocal() });
  const { erro, ocupado, executar } = useAcao();

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

  const ativa = p && p.status === "ativa";

  return (
    <Modal aberto titulo={p ? p.nome : "Paciente"} subtitulo={p ? `Prontuário ${p.prontuario ?? "—"}` : ""} onFechar={onFechar} largura={680}>
      {!p ? (
        <p>{erro || "Carregando..."}</p>
      ) : (
        <div className="modal-corpo">
          {erro && <p className="erro" role="alert">{erro}</p>}

          <div className="marcas">
            <Tag tom={TOM_PERFIL[p.perfil] || "neutro"}>{NOME_PERFIL[p.perfil] || p.perfil}</Tag>
            {p.status === "saiu" && <Tag tom="neutro">Saiu: {DESFECHO[p.desfecho] || p.desfecho}</Tag>}
          </div>

          <div className="dados">
            <div><small>Local</small>{p.localizacao ? p.localizacao.nome : ativa ? "Aguardando alocação" : "—"}</div>
            <div><small>GPA / IG</small>{p.gpa || "—"} · {p.ig || "—"}</div>
            <div><small>Entrada no COB</small>{fmt(p.chegada_em)}{p.chegada_tem_hora ? "" : " (sem hora)"}</div>
            <div><small>Tempo no COB</small>{fmtEspera(p.espera_min)}</div>
            <div><small>Pós-parto</small>{p.parto ? `${p.parto.horas}h (${p.parto.tipo}, ${p.parto.nascimento})` : "—"}</div>
            <div><small>Diagnóstico</small>{p.diagnostico || "—"}</div>
          </div>
          {p.observacoes && <div className="dados"><div><small>Observações da planilha</small>{p.observacoes}</div></div>}

          {ativa && (
            <>
              <h3 className="secao-titulo">Sinalizações</h3>
              <div className="marcas">
                {MARCAS.map(([campo, rotulo]) => (
                  <label key={campo}>
                    <input type="checkbox" checked={!!p[campo]} disabled={ocupado} onChange={(e) => salvar({ [campo]: e.target.checked })} />
                    {rotulo}
                  </label>
                ))}
              </div>
              <div className="campos-linha">
                <Campo rotulo="Perfil">
                  <select value={p.perfil} disabled={ocupado} onChange={(e) => salvar({ perfil: e.target.value })}>
                    {Object.entries(NOME_PERFIL).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
                  </select>
                </Campo>
                <Campo rotulo="Alergia">
                  <input value={alergia} onChange={(e) => setAlergia(e.target.value)} onBlur={() => alergia !== (p.alergia ?? "") && salvar({ alergia })} placeholder="ex.: dipirona" />
                </Campo>
                <Campo rotulo="Bolsa rota há (horas)">
                  <input type="number" min="0" max="240" value={bolsa} onChange={(e) => setBolsa(e.target.value)}
                    onBlur={() => String(bolsa) !== String(p.bolsa_rota_horas ?? "") && salvar({ bolsa_rota_horas: bolsa === "" ? null : Number(bolsa) })}
                    placeholder="vazio = sem bolsa rota" />
                </Campo>
              </div>
              {p.bolsa_rota_horas != null && p.bolsa_rota_horas >= 18 && (
                <p className="erro">Bolsa rota há {p.bolsa_rota_horas}h: acima de 18h, avaliar ATB (decisão da equipe).</p>
              )}

              <div className="linha-acoes">
                <Botao variante="primario" onClick={() => onAlocar({ id: p.id, nome: p.nome })}>
                  {p.localizacao ? "Mover" : "Alocar"}
                </Botao>
                {!p.parto && <Botao onClick={() => setAcao(acao === "parto" ? null : "parto")}>Registrar parto</Botao>}
                <Botao onClick={() => setAcao(acao === "saida" ? null : "saida")}>Registrar saída</Botao>
              </div>

              {acao === "parto" && (
                <div className="caixa">
                  <div className="campos-linha">
                    <Campo rotulo="Tipo de parto">
                      <select value={parto.tipo} onChange={(e) => setParto({ ...parto, tipo: e.target.value })}>
                        <option value="normal">Normal</option><option value="cesarea">Cesárea</option><option value="forceps">Fórceps</option>
                      </select>
                    </Campo>
                    <Campo rotulo="Nascimento">
                      <select value={parto.nascimento} onChange={(e) => setParto({ ...parto, nascimento: e.target.value })}>
                        <option value="vivo">Vivo</option><option value="natimorto">Natimorto</option>
                      </select>
                    </Campo>
                    <Campo rotulo="Data e hora">
                      <input type="datetime-local" value={parto.data_hora} max={agoraLocal()} onChange={(e) => setParto({ ...parto, data_hora: e.target.value })} />
                    </Campo>
                  </div>
                  <div className="linha-acoes">
                    <Botao variante="primario" disabled={ocupado}
                      onClick={() => executar(async () => { await registrarParto(id, parto); setAcao(null); await carregar(); onMudou(); })}>
                      Confirmar parto
                    </Botao>
                  </div>
                </div>
              )}

              {acao === "saida" && (
                <div className="caixa">
                  <div className="campos-linha">
                    <Campo rotulo="Desfecho">
                      <select value={saida.desfecho} onChange={(e) => setSaida({ ...saida, desfecho: e.target.value })}>
                        {Object.entries(DESFECHO).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
                      </select>
                    </Campo>
                    <Campo rotulo="Data e hora">
                      <input type="datetime-local" value={saida.data_hora} max={agoraLocal()} onChange={(e) => setSaida({ ...saida, data_hora: e.target.value })} />
                    </Campo>
                  </div>
                  <p className="nota">O leito ou a maca é liberado automaticamente (leito vai para limpeza).</p>
                  <div className="linha-acoes">
                    <Botao variante="primario" disabled={ocupado}
                      onClick={() => executar(async () => { await registrarSaida(id, saida); onMudou(); onFechar(); })}>
                      Confirmar saída
                    </Botao>
                  </div>
                </div>
              )}
            </>
          )}

          <h3 className="secao-titulo">Histórico</h3>
          <ul className="historico">
            {p.historico.length === 0 && <li>Nenhuma movimentação registrada.</li>}
            {p.historico.map((h, i) => (
              <li key={i}>
                <b>{MOTIVO[h.motivo] || h.motivo}</b> · {h.origem ? `${h.origem} → ` : ""}{h.destino || "fora do COB"}
                <br /><small>{fmt(h.data_hora)}{h.observacao ? ` · ${h.observacao}` : ""}</small>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Modal>
  );
}

/* ------------------------------------------------------------------ alocar / mover */
export function ModalAlocar({ paciente, onFechar, onMudou }) {
  const [dest, setDest] = useState(null);
  const [escolhido, setEscolhido] = useState(null);
  const [localMaca, setLocalMaca] = useState("");
  const [dataHora, setDataHora] = useState(agoraLocal());
  const [obs, setObs] = useState("");
  const { erro, ocupado, executar } = useAcao();

  useEffect(() => {
    executar(async () => setDest(await getDestinos()));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const grupos = dest
    ? [["Leitos livres", dest.leitos], ["Salas de parto", dest.salas_parto], ["Cirurgia / curetagem", dest.salas_cirurgia], ["Apoio", dest.apoio]]
    : [];

  return (
    <Modal aberto titulo="Alocar / mover" subtitulo={paciente.nome} onFechar={onFechar} largura={680}>
      <div className="modal-corpo">
        {erro && <p className="erro" role="alert">{erro}</p>}
        {!dest && !erro && <p>Carregando destinos...</p>}
        {grupos.map(([titulo, itens]) => (
          <div key={titulo}>
            <h3 className="secao-titulo">{titulo}</h3>
            {itens.length === 0 ? (
              <p className="nota">Nenhum disponível.</p>
            ) : (
              <div className="grade-chips">
                {itens.map((l) => (
                  <Chip key={l.codigo} selecionado={escolhido === l.codigo} onClick={() => setEscolhido(l.codigo)}>{l.nome}</Chip>
                ))}
              </div>
            )}
          </div>
        ))}
        {dest && (
          <div>
            <h3 className="secao-titulo">Sem leito</h3>
            <div className="grade-chips">
              <Chip selecionado={escolhido === "NOVA_MACA"} onClick={() => setEscolhido("NOVA_MACA")}>Nova maca</Chip>
            </div>
          </div>
        )}
        {escolhido === "NOVA_MACA" && (
          <Campo rotulo="Local da maca">
            <input value={localMaca} onChange={(e) => setLocalMaca(e.target.value)} placeholder="ex.: corredor próximo à enfermaria 3" />
          </Campo>
        )}
        <div className="campos-linha">
          <Campo rotulo="Data e hora">
            <input type="datetime-local" value={dataHora} max={agoraLocal()} onChange={(e) => setDataHora(e.target.value)} />
          </Campo>
          <Campo rotulo="Observação (opcional)">
            <input value={obs} onChange={(e) => setObs(e.target.value)} />
          </Campo>
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

  return (
    <Modal aberto titulo={`Leito ${leito.codigo}`} subtitulo={ROTULO[leito.situacao]} onFechar={onFechar} largura={460}>
      <div className="modal-corpo">
        {erro && <p className="erro" role="alert">{erro}</p>}
        <div className="linha-acoes">
          {leito.situacao === "limpeza" && <Botao variante="primario" disabled={ocupado} onClick={() => mudar("normal")}>Liberar leito (limpeza concluída)</Botao>}
          {leito.situacao === "indisponivel" && <Botao variante="primario" disabled={ocupado} onClick={() => mudar("normal")}>Tornar disponível</Botao>}
          {leito.situacao === "livre" && (
            <>
              <Botao disabled={ocupado} onClick={() => mudar("limpeza")}>Marcar em limpeza</Botao>
              <Botao disabled={ocupado} onClick={() => mudar("indisponivel")}>Marcar indisponível</Botao>
            </>
          )}
        </div>
        <p className="nota">Para ocupar este leito, use o botão Alocar na fila de espera.</p>
      </div>
    </Modal>
  );
}

/* ------------------------------------------------------------------ local da maca */
export function ModalMaca({ maca, onFechar, onMudou }) {
  const [local, setLocal] = useState(maca.local || "");
  const { erro, ocupado, executar } = useAcao();
  return (
    <Modal aberto titulo="Editar local da maca" subtitulo={maca.nome} onFechar={onFechar} largura={460}>
      <div className="modal-corpo">
        {erro && <p className="erro" role="alert">{erro}</p>}
        <Campo rotulo="Local">
          <input value={local} onChange={(e) => setLocal(e.target.value)} placeholder="ex.: corredor próximo à enfermaria 3" />
        </Campo>
        <p className="nota">A maca some da lista quando a paciente é movida para um leito.</p>
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