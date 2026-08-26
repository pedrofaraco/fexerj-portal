# Contributing

## Development Environment

**Backend**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Leave `PORTAL_ENVIRONMENT` unset (or `development`) locally so the default `changeme` password in `.env` still works. **Do not** set `production` unless you use a real password of at least 8 characters — the app will not boot otherwise.

**Frontend**

```bash
cd frontend
npm install
```

## Running Tests

**Backend** (from repo root):

```bash
source .venv/bin/activate
pytest tests/
```

**Frontend** (from `frontend/`):

```bash
npm test
```

## Linting and Type Checking

**Backend** (from repo root):

```bash
source .venv/bin/activate
ruff check backend/ tests/
mypy backend/
```

**Frontend** (from `frontend/`):

```bash
npm run lint
npm run build
```

These same checks run automatically via GitHub Actions on pushes to `master`, `develop`, and matching `feature/**`, `fix/**`, `refactor/**`, and `chore/**` branches, and on pull requests targeting `master` or `develop` (Python lint/typecheck, shellcheck, and frontend lint, test, and production build).

## Falar com a FEXERJ

A federação responde por WhatsApp, em mensagens curtas e às vezes truncadas. Pedro é o
intermediário: o texto é escrito aqui, ele cola lá. Perguntas curtas, uma decisão por item.

**Toda mensagem é escrita em `.superpowers/sdd/fexerj/` antes de ser enviada, e é de lá
que Pedro copia.** Um arquivo por mensagem, `AAAA-MM-DD-enviado.md` ou `-recebido.md`,
**nunca editado depois de escrito**: se algo nele se revelar errado, o texto enviado fica
como está e a descoberta vai num bloco `CORREÇÃO POSTERIOR` datado, no fim. Cada arquivo
fecha com três seções — **números afirmados**, **compromissos assumidos**, **fica em
aberto** — e o `INDICE.md` da pasta carrega a tabela de perguntas sem resposta.

A pasta é git-ignored, por decisão do Pedro: mantém a correspondência da federação fora de
um repositório público, e um registro append-only quase não precisa de histórico do git,
porque nada é reescrito. **Esta seção é a parte versionada.** Se a pasta não existir num
clone, é porque ela não vem no clone — recrie-a e peça o histórico ao Pedro. **Não
reconstrua o que foi dito a partir de mensagem de commit e apresente como fala deles:**
reconstrução que depois vira citação é o mecanismo por trás das quatro regras que já foram
implementadas a partir de leitura errada.

Registrar não é tarefa para o fim da sessão. Número dito a eles vira número que eles têm:
quando um documento publica depois outro número para a mesma coisa, eles veem contradição
e nós não vemos nada. Foi o que quase aconteceu com o 84 e o 87 do anexo de testes.

## Branch Strategy

- `master` — production only; never commit directly
- `develop` — integration branch; all feature branches target this
- `feature/<name>`, `refactor/<name>`, `chore/<name>`, `fix/<name>` — one branch per task; merged into `develop` via PR

## Commit Messages

Use the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <short summary>
```

Common types: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`.

Examples:
- `feat(backend): add /validate endpoint`
- `fix(frontend): handle 401 on run response`
- `chore(scripts): make setup.sh idempotent`

Keep the summary under 72 characters. Use the body for context when needed.

## Pull Request Process

1. Branch off `develop` and make your changes.
2. Ensure all tests pass locally before opening a PR.
3. Open a PR targeting `develop`.
4. A passing CI run (Python and shell linting, type check, tests, and frontend lint/build) is required before merging.
5. Squash-merge into `develop`; the branch is deleted after merge.
6. Periodically, `develop` is merged into `master` to deploy to production.

