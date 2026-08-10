# Migração do calculator: modelo por torneio → modelo por partida (FIDE)

Data: 2026-08-09
Status: aprovado, pronto para plano de implementação

Regras do modelo: [`docs/modelo-rating-fide.md`](../../modelo-rating-fide.md) — fechada,
com as seis dúvidas respondidas pela FEXERJ. **Este documento não redecide nenhuma regra.**
Ele decide *como* implementar.

Modelo atual: [`CALCULATOR.md`](../../../CALCULATOR.md).

## Problema

A especificação do modelo por partida está pronta. O que faltava era o escopo da
implementação: se o modelo novo substitui o atual ou coexiste, onde ele é testado sem
inutilizar o UAT, o que acontece com as listas já publicadas, se as três modalidades
entram de uma vez, e o que muda no portal.

A barra é diferente da de uma feature comum. O calculator é a ferramenta **oficial** da
FEXERJ, substituiu um processo manual e tem anos de uso. O ativo é a confiança
acumulada, não o código. E o modelo novo **produz ratings diferentes dos atuais mesmo
com histórico idêntico** — isso é o objetivo, não um defeito, mas a federação vai
precisar comunicar.

## Decisões

| Pergunta | Decisão |
|---|---|
| Substituir, coexistir ou branch separada? | **Coexistir**, os dois motores escolhidos por execução, com o atual como padrão |
| Onde o modelo novo fica disponível? | **UAT e produção, não-padrão** nos dois |
| O que acontece com as listas publicadas? | **Nada** — corte na última lista publicada, histórico intocado |
| As três modalidades de uma vez? | **Formato com as três de uma vez**, rollout dirigido pelos torneios enviados |
| Como a federação enxerga a diferença? | **Modo comparar no portal**, gerando `Comparison.csv` e resumo na tela |

A coexistência é o que dissolve o problema de ambiente: o UAT continua servindo o
modelo atual como padrão, então o caminho para testar um hotfix de produção não
desaparece, e nenhum terceiro ambiente precisa existir.

O modelo atual tem data de aposentadoria a definir pela federação, não pelo código —
ver "O que fica em aberto".

---

## 1. Arquitetura

**O motor atual não é tocado. Nem o cálculo, nem a leitura, nem a escrita.**

Isso é possível porque cada modo alimenta o motor com o formato que ele já sabe ler:

| Modo | `players.csv` de entrada | Motor atual | Motor novo | Saída |
|---|---|---|---|---|
| Modelo atual | 12 colunas | roda como hoje | — | 12 colunas, como hoje |
| Modelo FIDE | 12 colunas **ou** formato novo | — | converte na leitura se vier 12 | formato novo |
| Comparar | 12 colunas | roda como hoje | converte na leitura | ambos + `Comparison.csv` |

Duas consequências que valem mais que a economia de esforço:

1. **A conversão da §11.1 deixa de ser um script de mão única.** Vira o caminho de
   compatibilidade do leitor novo, exercitado a cada execução até a federação passar a
   guardar o arquivo no formato novo. Um caminho de código exercitado toda hora é um
   caminho de código testado; um script de conversão rodado uma vez na vida não é.
2. **O modo comparar funciona sobre o arquivo que a federação já tem hoje.** Nada a
   preparar antes de ver a diferença entre os modelos.

O modo comparar tem duas restrições, ambas verificadas na validação (§4):

- **exige o `players.csv` de 12 colunas**, porque o motor atual só sabe ler esse
  formato e não será adaptado. Depois que a federação migrar o arquivo, comparar deixa
  de fazer sentido de qualquer forma — não há mais um "modelo atual" rodando;
- **exige que todos os torneios do período sejam STD.** O modelo atual não tem conceito
  de modalidade: mandar um torneio de Rápido para ele produz um número que não
  corresponde a nada, e comparar contra esse número seria inventar uma diferença.

### 1.1 Organização

- `calculator/` — motor atual, intocado.
- `calculator/fide/` — motor novo:
  - `tables.py` — tabelas 8.1.2 (D→PD) e 8.1.1 (p→dp). Puro, sem dependências. É onde
    mora a decisão da §3 de não usar a fórmula logística, e o lugar mais barato de
    provar que está certa.
  - `rules.py` — K (§5), teto de 400, arredondamento (§3.5), piso de 1200 (§7), rating
    inicial (§6). Funções puras.
  - `ratinglist.py` — lê os dois formatos de `players.csv`, escreve o novo.
  - `cycle.py` — o período: junta as partidas de todos os torneios, agrupa por jogador e
    modalidade, aplica `rules`, emite.
  - `audit.py` — os CSVs de auditoria.
- `calculator/compare.py` — recebe o resultado dos dois motores e emite o comparativo.
  Depende dos dois; nenhum depende dele.

O parser de binários (`calculator/tunx_parser.py`) serve aos dois motores sem mudança.

### 1.2 Alternativas descartadas

**Mover `calculator/` para `calculator/legacy/` sob um despachante comum.** Mais
simétrico, mas move de lugar o código que gera rating oficial e suja o `git blame`
dele. Ganho estético, custo real.

**Um motor só, parametrizado pelas regras.** Os dois modelos divergem na estrutura —
agregado por torneio contra soma por partida, encadeamento contra período — não em
constantes. Parametrizar daria um motor com dois caminhos internos e nenhum dos dois
legível.

---

## 2. Formatos de arquivo

### 2.1 `players.csv` — formato novo (23 colunas)

```
Id_No;Id_CBX;Title;Name;ClubName;Birthday;Sex;Fed;
Rtg_Std;Games_Std;Peak2200_Std;SumOpp_Std;Pts_Std;
Rtg_Rpd;Games_Rpd;Peak2200_Rpd;SumOpp_Rpd;Pts_Rpd;
Rtg_Blz;Games_Blz;Peak2200_Blz;SumOpp_Blz;Pts_Blz
```

Oito colunas de identidade, depois cinco por modalidade.

- **`Rtg_Nat` vira `Rtg_Std`.** A #205 já documentou que o nome mente — guarda o rating
  FEXERJ, não o nacional. Um formato novo é o momento de corrigir, e como a conversão é
  automática ninguém edita à mão.
- **Rating vazio = não-rated.** Não zero. Cobre os três casos de uma vez: Rápido e Blitz
  nascendo vazios, jogador que nunca teve rating, e jogador que caiu abaixo de 1200 pela
  §7 — nesse último a contagem em `Games_` fica preservada, que é o que a §7 manda.
- **`Peak2200_` é `0`/`1`.**
- **`SumOpp_` e `Pts_` por modalidade** — a §11.1 rebaixa essas duas ao acúmulo de
  não-rated até as 5 partidas, e esse acúmulo é por modalidade.

### 2.2 Conversão do formato de 12 colunas

Determinística, aplicada na leitura. Rápido e Blitz sempre nascem vazios — o que
dispara o transpasse da §1.1 no primeiro torneio de cada modalidade, o comportamento
desejado. `SumOpponRating` → `SumOpp_Std` e `TotalPoints` → `Pts_Std` sempre.

O Clássico depende do estado do jogador na lista de origem, e são três casos distintos —
copiar `Rtg_Nat` direto estaria errado em dois deles:

| Caso na lista de 12 colunas | `Rtg_Std` | `Games_Std` | `Peak2200_Std` |
|---|---|---|---|
| `TotalNumGames = 0` (não-rated hoje) | vazio | `0` | `0` |
| `TotalNumGames > 0` e `Rtg_Nat >= 1200` | `Rtg_Nat` | `TotalNumGames` | `1` se `Rtg_Nat >= 2200`, senão `0` |
| `TotalNumGames > 0` e `Rtg_Nat < 1200` | vazio | `TotalNumGames` | `0` |

O primeiro caso importa porque no formato atual um jogador sem rating ainda carrega um
número em `Rtg_Nat`; quem determina que ele é não-rated é `TotalNumGames = 0`
(`calculator/classes.py`, `complete_players_info`). Copiar o número o tornaria rated por
acidente.

O terceiro caso existe porque o modelo atual tem piso de 1 ponto e o novo tem piso de
1200 (§12 da spec), então a lista de origem pode conter jogadores entre 1 e 1199. A §7 é
aplicada na conversão, preservando a contagem de partidas — sem isso o modelo novo
começaria num estado que ele mesmo considera impossível.

Jogadores hoje na faixa "temporária" (1 a 14 partidas) entram como **rated** com o
rating publicado. A §12 aposenta a regra `TEMPORARY` para o cálculo daqui em diante; ela
não reclassifica quem já tem rating publicado. O corte toma a lista publicada pelo valor
de face.

### 2.3 `tournaments.csv` — uma coluna no fim

```
Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj;TimeControl
```

`TimeControl` ∈ {STD, RPD, BLZ}. Nome escolhido para não colidir com `Type`, que é
formato de disputa (SS/RR/ST) — a §11.2 insiste nessa distinção porque confundi-las
trocaria o ritmo de todos os torneios.

**No fim, não no meio**: o motor atual lê esse arquivo por posição
(`calculator/classes.py`, `Tournament.__init__`), então uma coluna no fim é inerte para
ele e uma no meio o quebraria.

### 2.4 Saídas — uma execução, um período, uma lista

A §4 força a mudança. Hoje saem `RatingList_after_<Ord>.csv` e
`Audit_of_Tournament_<Ord>.csv` por torneio. No modelo novo o período tem um rating
inicial e um arredondamento: **lista intermediária por torneio não é um resultado
válido**, é um número que não existe.

| Arquivo | Conteúdo |
|---|---|
| `RatingList.csv` | a lista final do período, formato novo |
| `Audit_Games.csv` | uma linha por partida: torneio, modalidade, jogador, adversário, rating do adversário já limitado, D, PD, resultado, ΔR |
| `Audit_Period.csv` | uma linha por jogador × modalidade: torneios do período, rating inicial, n, ΣΔR, K, variação bruta, variação arredondada, rating final, caminho aplicado |
| `Comparison.csv` | só no modo comparar: jogador, rating STD pelo modelo atual, rating STD pelo modelo novo, diferença |

As colunas atuais de auditoria (`Erm`, `Rm`, `Dif`, `Nwe`, `Dw`, `kDw`) descrevem
agregados de torneio que deixam de existir e não têm sucessor — não são traduzidas.

---

## 3. Fluxo de cálculo

1. **Congelar o estado inicial.** A §4 diz que o rating do jogador *e o do adversário*
   são os do início do período. O motor congela os ratings iniciais numa estrutura só de
   leitura e todo o cálculo lê dali; os resultados vão para outra estrutura, escrita só
   no fim. É a diferença estrutural com o motor atual, que reescreve a lista a cada
   torneio — e a razão de não dar para adaptar o atual.

2. **Achatar os torneios em partidas.** O parser já devolve `(snr_a, snr_b, score_a)`.
   Cada partida passa a carregar de onde veio: torneio, modalidade e se o torneio é
   interno (`IsIrt = 0` **e** `IsFexerj = 0`).

3. **Classificar cada jogador × modalidade** contra o estado congelado:
   - com rating na modalidade → **rated**;
   - sem rating na modalidade mas com rating STD → **transposto** (§1.1): entra com o
     rating STD, tratado como rated, K = 40 porque a contagem da modalidade nova é zero;
   - sem rating em lugar nenhum → **não-rated**, caminho da §6.

4. **Rated:** para cada partida contra adversário rated, teto de 400 aplicado ao
   adversário, `PD` pela tabela 8.1.2, `ΔR = resultado − PD`.

5. **K e variação do período.** A §3 passo 4 dá `variação = ΣΔR × K`. A exceção do
   torneio interno (§5.2) faz o K variar dentro do período, então a forma implementada é

   ```
   variação = Σ (ΔR_i × K_i)
   ```

   com `K_i` o K vigente no torneio de onde a partida veio. Reduz à fórmula da spec
   quando todas as partidas do período compartilham o mesmo K.

6. **Teto de 700 (§5.1) — ponto aberto.** Fica numa função isolada, com a proposta da
   §5.1 implementada (por torneio, com o K e a contagem daquele torneio) e o ponto aberto
   registrado no docstring. Quando a FEXERJ responder, muda ali e em nenhum outro lugar.

7. **Arredondamento — armadilha conhecida.** O `round()` do Python é bancário:
   `round(0.5)` dá `0` e `round(2.5)` dá `2`. A §3.5 exige meio para longe do zero. O
   motor novo usa `Decimal(...).quantize(..., ROUND_HALF_UP)`. O motor atual usa
   `round()` em três pontos de `calculator/classes.py` — não são tocados, mas o motor
   novo não herda o hábito.

8. **Não-rated (§6):** acumula partidas contra rated; ao chegar a 5, calcula `Ru` com os
   dois adversários fictícios de 1600 empatados, teto de 2000, e abaixo de 1200 segue
   não-rated. Primeiro evento zerado é descartado (§6.1).

9. **Piso (§7):** quem termina abaixo de 1200 sai com rating vazio, `Games_` e
   `Peak2200_` preservados.

### 3.1 Leituras registradas

Pontos que a spec não decide e a implementação precisa. Nenhum bloqueia; todos ficam
aqui para a federação confirmar quando quiser.

- **O transposto conta como rated também para os adversários dele.** A §1.1 diz que ele
  "entra no cálculo daquela modalidade" e "é tratado como rated"; o cálculo dos
  adversários faz parte do cálculo daquela modalidade.
- **`Peak2200_` no corte sai do rating da lista de partida.** A lista de partida é uma
  lista publicada, então a §5 já responde: quem estiver com 2200 ou mais nela entra com
  o indicador ligado. Como é uma coluna do CSV, a federação pode ligar na mão quem tenha
  passado de 2200 e caído antes do corte.
- **Teto de 700 aplicado por torneio**, conforme a proposta da §5.1.
- **A §7 é aplicada na conversão do corte**, não só durante o cálculo: quem está entre 1
  e 1199 na lista de origem entra como não-rated com a contagem preservada (§2.2). A
  alternativa seria começar rated abaixo do piso e ser expulso no primeiro período, o
  que produziria uma lista inicial que o próprio modelo considera inválida.
- **O ano do período é o do `EndDate` mais recente entre os torneios do período.** A
  regra de sub-18 da §5 é "até o fim do ano em que completa 18 anos", o que exige saber
  a que ano o período pertence. O `EndDate` é hoje opcional no validador e **passa a ser
  obrigatório no modo FIDE**. Quando um período cruza a virada do ano, usar o ano mais
  recente é a leitura conservadora: o jogador que completou 18 no ano anterior sai do
  K=40 no período seguinte, não meio período depois.

---

## 4. Validação

O portão de formato continua no validador, antes de rodar
(`backend/validator.py` compara o cabeçalho por igualdade exata e exige 12 colunas).

- **Despacho por cabeçalho**: 12 colunas → formato legado; 23 → formato novo; qualquer
  outro → erro nomeando os dois aceitos.
- **`TimeControl`** obrigatório e dentro de {STD, RPD, BLZ} nos modos FIDE e comparar.
- **`Birthday` obrigatório no modo FIDE** (§5.3), opcional no modo atual.
- **`EndDate` obrigatório no modo FIDE**, hoje opcional. O fator K de sub-18 depende do
  ano do período, e o `EndDate` é a única fonte desse ano (§3.1).
- **No formato de 23 colunas**: cada `Rtg_` é inteiro ou vazio; `Games_` é inteiro não
  negativo; `Peak2200_` é `0` ou `1`; rating vazio com `Peak2200_ = 1` é aceito (jogador
  que atingiu 2200 e caiu abaixo do piso, §7).
- **No modo comparar**: `players.csv` tem de ser o de 12 colunas, e todo torneio do
  período tem de ser `TimeControl = STD`. As duas condições viram mensagem própria, não
  um erro genérico de formato — o operador precisa saber que a restrição é do modo, não
  do arquivo.

A consequência do último item é desejável: a mesma lista passa no modelo atual e é
recusada no modelo novo enquanto houver cadastro incompleto, e isso aparece na tela de
validação, antes de executar, não no meio de uma execução.

Erro em tempo de execução mantém o padrão de hoje: `ValueError` do motor vira 422 com
mensagem em português.

---

## 5. Portal

### 5.1 Seletor

Três opções no topo do formulário, antes dos uploads — antes porque o modo decide quais
regras de validação valem:

- **Modelo atual (oficial)** — padrão
- **Modelo FIDE**
- **Comparar os dois**

O modo acompanha `/validate` e `/run`, então a validação sempre corresponde ao que vai
rodar. **O seletor não é lembrado entre sessões**: volta para "Modelo atual" a cada
carregamento. Uma seleção esquecida é o modo de falha que interessa evitar.

### 5.2 Identificação da saída

O ZIP muda de nome por modo (`rating_cycle_output.zip`, `rating_cycle_fide.zip`,
`rating_cycle_comparison.zip`) e os arquivos do modelo novo ganham preâmbulo nomeando o
modelo, no mesmo padrão do `# audit_v1` de hoje.

Deliberadamente **não** existe um marcador "não oficial" controlado por flag: seria um
estado que alguém precisa lembrar de virar um dia, e não virar é a falha silenciosa. O
arquivo diz qual modelo o produziu, sempre. Se é oficial ou não é decisão da federação
numa data, não um booleano no código.

### 5.3 O risco de UX que importa

Hoje "Primeiro torneio" + "Quantidade" significa *rode estes N torneios em cadeia e me
dê N listas*. No modelo novo a mesma janela significa *este é o período* — uma lista, um
arredondamento, todas as partidas contra o rating inicial.

**Rodar cinco torneios de uma vez e rodar cinco vezes um torneio dão resultados
diferentes**, e os dois estão certos: são períodos diferentes. Um operador com o hábito
antigo tropeça aqui.

Duas defesas:

- o texto de apoio do intervalo muda no modo FIDE para dizer que o intervalo *é* o
  período de cálculo;
- o `Audit_Period.csv` nomeia os torneios que compuseram o período, para que a lista
  gerada nunca fique órfã do recorte que a produziu.

### 5.4 Tela de resultado

O resumo é montado a partir do ZIP (`frontend/src/resultParser.js`) e ganha um ramo por
forma de saída. No modo FIDE, o resumo é por modalidade presente no período. No modo
comparar é só de Clássico, pela restrição da §1: jogadores processados, quantos subiram,
quantos caíram, quantos ficaram iguais, maior variação para cada lado, e mediana da
variação absoluta.

A `HelpSection` passa a descrever as colunas novas e os três modos. CSS pelas classes
nomeadas de `frontend/src/index.css`, sem utilitário de cor do Tailwind — Chrome 109.

---

## 6. Testes

**Primeiro item do plano, antes de qualquer linha do motor novo: trancar o motor
atual.** Um teste de ouro que roda o ciclo atual sobre os binários que já existem em
`tests/binary/` e compara a saída com um arquivo gravado, caractere por caractere. O
motor não será tocado, mas o validador e o backend em volta dele mudam — e "não toquei"
é uma afirmação, enquanto o teste de ouro é evidência.

**A âncora de correção do motor novo é a consulta oficial da §10.** As 13 partidas com
`ΔR` individual e soma 19,60 viram fixture. É a única prova que não depende da leitura
que fizemos da spec: vem da própria FIDE.

| Alvo | Por que merece teste próprio |
|---|---|
| Fronteiras da tabela 8.1.2 | As faixas são intervalos fechados; `D=3` e `D=4` dão `PD` diferentes. Cada fronteira é onde um erro de `<` contra `<=` se esconde |
| Antissimetria da 8.1.1 | `dp(p) = −dp(1−p)` como propriedade sobre a tabela inteira |
| Arredondamento em ±0,5 | Exatamente onde o `round()` bancário morderia |
| K: faixas, sub-18, metade em interno, permanência do 10 | Cada linha da §5 muda rating de gente real |
| Teto de 700 | Está em aberto — o teste documenta a proposta implementada e falha alto se alguém mexer sem decidir |
| Piso de 1200, teto de 2000, transposto, primeiro evento zerado | Casos raros, e por isso os que ninguém repara quando quebram |
| Período: dois torneios juntos ≠ dois separados | A diferença estrutural entre os modelos |
| Conversão de 12 → 23 colunas | Caminho exercitado em toda execução até a federação migrar o arquivo |

Cobertura mantém o portão de 80% do RUNBOOK. Nomes de jogadores são placeholders
genéricos, seguindo o padrão de `tests/test_backend.py`.

---

## 7. Demonstrabilidade

Separado dos testes, e é o que a federação recebe. Testes provam para quem escreve o
código; a federação precisa de outra coisa.

1. O `Comparison.csv` sobre um ciclo real recente, com o resumo da tela.
2. Um documento curto derivado dele: quantos jogadores mudaram, para que lado, e os
   extremos explicados um a um — os extremos são os que geram telefonema.
3. O `Audit_Games.csv`, que é o argumento mais forte disponível: qualquer jogador pega
   as próprias partidas, abre a tabela 8.1.2 da spec e refaz a conta à mão. Isso troca
   "confie no programa" por "confira você mesmo", que é como a confiança acumulada
   sobrevive à troca de motor.

O documento diz explicitamente que **o modelo novo produz ratings diferentes com
histórico idêntico, e isso é o objetivo**. O comparativo existe para dimensionar a
diferença, não para minimizá-la.

---

## 8. O que fica em aberto

- **Teto de 700 quando o K varia dentro do período** (§5.1 da spec). Proposta
  registrada e implementada; aguarda um sim ou não da FEXERJ. Não bloqueia.
- **Data de aposentadoria do modelo atual.** A coexistência não é permanente, mas o
  momento da virada é decisão da federação. Enquanto o modelo atual for o padrão, ele é
  o oficial.
- **As três leituras registradas na §3.1**, que valem até a federação dizer o contrário.

## 9. Fora de escopo

- As 5 PRs do Dependabot abertas (#207–#211). A #209 (`jsdom` 29→30) e a #211
  (`@testing-library/jest-dom` 6→7) são major e mexem no ambiente de teste; trocar o
  chão dos testes durante a reescrita do motor de cálculo é procurar problema. A fila é
  drenada quando a migração estiver estável.
- Recálculo de histórico, em qualquer profundidade. O corte é na última lista publicada.
- Terceiro ambiente. A coexistência tornou desnecessário.
