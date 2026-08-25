# Anexo de Transição — Modelo de rating da FEXERJ

**Rascunho 2 — 13/08/2026.** Documento em revisão com a FEXERJ; não é versão final.

O que vale **uma única vez**, na passagem do modelo por torneio para o modelo por partida,
mais a descrição dos arquivos que o programa lê e escreve. Nada aqui é regra permanente do
modelo: essas estão no **Anexo Normativo**, e é a ele que se remete numa citação.

A separação segue um critério só: **o corpo normativo não pode conter nada que deixe de
ser verdade depois da virada.** Uma regra de conversão dentro de um texto normativo vira
letra morta que alguém cita em 2030.

---

## Sumário

- **1. Conversão da lista atual** — o que acontece com cada jogador na virada
- **2. Os arquivos** — lista de jogadores, lista de torneios, arquivo de auditoria
- **3. O que deixa de existir** — as regras aposentadas

---

## 1. Conversão da lista atual

Acontece uma única vez, na data de corte, e produz a primeira lista no formato da seção
2.1 a partir da lista de 12 colunas que a federação usa hoje.

### 1.1 Rating e piso

O piso de 1200 do modelo novo (seção 7 do Anexo Normativo) é escrito para um rating que
**cai durante um período**. A conversão levanta dois casos que ele não cobre, porque
tratam de registros que **já existem** na lista de hoje. As duas regras:

- **Jogador com rating publicado e menos de 5 partidas: o rating é zerado**, e ele
  entra não-rated. A contagem de partidas é preservada "para registro", e as partidas
  já disputadas valem como acúmulo rumo às 5 que ele passa a precisar. Motivo: o
  modelo novo não produz rating com menos de 5 partidas (Anexo Normativo, seção 6.1), e a lista
  convertida conteria números que o próprio modelo recusa. **256 jogadores** na lista
  atual.
- **Jogador com rating abaixo de 1200 e 5 partidas ou mais: sobe para o piso** e entra
  rated. Motivo: entrar não-rated o removeria da lista em silêncio, porque o cálculo do
  rating inicial raramente devolve alguém acima de 1200; entrando no piso, a saída — se
  vier — acontece pela regra do piso, com linha de auditoria. **60 jogadores**.

Três fronteiras que as respostas não explicitavam, resolvidas assim:

- `Rtg_Nat = 0` **não é "abaixo de 1200"**: significa que a lista de origem não traz
  rating nenhum. Esses jogadores entram não-rated, e não sobem ao piso — subir daria
  rating aos 768 não-rated da lista de uma só vez.
- **"5 partidas ou mais"**, e não "mais de 5": cinco é o mínimo para ter rating
  (Anexo Normativo, seção 6.1), então quem tem exatamente cinco fica do lado de quem pode ter rating.
- Quando os dois casos se aplicam ao mesmo jogador (abaixo do piso **e** com menos de
  5 partidas), vale o primeiro: ele entra não-rated.

**A conferência do operador na data de corte.** A lista de hoje não registra *quando*
cada rating foi obtido, e é isso que a janela de 26 meses (Anexo Normativo, seção 6.2) precisaria saber.
A conferência é, por isso, do operador, e acontece uma única vez, na virada:

- Para cada jogador com **menos de 5 partidas**, verificar quando o rating foi obtido; se
  for anterior à janela, o rating é descartado e o jogador entra não-rated.
- Registro de **grampo remanescente** — id temporário de não-federado, marcado com o
  **status 2** (seção 2.1) — é descartado quando o prazo dele já venceu sem que o
  jogador se federasse. O que se descarta é o registro vencido, não a figura do grampo,
  que segue em uso a cada ciclo.

---


### 1.2 Data de nascimento

A data de nascimento passa a ser exigida do jogador cujo fator K ela decide (seção 5.2 do
Anexo Normativo). Na lista atual, **298 jogadores** não têm data legível, mas o recorte da
seção 5.2 alcança **1** deles: os demais recebem o mesmo K com a data e sem ela.

A conversão, portanto, **não depende** de completar os 298 — depende de **uma** célula.
Completar o resto é trabalho de cadastro que vale por si, e pode acontecer depois da
virada, à medida que cada jogador entre no recorte ao completar 30 partidas.

Duas células da lista atual trazem número de série do Excel no lugar da data (ids 998 e
3000). A do id 3000 é justamente a única dentro do recorte.

---

## 2. Os arquivos

São três: a lista de jogadores, a lista de torneios e os arquivos de auditoria. Os dois
primeiros o operador entrega ao programa; os de auditoria o programa devolve.

A **lista de jogadores é estado**: o programa a reescreve inteira a cada execução, e ela
diz como cada jogador está no fim do último ciclo. Os **arquivos de auditoria são
eventos**: descrevem o que aconteceu numa execução, saem datados e não são reescritos. É
por isso que o registro de uma mudança pertence à auditoria, e não a uma coluna de
observações na lista.

### 2.1 Lista de jogadores

Identidade única por jogador e, **por modalidade**, rating, contagem de partidas, fator K,
marcador do primeiro torneio, data da última atividade, rating FIDE e o acúmulo da seção
6.1 do Anexo Normativo. O cabeçalho atual, de 12 colunas, passa a **42**.

**Continua sendo um arquivo só.** A recomendação técnica era separar arquivo de trabalho e
lista publicada; a diretoria optou pelo arquivo único, com o fator K e o status do jogador
incluídos.

O arquivo é **estado, não histórico**: ele diz como cada jogador está no fim do último
ciclo, e o programa o reescreve inteiro a cada execução. O que aconteceu num ciclo — uma
substituição de rating, por exemplo — é evento, e fica no arquivo de auditoria daquele
ciclo (seção 2.3), que é datado e não é reescrito.

#### As nove colunas de identidade

`Id_No;Id_CBX;Title;Name;ClubName;Birthday;Sex;Fed;Status`

A única nova é o `Status`, e ela é **cadastral**, como o clube: o operador preenche, o
programa preserva, e nenhum cálculo a lê. Governa **publicação, não cálculo**:

| Status | Significado |
|---|---|
| `1` | Ativo |
| `0` | Inativo |
| `2` | Grampo — id temporário de não-federado |
| `3` | Inativo, em outro estado ou no exterior |
| `4` | Falecido |

**Nenhum status interrompe cálculo.** Um jogador inativo, em outro estado ou falecido
continua sendo calculado e continua movimentando a contagem de partidas — apenas não
aparece na lista publicada. Por isso o programa **não recusa** um arquivo em que um
jogador nessa condição tenha partidas: a morte pode ocorrer no meio do ciclo, com torneios
em andamento.

**O status não filtra a saída do programa.** A lista que o ciclo escreve traz **todos** os
jogadores da lista de entrada, qualquer que seja o status, com o rating de cada um
atualizado. Retirar os que não são publicáveis é passo da **publicação**, feito pela
federação depois da execução — a lista de saída é o estado guardado até o ciclo seguinte,
não a lista publicada.

**O grampo é instrumento corrente, não sobra de cadastro.** É o id temporário que a
federação atribui a um jogador **não federado** para que ele possa disputar e ter rating
em evolução antes de se filiar; em geral vale por um ciclo de execução, e só a federação o
conhece. Para o cálculo ele é um jogador como qualquer outro — entra, joga, seu rating
evolui. O status `2` apenas o mantém fora da lista publicada, como todos os status
diferentes de `1`.

Grampos continuam a ser criados a cada ciclo. O que a conversão descarta (Anexo Normativo, seção 7) são os
registros de grampo **remanescentes na lista atual**, cujos ids temporários venceram sem
que o jogador se federasse — não a figura do grampo.

#### As onze colunas de cada modalidade

Três blocos iguais, com os sufixos `_Std`, `_Rpd` e `_Blz`:

`Rtg_;Games_;K_;FirstTrn_;LastPlayed_;RtgFide_;FideDate_;AccGames_;AccSumOpp_;AccPts_;AccSince_`

| Coluna | Preenche | O que é |
|---|---|---|
| `Rtg_` | programa | Rating na modalidade. **Vazio significa sem rating.** |
| `Games_` | programa | Partidas disputadas na vida, na modalidade. Alimenta o fator K (Anexo Normativo, seção 5) e é preservada quando o piso age (Anexo Normativo, seção 7). Não inclui as partidas do torneio descartado (Anexo Normativo, seção 6.1). |
| `K_` | programa | Fator K da seção 5 do Anexo Normativo — `10`, `20` ou `40` —, **e o registro de que o jogador já atingiu 2.200**. Ver a seção 5 do Anexo Normativo. |
| `FirstTrn_` | programa | `1` depois do primeiro torneio **aceito** — não zerado e com ao menos um adversário com rating. Enquanto está em `0`, o próximo torneio zerado é descartado (seção 6.1 do Anexo Normativo). Nunca volta a `0`. |
| `LastPlayed_` | programa | Período (`AAAA-MM`) em que o jogador teve partidas na modalidade pela última vez. Vazio se nunca teve. |
| `RtgFide_` | **operador** | Rating FIDE do jogador na modalidade (Anexo Normativo, seção 6.4). Vazio quando não há. De 1.200 ou mais. |
| `FideDate_` | **operador** | Data em que o `RtgFide_` foi conferido (Anexo Normativo, seção 6.4, alínea d). Obrigatória quando há rating FIDE, e só então. |
| `AccGames_` | programa | Partidas já somadas ao acúmulo da seção 6.1 do Anexo Normativo. Distinta de `Games_`. |
| `AccSumOpp_` | programa | Soma dos ratings dos adversários acumulada rumo ao primeiro rating. |
| `AccPts_` | programa | Pontos acumulados rumo ao primeiro rating. |
| `AccSince_` | programa | Período (`AAAA-MM`) em que o acúmulo corrente começou, para a janela de 26 meses (Anexo Normativo, seção 6.2). |

As colunas do programa são **reescritas a cada execução**, a partir do estado em que o
período termina: editá-las à mão não muda o resultado daquele ciclo e é sobrescrito no
seguinte. A exceção é `K_`, pelo motivo exposto na seção 5 do Anexo Normativo — é a única coluna em que uma
edição manual muda cálculo.

As quatro colunas `Acc` compartilham o prefixo e ficam lado a lado porque zeram juntas: no
instante em que o jogador ganha rating, e de novo se o piso o derrubar depois, já que o
acúmulo rumo ao próximo rating recomeça do zero e não da contagem vitalícia.

#### A conversão a partir do formato atual

É direta: a coluna `Rtg_Nat` de hoje — que apesar do nome guarda o **rating FEXERJ** —
vira o rating **STD**; Rápido e Blitz começam vazios, o que dispara o transpasse (seção
1.1) no primeiro torneio de cada modalidade.

As colunas `SumOpponRating` e `TotalPoints`, que hoje sustentam a regra de rating
temporário, passam a servir apenas ao acúmulo de jogadores não-rated até as 5 partidas
(Anexo Normativo, seção 6.1).

Três colunas novas não têm origem na lista atual e recebem valor de partida:

- `FirstTrn_` fica ligada para quem já tem partidas disputadas: no modelo antigo a
  contagem só avançava com resultados aproveitados, então quem tem partidas já teve um
  torneio aceito. Ligada de outro modo, todo jogador convertido voltaria a ter direito ao
  descarte da seção 6.1 do Anexo Normativo.
- `Status` entra como `1`: a lista atual não traz a coluna, e ela é do operador.
- `LastPlayed_`, `RtgFide_`, `FideDate_` e `AccSince_` entram vazias — a lista atual não
  registra quando cada jogador jogou pela última vez, nem quando um acúmulo começou.

### 2.2 Lista de torneios

Ganha uma coluna de **modalidade** (STD/RPD/BLZ). A coluna `Type` existente é
**formato de disputa** (`SS`, `RR`, `ST`) e não ritmo de jogo — são coisas distintas.

A coluna `EndDate`, hoje opcional e nunca lida pelo cálculo, passa a ser **obrigatória
e precisa ser uma data legível**: é dela que saem o ano do período (regra de sub-18,
seção 5 do Anexo Normativo) e o mês (janela de 26 meses, seção 6.2 do Anexo Normativo). São aceitos os formatos
`AAAA-MM-DD`, `DD/MM/AAAA` e `DD.MM.AAAA` — o último é o que os arquivos da federação
usam hoje.

### 2.3 Arquivo de auditoria

Precisa identificar a modalidade e passa a ter forma **por partida**: as colunas
atuais (`Erm`, `Rm`, `Dif`, `Nwe`, `Dw`, `kDw`) descrevem agregados de torneio que
deixam de existir no modelo novo.

A auditoria do período traz ainda **três colunas para a substituição de rating** (seção
6.4 do Anexo Normativo) — o rating anterior, a origem do rating adotado e a data em que ele foi conferido
—, vazias em toda linha que não seja de substituição. Elas existem porque a substituição
acontece **antes** do cálculo: sem elas, a linha mostraria o rating novo como se sempre
tivesse sido aquele.

São três arquivos de auditoria por execução. `Audit_Games.csv` traz uma linha por
partida, de cada lado, para que qualquer jogador refaça a própria conta contra a tabela
8.1.2. `Audit_Period.csv` traz uma linha por jogador e modalidade, e mostra que a soma
fecha. `Audit_Checks.csv` não descreve cálculo nenhum: **aponta** as linhas do ciclo que
merecem olho humano, e sai vazio — só com o cabeçalho — quando não houve nenhuma.

| Aviso | Quando aparece | Por que não é erro |
|---|---|---|
| `K10_BELOW_2200` | Jogador com fator K de 10 e rating abaixo de 2.200, ou sem rating | É o estado de quem atingiu 2.200 e caiu depois. É também como apareceria um `10` digitado por engano, que congelaria o fator daquele jogador — e o programa não distingue os dois. |
| `CALCULATED_WHILE_DECEASED` | Partidas calculadas para jogador com status `4` | A morte pode ocorrer no meio do ciclo, com torneios em andamento: as partidas foram disputadas e são calculadas. O que depende de decisão é a publicação. |

O arquivo de auditoria é **saída, regerada a cada execução**, e é onde ficam os
**eventos** de um ciclo. A lista de jogadores é **estado**: diz como cada jogador está no
fim do último ciclo, e é reescrita inteira a cada execução. É por isso que o registro de
uma mudança pertence à auditoria, e não a uma coluna de observações na lista — texto
digitado numa coluna de estado ou some na execução seguinte, ou se acumula sem que
ninguém apague nem leia.

---

## 3. O que deixa de existir

| Regra atual | Situação |
|---|---|
| `RATING_PERFORMANCE` | Aposentada |
| `DOUBLE_K` | Aposentada |
| `TEMPORARY` (jogador com 1 a 14 partidas) | Substituída pelo rating inicial da seção 6 do Anexo Normativo |
| Tabela de K por partidas na vida (30/25/15/10) | Substituída pela seção 5 do Anexo Normativo |
| Expectativa pela **média** dos adversários do torneio | Substituída pelo cálculo por partida |
| Encadeamento torneio a torneio | Substituído pelo período da seção 4 do Anexo Normativo |
| Piso de rating em 1 ponto | Substituído pelo piso de 1200 (Anexo Normativo, seção 7) |

---
