# Gestar Digital

Observatório de gestão do Centro Obstétrico (COB) do Hospital das Clínicas da UFPE: mostra a ocupação dos leitos, a fila de espera e os indicadores do setor a partir de dados de gestão.

> **Não é um prontuário eletrônico.** O sistema apoia a decisão da equipe e não substitui o registro clínico.
> Os dados usados no desenvolvimento são **todos simulados**.

## Tecnologias

| Parte | Tecnologia |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2, pandas |
| Banco de dados | SQLite (arquivo local `gestar.db`) |
| Frontend | React + Vite (JavaScript), react-router-dom |
| Testes | pytest |

## Estrutura do repositório

```
gestar-digital/
├── backend/
│   ├── app/
│   │   ├── main.py            # cria a API e registra as rotas
│   │   ├── config.py          # configurações
│   │   ├── database.py        # conexão com o SQLite
│   │   ├── models.py          # tabelas do banco
│   │   ├── seed.py            # carga de dados simulados
│   │   ├── routers/           # health, painel, importacoes
│   │   └── services/          # planilha.py (leitura) e importacao.py (banco)
│   ├── tests/
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   └── src/                   # pages, components/ui, styles, api.js
├── data/sample/               # planilhas CSV fictícias para teste
└── docs/
```

## Pré-requisitos

- [Python 3.11 ou superior](https://www.python.org/downloads/) (marque "Add Python to PATH" na instalação)
- [Node.js 20 ou superior](https://nodejs.org/) (já inclui o npm)
- [Git](https://git-scm.com/)

Conferir as versões:
```powershell
python --version
node --version
npm --version
```

## Como rodar (do zero)

Abra **dois terminais**: um para o backend e outro para o frontend.

### 1. Backend e banco de dados

```powershell
cd backend

# criar e ativar o ambiente virtual (só na primeira vez criar)
python -m venv .venv
.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate

# instalar as dependências
pip install -r requirements-dev.txt

# criar o banco e popular com dados simulados
python -m app.seed --recriar

# subir a API
uvicorn app.main:app --reload
```

Se o PowerShell bloquear a ativação do ambiente, rode uma vez:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

A API fica em **http://localhost:8000**:
- Documentação interativa: 
- Saúde da API: http://localhost:8000/health
- Dados do painel: http://localhost:8000/api/painel

> Rode sempre os comandos de dentro da pasta `backend/`. O arquivo `gestar.db` é criado nela.

### 2. Frontend

```powershell
cd frontend
npm install
npm install react-router-dom   # só se o npm install não instalar
npm run dev
```

Abra **http://localhost:5173**. O frontend conversa com a API em `http://localhost:8000` (endereço definido em `src/api.js`). A API precisa estar rodando.

## Banco de dados (SQLite)

O banco é um arquivo local (`backend/gestar.db`). Não há nada para instalar nem configurar. As tabelas são criadas automaticamente.

| Comando (dentro de `backend/`) | O que faz |
|---|---|
| `python -m app.seed` | Cria o banco e popula com leitos, salas, 8 pacientes e 3 usuários de demonstração. Num banco já populado, só cria os usuários que faltarem |
| `python -m app.seed --sem-pacientes` | Só o catálogo (leitos, salas, macas). Ideal para demonstrar a importação |
| `python -m app.seed --recriar` | **Apaga tudo** e popula de novo |
| `python -m app.seed --recriar --sem-pacientes` | Apaga tudo e deixa só o catálogo |

Para zerar o banco manualmente, pare a API e apague o arquivo `backend/gestar.db`.

Não usamos migrações (Alembic). Quando o `models.py` mudar, recrie o banco com `--recriar`.

### Alterar a quantidade de leitos

No topo de `backend/app/seed.py`:http://localhost:8000/docs

```python
NUM_ENFERMARIAS = 9
LETRAS_LEITO = "AB"       # leitos por enfermaria: "AB" = 2 leitos, "ABC" = 3
INDISPONIVEIS = {"E9B"}   # leitos fora de uso
EM_LIMPEZA = {"E3B"}      # leitos em limpeza
```

Depois, `python -m app.seed --recriar`.

## Importação da planilha

Na tela **Integração** do frontend (ou no `POST /api/importacoes` em `/docs`), envie um arquivo `.csv` ou `.xlsx` com as colunas:

| Coluna | Formato |
|---|---|
| leito | `Enf 3 - Leito A`, `E3A` ou `3A`. Vazio = paciente vai para a fila |
| código do prontuário | numérico. É a chave que identifica a paciente |
| data de entrada no COB | `dd/mm/aaaa` (a hora é opcional) |
| nome completo | texto |
| GPA | `G1P2A3` |
| IG | semanas (ex.: `39`, `39s2d`, `39+2`) |
| diagnóstico | texto livre |
| OBS | texto livre (coluna opcional) |

Regras:
- A planilha manda nos dados de **origem** (nome, GPA, IG, diagnóstico, observações, data de entrada).
- O Gestar manda na **localização** e no estado da paciente. Uma reimportação **nunca move** uma paciente que já existe; se a planilha indicar outro leito, aparece uma "divergência" na conferência.
- Erro de digitação não faz a paciente sumir: ela entra na fila e o problema aparece na tela de conferência. Só ficam de fora linhas sem prontuário numérico, sem nome ou com prontuário repetido no arquivo.

Planilhas fictícias para teste, em `data/sample/`:
- `pacientes_teste.csv` (13 linhas)
- `pacientes_teste_2.csv` (25 linhas, mais casos de erro)

Teste rápido: `python -m app.seed --recriar --sem-pacientes`, depois envie um dos CSVs na tela de Integração e volte ao painel.

## Testes

```powershell
cd backend
python -m pytest -v
```

Use `python -m pytest` (e não só `pytest`) para o Python encontrar o pacote `app`.

## Login e perfis

Perfis: `enfermagem`, `medico` e `gestao`. O seed cria um usuário de demonstração para cada um (senhas só para uso local; no protótipo hospedado a senha é a da variável `GESTAR_SENHA_DEMO`):

| Login | Senha | Perfil |
|---|---|---|
| `enfermagem` | `gestar123` | Enfermagem |
| `medico` | `gestar123` | Médico |
| `gestao` | `gestar123` | Gestão |

- `POST /api/auth/login` recebe `username` e `password` (formulário) e devolve um token válido por 12h. Envie-o nas outras chamadas no cabeçalho `Authorization: Bearer <token>`.
- No frontend, a tela **/login** abre sozinha quando ninguém está logado. O nome e o perfil aparecem no topo; clicando neles dá para **trocar de usuário** (os usuários recentes daquele computador ficam listados, sem senha) ou **sair**.
- No `/docs`, use o botão **Authorize** para entrar com um desses usuários.
- As senhas ficam no banco só como hash (PBKDF2-SHA256).

Variáveis de ambiente (opcionais):

| Variável | Padrão | Para quê |
|---|---|---|
| `EXIGIR_LOGIN` | `true` | Toda rota `/api` exige token. `false` libera as rotas sem login (só para depurar pela linha de comando) |
| `GESTAR_SECRET_KEY` | chave de desenvolvimento | Assina os tokens. **Obrigatório trocar** fora da máquina local |
| `GESTAR_TOKEN_HORAS` | `12` | Validade do token, em horas |

### O que cada perfil pode fazer

| Ação | Enfermagem | Médico | Gestão |
|---|---|---|---|
| Ver painel, fila, ficha, pendências, plantão e relatório | ✅ | ✅ | ✅ |
| Alocar e mover pacientes, registrar parto e saída | ✅ | ✅ | ❌ |
| Editar sinalizações, status do leito e local da maca | ✅ | ✅ | ❌ |
| Criar e concluir pendências | ✅ | ✅ | ❌ |
| Importar a planilha | ✅ | ✅ | ❌ |

- **Gestão é somente leitura:** o backend responde **403** em qualquer rota de escrita, e o frontend esconde os botões de edição e mostra "Somente leitura" no cabeçalho.
- **Rota nova que altera dados:** coloque `usuario=Depends(editor)` (de `app.auth`) e passe `usuario_id=id_de(usuario)` para o serviço, para registrar quem fez.
- **Botão novo de edição no frontend:** mostre só se `usePodeEditar()` (de `src/auth/useSessao.js`) for `true`.
- Para mudar quem pode editar, altere `PERFIS_QUE_EDITAM` em `backend/app/auth.py`. Para uma regra específica de uma rota, use `Depends(exigir_perfil("medico"))`.

### Quem alterou cada informação

Movimentações (alocar, mover, saída), partos, pendências (criação e conclusão) e importações guardam **quem fez e quando**. A ficha da paciente mostra "por Fulano" no histórico, no parto e nas pendências; a passagem de plantão mostra quem criou e quem concluiu cada pendência.

## API (resumo)

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Verifica se a API está no ar |
| POST | `/api/auth/login` | Entra com login e senha e devolve o token |
| GET | `/api/auth/me` | Dados do usuário logado |
| GET | `/api/painel` | Ocupação, enfermarias, salas, macas e fila de espera |
| POST | `/api/importacoes` | Importa um CSV/Excel (campo `arquivo`) e devolve o resumo com os problemas |
| GET | `/api/importacoes/ultima` | Resumo da última importação |

## Protótipo hospedado (Render)

O protótipo para clientes roda no [Render](https://render.com), no plano gratuito, a partir do `Dockerfile` e do `render.yaml` na raiz. A API e as telas ficam **no mesmo endereço**.

**Publicar pela primeira vez:** render.com → **New → Blueprint** → escolher este repositório → informar a `GESTAR_SENHA_DEMO` quando o Render pedir. A `GESTAR_SECRET_KEY` é gerada sozinha.
Se o repositório não aparecer na lista, quem é dona dele no GitHub precisa autorizar o app do Render para este repositório.

**Atualizar:** cada merge na `main` publica a nova versão sozinho (leva alguns minutos).

| Variável (no Render) | Para quê |
|---|---|
| `GESTAR_SENHA_DEMO` | Senha dos usuários `enfermagem`, `medico` e `gestao` no protótipo. **Não use a `gestar123`**: ela está neste README, que é público |
| `GESTAR_SECRET_KEY` | Assina os tokens de login. Gerada pelo Render |

Como o protótipo se comporta:
- **Dados:** o banco nasce com os dados de demonstração a cada reinício. No plano gratuito o servidor "dorme" depois de 15 minutos sem acesso e apaga o disco, então tudo o que for feito lá **volta ao estado inicial**. Não envie planilhas com dados reais.
- **Primeiro acesso do dia:** pode levar até 1 minuto (o servidor está acordando).
- **Segurança:**
  - o servidor **não sobe** se a chave ou a senha forem as padrão do repositório;
  - 8 senhas erradas seguidas bloqueiam aquele IP por 15 minutos;
  - a planilha enviada pode ter no máximo 5 MB;
  - a documentação da API (`/docs`) e o guia de estilo (`/componentes`) ficam desligados;
  - o site não aparece em buscadores.

Testar a imagem no seu computador (precisa do Docker):
```bash
docker build -t gestar .
docker run --rm -p 8000:8000 -e GESTAR_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')" -e GESTAR_SENHA_DEMO="uma-senha-qualquer" gestar
# abra http://localhost:8000
```

**Tirar do ar:**
1. No Render, abra o serviço → **Settings → Delete Web Service**. O endereço para de funcionar na hora e o serviço some da conta.
2. No GitHub, em **Settings → Applications → Render → Configure**, remova o acesso ao repositório (ou desinstale o app).

## Problemas comuns

| Sintoma | Solução |
|---|---|
| `ModuleNotFoundError: app` ao rodar o pytest | Estar em `backend/` e usar `python -m pytest` |
| `ImportError: cannot import name 'importacoes' from 'app.routers'` | O arquivo `backend/app/routers/importacoes.py` não está nessa pasta. Confira se não ficou numa subpasta |
| `Form data requires "python-multipart"` | `pip install -r requirements-dev.txt` |
| `Failed to resolve import "react-router-dom"` | Dentro de `frontend/`: `npm install react-router-dom` |
| Volta sempre para a tela de login | O token venceu (12h) ou o banco foi recriado. Entre de novo |
| Painel diz "A API está rodando?" | Suba o backend (`uvicorn app.main:app --reload`) e confira http://localhost:8000/health |
| Erro de CORS no navegador | O frontend deve estar em `http://localhost:5173` (porta padrão do Vite) |
| Tela vazia depois de mudar o `models.py` | `python -m app.seed --recriar` |
| `no such table` | Rode `python -m app.seed` dentro de `backend/` |

## Fluxo de trabalho (Git)

- Nunca commitar direto na `main`. Criar uma branch por tarefa: `feat/G-XX-descricao-curta`.
- Commits no formato `feat:`, `fix:` ou `docs:`. Exemplo: `feat: importa planilha CSV/Excel (G-10)`.
- Abrir Pull Request, ter revisão de outra pessoa da equipe e fazer **squash merge**.
- O `.env`, o `gestar.db`, o `.venv/` e o `node_modules/` ficam no `.gitignore`.

## Limites do MVP

- Só dados simulados. Nenhum dado real de paciente deve entrar no repositório.
- Banco SQLite. O protótipo hospedado (Render, plano gratuito) volta aos dados de demonstração a cada reinício; uma hospedagem com dados que persistem fica como evolução futura.
- A integração com o AGHU e a leitura automática da planilha do Teams (Microsoft Graph) são evoluções futuras. Hoje a entrada é por CSV/Excel.
- O perfil da paciente (gestante, puérpera, abortamento) é uma sugestão inferida do diagnóstico e deve ser validada pela equipe do setor.
- A planilha traz só a data de entrada, sem a hora. Por isso o tempo de espera aparece como "hora de entrada não informada" quando falta o horário.

## Equipe

Projeto acadêmico, equipe de 6 pessoas. Adrieli Queiroz, Lorena Cavalcanti, Letícia Uchoa, Camily Vitória, Ana Júlia Ferreira e Maria Eduarda Braga. 
ENTREGA MVP: 3 de dezembro de 2026;
Apresentação final do MVP: 7 de dezembro de 2026.