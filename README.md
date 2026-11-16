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
- Documentação interativa: http://localhost:8000/docs
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
| `python -m app.seed` | Cria o banco e popula com leitos, salas e 8 pacientes de demonstração |
| `python -m app.seed --sem-pacientes` | Só o catálogo (leitos, salas, macas). Ideal para demonstrar a importação |
| `python -m app.seed --recriar` | **Apaga tudo** e popula de novo |
| `python -m app.seed --recriar --sem-pacientes` | Apaga tudo e deixa só o catálogo |

Para zerar o banco manualmente, pare a API e apague o arquivo `backend/gestar.db`.

Não usamos migrações (Alembic). Quando o `models.py` mudar, recrie o banco com `--recriar`.

### Alterar a quantidade de leitos

No topo de `backend/app/seed.py`:

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

## API (resumo)

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Verifica se a API está no ar |
| GET | `/api/painel` | Ocupação, enfermarias, salas, macas e fila de espera |
| POST | `/api/importacoes` | Importa um CSV/Excel (campo `arquivo`) e devolve o resumo com os problemas |
| GET | `/api/importacoes/ultima` | Resumo da última importação |

## Problemas comuns

| Sintoma | Solução |
|---|---|
| `ModuleNotFoundError: app` ao rodar o pytest | Estar em `backend/` e usar `python -m pytest` |
| `ImportError: cannot import name 'importacoes' from 'app.routers'` | O arquivo `backend/app/routers/importacoes.py` não está nessa pasta. Confira se não ficou numa subpasta |
| `Form data requires "python-multipart"` | `pip install -r requirements-dev.txt` |
| `Failed to resolve import "react-router-dom"` | Dentro de `frontend/`: `npm install react-router-dom` |
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
- Banco SQLite local, sem deploy. A hospedagem fica como evolução futura.
- A integração com o AGHU e a leitura automática da planilha do Teams (Microsoft Graph) são evoluções futuras. Hoje a entrada é por CSV/Excel.
- O perfil da paciente (gestante, puérpera, abortamento) é uma sugestão inferida do diagnóstico e deve ser validada pela equipe do setor.
- A planilha traz só a data de entrada, sem a hora. Por isso o tempo de espera aparece como "hora de entrada não informada" quando falta o horário.

## Equipe

Projeto acadêmico, equipe de 6 pessoas. Adrieli Queiroz, Lorena Cavalcanti, Letícia Uchoa, Camily Vitória, Ana Júlia Ferreira e Maria Eduarda Braga. 
ENTREGA MVP: 3 de dezembro de 2026;
Apresentação final do MVP: 7 de dezembro de 2026.