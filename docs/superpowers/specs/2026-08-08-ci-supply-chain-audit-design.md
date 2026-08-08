# CI: separar auditoria de runtime e de tooling

Data: 2026-08-08
Status: aprovado, pronto para plano de implementação

## Problema

O job `supply-chain-audit` falha em **todo** PR desde 2026-06-28. As 14 PRs abertas
(todas do Dependabot) estão bloqueadas há seis semanas, incluindo bumps de `fastapi`
e `uvicorn` que não têm relação nenhuma com a causa.

A causa é que `npm audit` roda sem threshold e sem separar dependências de runtime
das de desenvolvimento. Qualquer advisory em qualquer ponto da árvore transitiva
derruba o build inteiro. Hoje são 4 findings `high`, todos transitivos e todos sob
`devDependencies`:

| Pacote | Cadeia | Onde executa |
|---|---|---|
| `brace-expansion` | `eslint` → `minimatch` | lint |
| `postcss` | `vite` | build |
| `nanoid` | `vite` → `postcss` | build |
| `undici` | `jsdom` | ambiente de teste |

Nenhum deles entra no bundle servido ao navegador.

### Como chegamos aqui

O `CODE_REVIEW_2026-04-18.md` §7.1 recomendava `npm audit --audit-level=high` em modo
**advisory** (`continue-on-error: true`) para começar. O PR #101 implementou o job como
**bloqueante e sem threshold**, acompanhado de um `npm audit fix` que o deixou verde
naquele dia.

Esta é a segunda volta do mesmo ciclo. Rodar `npm audit fix` de novo sem mexer na
política apenas reinicia o relógio até o próximo advisory na árvore do `vite`/`eslint`/`jsdom`.

`--audit-level=high` sozinho também não resolveria: os 4 findings atuais **são** `high`.

## Decisão

Separar o que bloqueia merge do que apenas informa, nos dois ecossistemas.

O critério é **superfície de exposição real**, não severidade nominal. Vulnerabilidade
em dependência que chega ao usuário ou ao servidor bloqueia. Vulnerabilidade em
ferramenta de build exige que o atacante já tenha execução de código na máquina de
build — é risco real, mas de outra classe, e não justifica parar uma release.

## Mudanças

### 1. `.github/workflows/ci.yml` — npm

Substituir o passo único `npm audit` por dois. O passo `npm ci` anterior permanece
inalterado — ambos os passos de audit dependem dele:

```yaml
- name: npm ci                       # inalterado
  run: npm ci
  working-directory: frontend

- name: npm audit (runtime — blocking)
  run: npm audit --omit=dev
  working-directory: frontend

- name: npm audit (dev tooling — advisory)
  run: npm audit
  continue-on-error: true
  working-directory: frontend
```

Cobertura do passo bloqueante: `react`, `react-dom`, `jszip`, `prop-types` — os
quatro pacotes sob `dependencies` no `package.json`. O `--omit=dev` filtra a árvore
do lockfile; o `npm ci` continua instalando tudo, porque os outros jobs precisam.

### 2. `.github/workflows/ci.yml` — pip

O `pip-audit -r requirements-dev.txt` tem a mesma assimetria: bloqueia em
vulnerabilidade de `pytest`/`mypy`/`ruff`/`httpx`, que nunca chegam ao servidor.
Hoje está limpo, então não bloqueia nada — é armadilha adormecida, não incêndio.
Corrigir junto para o job ficar coerente:

```yaml
- name: pip-audit (runtime — blocking)
  run: |
    python -m pip install --upgrade pip pip-audit
    pip-audit -r requirements.txt

- name: pip-audit (dev tooling — advisory)
  run: pip-audit -r requirements-dev.txt
  continue-on-error: true
```

`requirements-dev.txt` inclui `-r requirements.txt`, então o passo advisory continua
sendo um superconjunto — nada sai de vista.

### 3. `frontend/package-lock.json`

Rodar `npm audit fix` para zerar os 4 findings atuais. Resultado do dry-run:

- **4 `change`** — `undici 7.28.0→7.29.0`, `postcss 8.5.15→8.5.26`,
  `nanoid 3.3.14→3.3.18`, `brace-expansion 5.0.6→5.0.9`. Todos patch e dentro do
  range semver existente: **`package.json` não é modificado**.
- **35 `add`** — binários opcionais de outras plataformas (`lightningcss-*`,
  `@tailwindcss/oxide-*`). Não é superfície de ataque nova; é o npm normalizando
  dependências opcionais por plataforma no lockfile. Colateral positivo: torna o
  `npm ci` do runner Linux mais reprodutível a partir de um lockfile gerado no macOS.

O diff do lockfile será grande por causa dos 35 `add`. **A descrição do PR precisa
explicar isso**, senão parece escopo escondido.

## Verificação

Nada é declarado pronto sem estes comandos rodando verde:

```bash
cd frontend && npm audit --omit=dev          # exit 0
cd frontend && npm ci && npm run lint && npm run test:coverage && npm run build
pytest tests/
```

Já verificado durante o design (baseline, antes de qualquer mudança):

- `npm audit --omit=dev` → `found 0 vulnerabilities`, exit 0
- `pip-audit -r requirements-dev.txt` → `No known vulnerabilities found`
- `pytest` → 292 passed, backend 96% / calculator 97%
- `vitest` → 150 passed em 11 arquivos
- `ruff` e `mypy` → limpos

**Critério de aceitação final:** o CI real fica verde num PR aberto contra `develop`.
Verde local não conta.

## Fora de escopo

- Drenar as 14 PRs abertas do Dependabot (trabalho seguinte, com risco próprio —
  `mypy 1.19 → 2.3` é major).
- Alterar `.github/dependabot.yml`.
- Qualquer mudança em `package.json`.

## Riscos

**O passo advisory sinaliza, não corrige.** Quem de fato remedia os findings de
tooling é o Dependabot, que já abre PR para esses pacotes. Se a fila do Dependabot
continuar parada, os findings de dev acumulam silenciosamente num check amarelo que
ninguém lê. Isso torna drenar a fila do Dependabot uma dependência real deste
trabalho, não um "nice to have" — deve ser a próxima leva.
