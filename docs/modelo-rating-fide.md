# Modelo de rating FEXERJ — regras completas

**Versão 1.4 — 11/08/2026.**

Especificação do modelo de rating **por partida** da FEXERJ, aplicável às modalidades
Clássico, Rápido e Blitz. Alinhado ao Handbook FIDE B02, com as adaptações numéricas da
federação. Substitui o modelo por torneio descrito em
[`CALCULATOR.md`](../CALCULATOR.md).

- **Base normativa:** [FIDE Rating Regulations](https://handbook.fide.com/chapter/B022024)
  (vigente desde 01/03/2024, com emenda de 01/10/2025 em 8.3.1) e
  [FIDE Rapid and Blitz Rating Regulations](https://handbook.fide.com/chapter/B02RBRegulations2024).
- **Vigência prevista:** a partir da temporada de 2027 — 01/03/2027. Até lá, o modelo
  atual continua gerando a lista oficial.
- **Validação:** o cálculo da seção 3 foi conferido contra uma consulta oficial da FIDE
  (seção 10) e o modelo completo foi rodado sobre um ciclo real da federação (seção 13).

> Os pontos ainda em aberto estão na primeira seção. O restante do documento descreve o
> modelo como ele vale.

---

## Sumário

- **Pontos em aberto** — o que ainda depende de decisão
- **1. Modalidades** — Clássico, Rápido e Blitz; transpasse entre elas
- **2. Parâmetros** — os números da FIDE e as adaptações da FEXERJ
- **3. Cálculo para jogador já rated** — a conta, passo a passo
- **4. Período de cálculo** — o que é um período e como é delimitado
- **5. Fator K** — a tabela, o teto de 700 e a dependência da data de nascimento
- **6. Rating inicial de jogador não-rated** — as 5 partidas, o descarte, a janela de 26 meses
- **7. Piso de rating** — durante o cálculo e na conversão da lista atual
- **8. Tabela 8.1.2** — diferença de rating para probabilidade
- **9. Tabela 8.1.1** — percentual de pontos para diferença de rating
- **10. Validação contra dado oficial da FIDE**
- **11. O que muda nos arquivos** — jogadores, torneios e auditoria
- **12. O que deixa de existir** — as regras aposentadas
- **13. Simulação sobre um ciclo real** — o modelo rodado sobre os 35 torneios de 2026

---

## Pontos em aberto

Três pontos. Enquanto não houver decisão, o programa segue o que está descrito em cada
um.

### 1. Como a permanência do K=10 é guardada

O K de 10 é permanente (seção 5): uma vez atingidos 2.200, o fator não volta a subir,
mesmo que o rating caia. Para isso o programa precisa saber que a marca foi atingida, o
que o rating atual sozinho não diz.

**A proposta da federação** foi dispensar um campo e usar o próprio K gravado no
arquivo, testando `K = 10`. Funciona, mas muda a natureza da coluna: o K deixa de ser
resultado e passa a ser entrada. Um `10` digitado por engano numa linha congela o fator
daquele jogador para sempre, e o programa não tem como distinguir isso de um K legítimo.

**Recomendação: um campo próprio por modalidade**, que o programa liga ao cruzar 2.200 e
nunca desliga, com o fator K continuando a ser recalculado a cada ciclo.

Sobre a dúvida anotada na versão 1.3 — *para que serve, então, uma coluna de K que não
alimenta o cálculo?* Para conferir. Ela mostra com que fator cada jogador foi calculado
naquele ciclo, que é o número que explica o tamanho da variação dele; sem a coluna,
descobrir isso exige refazer a regra da seção 5 à mão, jogador a jogador. É o mesmo papel
do rating publicado: é resultado, e é por ser resultado que serve de conferência. O que o
cálculo **precisa** guardar e não consegue deduzir é outra coisa — a permanência do K=10
—, e é ela que pede campo próprio.

**Este é o ponto que trava a implementação:** ele define as colunas do arquivo de
jogadores, e esse arquivo muda uma vez só (seção 11.1).

### 2. Se o rating FIDE é reconferido depois da entrada

O momento de captura está definido (§6.4, alínea d). Ficou em aberto o que acontece
**depois**: o rating FEXERJ de quem entrou pela FIDE deve ser reaproximado do rating FIDE
quando os dois divergirem além de alguma margem?

**Recomendação: não reaproximar.** Feita a entrada, aquele rating é da federação e evolui
pelas partidas disputadas aqui. As duas listas medem populações de adversários
diferentes, e divergir é o esperado, não um defeito. Reaproximar substituiria por um
número de fora o resultado de partidas já calculadas e publicadas, sem linha de auditoria
que explicasse a mudança.

Se ainda assim a federação quiser um gatilho, ele precisa ser regra escrita — margem,
periodicidade e o que acontece com a contagem de partidas —, e não correção manual caso a
caso, que é indistinguível de erro de digitação.

### 3. Como este documento se encaixa nos regimentos

O modelo atual está no Art. 68 do regimento. Falta definir a forma da substituição: o
artigo é reescrito para remeter a este documento, é revogado, ou este documento passa a
valer como regulamentação dele? Não muda cálculo nenhum, mas define como o documento é
citado e por quem é aprovado.

---

## 1. Modalidades

A FEXERJ passa a manter **três ratings independentes** por jogador:

| Modalidade | Sigla |
|---|---|
| Clássico | STD |
| Rápido | RPD |
| Blitz | BLZ |

Cada modalidade tem rating, contagem de partidas e histórico próprios. As regras
abaixo se aplicam **igualmente às três**, salvo onde indicado.

As adaptações numéricas da FEXERJ (seção 2) valem **igualmente para as três
modalidades**. A única divergência em relação ao texto da FIDE é o teto de
2400/2650, que a FEXERJ ignora — substituído por 2200 (seção 2) e pelo teto de 400
sempre aplicado.

### 1.1 Transpasse entre modalidades

Espelha o 7.2.1 do regulamento FIDE de Rápido/Blitz.

Jogador **sem rating** numa modalidade que **tenha rating STD** entra no cálculo
daquela modalidade usando o **rating STD** e é tratado como **rated** — não passa
pelo cálculo de rating inicial da seção 6.

O fator K do jogador transposto sai da contagem de partidas **da modalidade nova**,
que é zero — portanto **K=40**. Fatores K e contagens de partidas são independentes
por modalidade; só o rating inicial vem do STD.

Jogador que já tem rating FIDE naquela modalidade entra com ele, sem passar pelo
transpasse nem pelo cálculo de rating inicial — ver a seção 6.5.

---

## 2. Parâmetros — FIDE e adaptação FEXERJ

| Parâmetro | Seção FIDE | FIDE | **FEXERJ** |
|---|---|---:|---:|
| Rating mínimo (abaixo disso, jogador vira não-rated) | 7.2 | 1400 | **1200** |
| Rating dos adversários fictícios no rating inicial | 8.2.2 | 1800 | **1600** |
| Rating inicial máximo | 8.2.3 | 2200 | **2000** |
| Rating que fixa K=10 | 8.3.3 | 2400 | **2200** |
| Teto de rating para o K=40 de sub-18 | 8.3.3 | 2300 | **2100** |
| Teto da diferença de rating | 8.3.1 | 400 | **400, sempre** |
| Partidas mínimas para primeiro rating | 7.1.4 | 5 | **5** |

**Teto da diferença de rating: 400 pontos, sempre.** A exceção da FIDE para jogadores
com 2650 ou mais **não vale** na FEXERJ.

---

## 3. Cálculo para jogador já rated

Aplicado a cada partida **contra adversário rated**. Partidas contra não-rated
**não entram** no cálculo do jogador rated (8.3.1: *"for each game played against a
rated player"*).

### Passo 1 — diferença de rating, com teto

```
D = rating_do_jogador − rating_do_adversário
D = max(−400, min(400, D))
```

O teto é aplicado **ao rating do adversário**, antes de qualquer conta. A própria
FIDE exibe o adversário já limitado em suas páginas de cálculo.

### Passo 2 — probabilidade esperada

`PD` sai da **tabela 8.1.2** (seção 8 deste documento), pela diferença `D`.

- `D ≥ 0` (jogador é o de rating maior): usa a coluna **H**
- `D < 0`: usa a coluna **L** para `|D|`, que equivale a `1 − PD_H`

**Não usar a fórmula logística.** A tabela produz valores diferentes — a divergência
foi medida e está documentada na seção 10.

### Passo 3 — variação da partida

```
ΔR = resultado − PD          resultado ∈ {1, 0.5, 0}
```

### Passo 4 — variação do período

```
ΣΔR = soma de todos os ΔR do período
variação = ΣΔR × K
```

### Passo 5 — arredondamento

```
novo_rating = rating_inicial_do_período + arredonda(variação)
```

Arredonda para o inteiro mais próximo, **uma única vez por período** (8.3.4). O 0,5
arredonda **para longe do zero** (`+0,5 → +1`; `−0,5 → −1`).

---

## 4. Período de cálculo

**Todas as partidas do período são calculadas contra o rating do início do período.**
O rating não é atualizado entre torneios do mesmo período.

Isso vale também para o rating dos **adversários**: usa-se o do início do período.

> Verificado empiricamente numa consulta oficial da FIDE: um jogador disputou dois
> torneios no mesmo mês, com doze dias de intervalo, tendo ganho 11,40 pontos no
> primeiro. O segundo torneio foi calculado com o **mesmo** rating de partida do
> primeiro.

### 4.1 Como o período é delimitado

O período é **fixo: bimestral, com lista publicada em meses ímpares**. Isso substitui a
regra do modelo atual, em que o período era simplesmente o conjunto de torneios que o
operador escolhesse rodar numa execução.

**Consequência, com todas as letras: todos os torneios do bimestre entram numa
execução só.** Rodar torneio a torneio dentro do mesmo bimestre dá um resultado
diferente de rodar o bimestre inteiro de uma vez, porque o fator K (seção 5), o teto
de 700 (seção 5.1) e o arredondamento (seção 3, passo 5) são todos definidos **por
período** — fatiar a execução fatia os três junto. Não é preferência operacional: é
o que faz "por período" significar alguma coisa.

---

## 5. Fator K

| Condição | K |
|---|---:|
| Jogador novo na lista, até completar 30 partidas | 40 |
| Até o fim do ano em que completa 18 anos, com rating abaixo de **2100** | 40 |
| Rating abaixo de **2200** | 20 |
| Rating já atingiu **2200** em alguma lista publicada | 10 |

O K de 10 é **permanente**: uma vez que o rating publicado atinge 2200, o jogador
mantém K=10 mesmo que caia depois. Isso exige **persistir um indicador por
modalidade** de que o jogador já atingiu 2200 — não basta olhar o rating atual.

> *Perguntado pela diretoria: "não basta converter uma vez e só testar o K?"* Não
> basta, e o motivo é a própria permanência. Testando só o rating atual, um jogador
> que chegou a 2210 e caiu para 2150 voltaria a K=20, contrariando a regra. E converter
> uma única vez também não resolve, porque o indicador precisa ser ligado **toda vez**
> que alguém cruzar 2200 daqui para frente, não só na migração. Na prática é um campo
> por modalidade que o programa liga sozinho e nunca desliga — ninguém precisa
> preenchê-lo à mão.

Esse indicador **vence todas as outras condições** da tabela acima: nem a regra de
sub-18 nem a de jogador novo levantam o K de volta depois que ele chega a 10. O K é
um freio que só aperta, nunca afrouxa.

A única situação que parece contradizer isso não é exceção: um jogador que estreia
numa modalidade nova (seção 1.1) entra com K=40 mesmo já tendo K=10 na modalidade de
origem, porque o indicador de 2200 é guardado **por modalidade** — e naquela
modalidade ele não atingiu 2200 nenhuma vez. O freio existe por modalidade; a
modalidade nova começa sem ele.

O K é determinado **uma vez por período** e vale para todas as partidas dele, sem
exceção.

### 5.1 Teto de 700 (8.3.3)

Cláusula da FIDE, aplicada ao pé da letra: *"If the number of games (n) for a player
on any list for a rating period multiplied by K exceeds 700, then K shall be the
largest whole number such that K x n does not exceed 700."*

Um K, um n, o período inteiro: `n` é o número de partidas do jogador **no período** e
`K` é o fator único da seção 5. Se `n × K > 700`, `K` passa a ser o **maior inteiro**
tal que `K × n ≤ 700`.

**O teto é de 700, aplicado por período e não por torneio.** Sobre o
valor: rodado o ciclo real de 2026 (seção 13), **o teto não chegou a agir uma vez** —
a mediana foi de 4 a 5 partidas por jogador por bimestre e o máximo foi 26, contra as
18 partidas necessárias para o teto começar a morder sob K=40. Manter 700 é o valor da
própria FIDE e, no calendário real da federação, indiferente na prática. Aplicar o teto
torneio a torneio deixava o período total passar do limite por um múltiplo dele: um
jogador com 40 partidas sob K=40, em dois torneios de 20, chegaria a K=35 em cada
torneio (700 ÷ 20) — 1.400 no período, o dobro do teto. Com o teto sobre as 40
partidas do período inteiro, K vira 17 (40 × 17 = 680).

### 5.2 Dependência de data de nascimento

A regra de sub-18 exige a **data de nascimento**, hoje presente na coluna `Birthday`
do arquivo de jogadores mas **nunca usada** pelo cálculo. Passa a ser insumo com
efeito direto no rating, o que torna a qualidade desse dado relevante.

**A data de nascimento é dado obrigatório.** Nos torneios IRT e FEXERJ a informação já
está disponível pelo cadastro; a lacuna aparece nos internos. Não há comportamento padrão
para o caso ausente: o arquivo é recusado.

**Basta o ano.** O cálculo só usa o ano de nascimento, então os formatos que o cadastro
produz na prática — `00/00/AAAA`, comum nos IRT, e registros antigos que trazem apenas
`AAAA` — são aceitos como estão, sem precisar completar dia e mês.

Consequência de migração: a lista de jogadores atual aceita `Birthday` em branco, e o
validador passa a rejeitar. Isso se resolve na mesma conversão única que
adiciona as colunas de Rápido e Blitz (seção 11.1) — não exige passo separado, mas
exige que os cadastros estejam completos antes do primeiro ciclo no modelo novo.

---

## 6. Rating inicial de jogador não-rated

### 6.1 Quando o rating é calculado

Só quando o jogador acumular **pelo menos 5 partidas contra adversários rated**
(7.1.4). Até lá, os resultados ficam acumulados e nenhum rating é publicado.

Se o jogador **zerar seu primeiro torneio**, esse resultado é **descartado** do
cálculo do primeiro rating (8.2.1). Aqui, "evento" é o **torneio**, não o período: o
descarte olha o primeiro torneio isoladamente, mesmo que o jogador tenha pontuado em
outro torneio do mesmo período.

Duas precisões sobre o alcance do descarte:

- **"Zerar" é zerar o torneio inteiro**, não só as partidas contra adversários com
  rating. Um estreante num torneio cheio de não-rated pode enfrentar um único jogador
  com rating e perder, ganhando todo o resto: o torneio não foi zerado, e a derrota
  conta.
- **O descarte vale uma única vez, no primeiro torneio que o jogador disputa.** Se esse
  primeiro torneio foi descartado e ele zerar o seguinte, o seguinte conta normalmente.

As partidas do torneio descartado **não entram na contagem de partidas** do jogador: a
contagem registra as partidas válidas para cálculo de rating, e as desse torneio não
foram usadas em cálculo nenhum. Isso é diferente do que acontece no piso (seção 7), onde
o rating é zerado mas a contagem é inteiramente preservada.

### 6.2 Janela de 26 meses (7.1.4)

Passa a ser guardada a **data em que o acúmulo do jogador sem rating começou** — a
data do primeiro torneio que contribuiu partidas para o cálculo do primeiro rating
dele.

Cláusula da FIDE: *"Results from other tournaments played within consecutive rating
periods of not more than 26 months are pooled to obtain the initial rating."* (7.1.4)

É um limite de **janela**, não uma expiração partida a partida: as partidas
acumuladas não vencem uma a uma. O que se verifica, a cada período, é a distância
entre o período corrente e o período em que o acúmulo começou. Se essa distância
ultrapassar 26 meses, o acúmulo não pode mais ser agrupado — os resultados
anteriores saem do cálculo e o acúmulo do jogador recomeça do zero, a partir do
período corrente.

O que se perde é o **acúmulo** rumo ao primeiro rating. A **contagem de partidas
disputadas é preservada**: ela alimenta o fator K (seção 5).

O reinício do acúmulo **não devolve ao jogador o descarte** do primeiro torneio zerado
(seção 6.1). Esse descarte é contado por jogador, e não por acúmulo: uma vez usado, não
volta a valer, nem quando a janela expira, nem quando o jogador perde o rating pelo piso
(seção 7).

### 6.3 Fórmula

```
Ra = média dos ratings dos adversários rated,
     acrescida de dois adversários fictícios de rating 1600,
     contra os quais o resultado é considerado empate

p  = pontos obtidos ÷ partidas jogadas   (incluindo os dois empates fictícios)

dp = valor correspondente a p na tabela 8.1.1 (seção 9)

Ru = Ra + dp        arredondado para o inteiro mais próximo
Ru = min(Ru, 2000)  teto do rating inicial
```

Se `Ru` ficar abaixo de **1200**, o jogador permanece não-rated.

### 6.4 Jogador que já tem rating FIDE

Jogador que chega com rating FIDE numa modalidade **entra com esse rating**, sem passar
pelo cálculo do rating inicial. O rating é lançado pelo operador no cadastro; a contagem
de partidas na FEXERJ é tratada pelo programa e começa em zero.

- **Sem teto e sem conversão.** O teto de 2.000 da seção 6.3 existe para conter uma
  estimativa feita com poucas partidas; um rating FIDE não é estimativa, e vale pelo
  valor de face. O teto de 400 pontos por partida (seção 3) continua valendo e é o que
  limita o efeito de um rating muito acima da faixa da federação.
- **O fator K vem da faixa do rating** (seção 5), não da contagem de partidas na
  federação: quem entra com 2.300 recebe o K de quem tem 2.300, não o K=40 de jogador
  novo.
- **Rating de 2.200 ou mais liga o indicador permanente de K=10** naquela modalidade,
  como se o jogador tivesse atingido a marca numa lista da federação.
- **Quando o rating é registrado.** O rating FIDE é informado no cadastro **no momento
  da filiação** e **reconferido antes do primeiro uso**: na montagem da lista inicial e,
  depois dela, sempre que o jogador for entrar numa modalidade em que ainda tenha **zero
  partidas** na federação. Vale o valor da reconferência, não o guardado na filiação.

### 6.5 Jogador que recebe rating entre torneios (8.2.4)

Se um jogador não-rated receber rating publicado **antes** de um torneio dele ser
processado, ele é calculado **como rated**, com o rating atual — mas, no cálculo dos
**adversários** daquele torneio, continua contando como **não-rated**.

---

## 7. Piso de rating

O piso de 1200 aparece em dois momentos diferentes: durante o cálculo normal de um
jogador que já tem rating, e na conversão única da lista atual para o modelo novo.
São situações distintas.

### Durante o cálculo

Jogador cujo rating cair abaixo de **1200** passa a ser exibido como **não-rated** na
lista seguinte (7.2, adaptado).

**O rating é zerado; a contagem de partidas é preservada.** O jogador volta à
condição de não-rated e precisa das 5 partidas da seção 6 para ter rating publicado
de novo, mas seu histórico de partidas jogadas não é apagado — o que significa que,
ao voltar, o K vem da contagem preservada e não necessariamente de 40. *Confirmado
pela FEXERJ.*

> Esta é uma decisão da FEXERJ, não uma leitura do texto da FIDE. Conferimos: o
> regulamento FIDE é **silencioso** sobre o que acontece com a contagem de partidas e
> com o histórico de quem cai abaixo do mínimo, sobre como esse jogador recupera
> rating, e não tem seção de reintegração. A regra acima preenche uma lacuna, não
> contraria o original.

### Na conversão da lista atual

A conversão da lista atual para o formato do modelo novo levanta dois casos que a
regra acima — pensada para o cálculo corrente — não cobre, porque tratam de
registros que **já existem** na lista de hoje, não de um rating que caiu durante um
período. As duas regras:

- **Jogador com rating publicado e menos de 5 partidas: o rating é zerado**, e ele
  entra não-rated. A contagem de partidas é preservada "para registro", e as partidas
  já disputadas valem como acúmulo rumo às 5 que ele passa a precisar. Motivo: o
  modelo novo nunca produziria um rating com menos de 5 partidas (seção 6.1) — a lista
  convertida nasceria com números que o próprio modelo recusa. **256 jogadores** na
  lista atual.
- **Jogador com rating abaixo de 1200 e 5 partidas ou mais: sobe para o piso** e entra
  rated. Motivo: entrar não-rated o removeria da lista em silêncio, porque o cálculo do
  rating inicial raramente devolve alguém acima de 1200; entrando no piso, a saída — se
  vier — acontece pela regra desta seção, com linha de auditoria. **60 jogadores**.

Três fronteiras que as respostas não explicitavam, resolvidas assim:

- `Rtg_Nat = 0` **não é "abaixo de 1200"**: significa que a lista de origem não traz
  rating nenhum. Esses jogadores entram não-rated, e não sobem ao piso — subir daria
  rating aos 768 não-rated da lista de uma só vez.
- **"5 partidas ou mais"**, e não "mais de 5": cinco é o mínimo para ter rating
  (seção 6.1), então quem tem exatamente cinco fica do lado de quem pode ter rating.
- Quando os dois casos se aplicam ao mesmo jogador (abaixo do piso **e** com menos de
  5 partidas), vale o primeiro: ele entra não-rated.

**A conferência do operador na data de corte.** A lista de hoje não registra *quando*
cada rating foi obtido, e é isso que a janela de 26 meses (seção 6.2) precisaria saber.
A conferência é, por isso, do operador, e acontece uma única vez, na virada:

- Para cada jogador com **menos de 5 partidas**, verificar quando o rating foi obtido; se
  for anterior à janela, o rating é descartado e o jogador entra não-rated.
- Jogador **sem registro efetivo válido** — o que o cadastro chama de *grampo* — é
  descartado, seja por prazo vencido, seja por estar marcado com o **status 2**
  (seção 11.1).

---

## 8. Tabela 8.1.2 — diferença de rating (D) para probabilidade (PD)

`H` = jogador de rating **maior**. `L` = jogador de rating **menor** (`L = 1 − H`).

| D | H | L | D | H | L | D | H | L | D | H | L |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0-3 | .50 | .50 | 92-98 | .63 | .37 | 198-206 | .76 | .24 | 345-357 | .89 | .11 |
| 4-10 | .51 | .49 | 99-106 | .64 | .36 | 207-215 | .77 | .23 | 358-374 | .90 | .10 |
| 11-17 | .52 | .48 | 107-113 | .65 | .35 | 216-225 | .78 | .22 | 375-391 | .91 | .09 |
| 18-25 | .53 | .47 | 114-121 | .66 | .34 | 226-235 | .79 | .21 | 392-411 | .92 | .08 |
| 26-32 | .54 | .46 | 122-129 | .67 | .33 | 236-245 | .80 | .20 | 412-432 | .93 | .07 |
| 33-39 | .55 | .45 | 130-137 | .68 | .32 | 246-256 | .81 | .19 | 433-456 | .94 | .06 |
| 40-46 | .56 | .44 | 138-145 | .69 | .31 | 257-267 | .82 | .18 | 457-484 | .95 | .05 |
| 47-53 | .57 | .43 | 146-153 | .70 | .30 | 268-278 | .83 | .17 | 485-517 | .96 | .04 |
| 54-61 | .58 | .42 | 154-162 | .71 | .29 | 279-290 | .84 | .16 | 518-559 | .97 | .03 |
| 62-68 | .59 | .41 | 163-170 | .72 | .28 | 291-302 | .85 | .15 | 560-619 | .98 | .02 |
| 69-76 | .60 | .40 | 171-179 | .73 | .27 | 303-315 | .86 | .14 | 620-735 | .99 | .01 |
| 77-83 | .61 | .39 | 180-188 | .74 | .26 | 316-328 | .87 | .13 | > 735 | 1.0 | .00 |
| 84-91 | .62 | .38 | 189-197 | .75 | .25 | 329-344 | .88 | .12 |  |  |  |

Com o teto de 400 sempre aplicado, **as faixas acima de 411 são inalcançáveis
na FEXERJ** — ficam registradas por fidelidade ao original.

---

## 9. Tabela 8.1.1 — percentual de pontos (p) para diferença de rating (dp)

Usada apenas no **rating inicial** (seção 6).

| p | dp | p | dp | p | dp | p | dp |
|---|---|---|---|---|---|---|---|
| 1.0 | 800 | .74 | 184 | .48 | −14 | .22 | −220 |
| .99 | 677 | .73 | 175 | .47 | −21 | .21 | −230 |
| .98 | 589 | .72 | 166 | .46 | −29 | .20 | −240 |
| .97 | 538 | .71 | 158 | .45 | −36 | .19 | −251 |
| .96 | 501 | .70 | 149 | .44 | −43 | .18 | −262 |
| .95 | 470 | .69 | 141 | .43 | −50 | .17 | −273 |
| .94 | 444 | .68 | 133 | .42 | −57 | .16 | −284 |
| .93 | 422 | .67 | 125 | .41 | −65 | .15 | −296 |
| .92 | 401 | .66 | 117 | .40 | −72 | .14 | −309 |
| .91 | 383 | .65 | 110 | .39 | −80 | .13 | −322 |
| .90 | 366 | .64 | 102 | .38 | −87 | .12 | −336 |
| .89 | 351 | .63 | 95 | .37 | −95 | .11 | −351 |
| .88 | 336 | .62 | 87 | .36 | −102 | .10 | −366 |
| .87 | 322 | .61 | 80 | .35 | −110 | .09 | −383 |
| .86 | 309 | .60 | 72 | .34 | −117 | .08 | −401 |
| .85 | 296 | .59 | 65 | .33 | −125 | .07 | −422 |
| .84 | 284 | .58 | 57 | .32 | −133 | .06 | −444 |
| .83 | 273 | .57 | 50 | .31 | −141 | .05 | −470 |
| .82 | 262 | .56 | 43 | .30 | −149 | .04 | −501 |
| .81 | 251 | .55 | 36 | .29 | −158 | .03 | −538 |
| .80 | 240 | .54 | 29 | .28 | −166 | .02 | −589 |
| .79 | 230 | .53 | 21 | .27 | −175 | .01 | −677 |
| .78 | 220 | .52 | 14 | .26 | −184 | .00 | −800 |
| .77 | 211 | .51 | 7 | .25 | −193 |  |  |
| .76 | 202 | .50 | 0 | .24 | −202 |  |  |
| .75 | 193 | .49 | −7 | .23 | −211 |  |  |

A tabela é antissimétrica: `dp(p) = −dp(1−p)`.

---

## 10. Validação contra dado oficial da FIDE

O cálculo da seção 3 foi conferido contra uma consulta pública de cálculo da FIDE
(lista de agosto de 2026, modalidade Clássico, um jogador com dois torneios no
período). **As 13 partidas conferem individualmente** e a soma reproduz exatamente a
variação publicada de 19,60.

A mesma conferência mostrou por que a tabela não pode ser trocada pela fórmula
logística — **7 das 13 partidas divergem**:

| D | esperado pela fórmula | ΔR pela fórmula | ΔR pela tabela (FIDE) |
|---:|---:|---:|---:|
| 400 | 0,9091 | 0,0909 | **0,08** |
| 367 | 0,8921 | 0,1079 | **0,10** |
| 46 | 0,5658 | 0,4342 | **0,44** |

No período, a fórmula daria 20,36 contra os 19,60 publicados — **0,76 ponto de
diferença** para um jogador em um mês.

---

## 11. O que muda nos arquivos

### 11.1 Lista de jogadores

Identidade única por jogador, com rating, contagem de partidas e indicador de
"já atingiu 2200" **por modalidade**. O cabeçalho atual de 12 colunas cresce.

A conversão a partir do formato atual é direta: a coluna `Rtg_Nat` de hoje — que
apesar do nome guarda o **rating FEXERJ** — vira o rating **STD**; Rápido e Blitz
começam vazios, o que dispara o transpasse (seção 1.1) no primeiro torneio de cada
modalidade.

As colunas `SumOpponRating` e `TotalPoints`, que hoje sustentam a regra de rating
temporário, passam a servir apenas ao acúmulo de jogadores não-rated até as 5
partidas (seção 6.1). Ganha-se também a **data de início do acúmulo**, necessária
para a janela de 26 meses (seção 6.2).

**Continua sendo um arquivo só.** A recomendação técnica era
separar arquivo de trabalho e lista publicada; a diretoria optou pelo arquivo único,
com o **fator K** e o **status** do jogador incluídos.

**A coluna de fator K é saída.** O programa a reescreve a cada ciclo, calculando o K de
cada jogador a partir do rating, da contagem de partidas e da data de nascimento
(seção 5). Não é preciso avisar ninguém para não editá-la: uma edição manual não altera
o cálculo daquele ciclo e desaparece na primeira execução seguinte, sobrescrita pelo
valor calculado.

**Para que serve, então, uma coluna que o programa não lê:** para conferir. Ela mostra
com que fator cada jogador foi calculado naquele ciclo, que é o número que explica o
tamanho da variação dele. Sem ela, descobrir isso exige refazer a regra da seção 5 à mão,
jogador a jogador. É o mesmo papel do rating publicado — é resultado, e é por ser
resultado que serve de conferência.

Há um único dado que o cálculo **precisa** conhecer e não consegue deduzir do arquivo: a
permanência do K=10, isto é, que o jogador já atingiu 2.200 alguma vez, mesmo estando
abaixo disso agora. Como esse dado é guardado — em campo próprio, ou lido do próprio K —
é o ponto em aberto 1.

O **status** é cadastral, como o clube: o operador preenche, e ele não entra em cálculo
nenhum. Valores:

| Status | Significado |
|---|---|
| `1` | Ativo |
| `0` | Inativo |
| `2` | Grampo — registro sem lastro válido |
| `3` | Inativo, em outro estado ou no exterior |
| `4` | Falecido |

O status governa **publicação, não cálculo**. Um jogador falecido continua sendo
calculado e continua movimentando a contagem de partidas — apenas não aparece na lista
publicada. Por isso o programa não recusa um arquivo em que um jogador nessa condição
tenha partidas: a morte pode ocorrer no meio do ciclo, com torneios em andamento.

A única exceção é o status `2`, e ela vale uma vez só: na conversão da lista atual, o
registro marcado como grampo é descartado (seção 7). Passada a virada, um registro nessa
condição não deveria mais existir, e o status volta a ser apenas cadastral.

**"Id Anterior".** É um id de jogador **que já existe na lista** — a existência é
condição necessária —, apontando o registro que aquela pessoa tinha antes. Serve para
manter o histórico ligado sem publicar as duas linhas: o registro que traz um Id Anterior
tem status diferente de `1` e não é publicado. Hoje isso é controlado à mão pelo campo do
clube. É informação cadastral, preenchida pelo operador, e não um valor que o programa
calcule.

### 11.2 Lista de torneios

Ganha uma coluna de **modalidade** (STD/RPD/BLZ). A coluna `Type` existente é
**formato de disputa** (`SS`, `RR`, `ST`) e não ritmo de jogo — são coisas distintas.

A coluna `EndDate`, hoje opcional e nunca lida pelo cálculo, passa a ser **obrigatória
e precisa ser uma data legível**: é dela que saem o ano do período (regra de sub-18,
seção 5) e o mês (janela de 26 meses, seção 6.2). São aceitos os formatos
`AAAA-MM-DD`, `DD/MM/AAAA` e `DD.MM.AAAA` — o último é o que os arquivos da federação
usam hoje.

### 11.3 Arquivo de auditoria

Precisa identificar a modalidade e passa a ter forma **por partida**: as colunas
atuais (`Erm`, `Rm`, `Dif`, `Nwe`, `Dw`, `kDw`) descrevem agregados de torneio que
deixam de existir no modelo novo.

---

## 12. O que deixa de existir

| Regra atual | Situação |
|---|---|
| `RATING_PERFORMANCE` | Aposentada |
| `DOUBLE_K` | Aposentada |
| `TEMPORARY` (jogador com 1 a 14 partidas) | Substituída pelo rating inicial da seção 6 |
| Tabela de K por partidas na vida (30/25/15/10) | Substituída pela seção 5 |
| Expectativa pela **média** dos adversários do torneio | Substituída pelo cálculo por partida |
| Encadeamento torneio a torneio | Substituído pelo período da seção 4 |
| Piso de rating em 1 ponto | Substituído pelo piso de 1200 (seção 7) |

---

## 13. Simulação sobre um ciclo real

O modelo foi rodado sobre o último ciclo completo da federação: **35 torneios entre
25/01 e 07/06/2026**, todos de Clássico, com os 2.385 jogadores da lista e 480 deles
disputando partidas. Serve para sair da discussão teórica e ver o efeito das regras
sobre gente real.

**Conferência de base.** O mesmo ciclo foi reprocessado pelo modelo atual e as **35
listas de rating saíram idênticas** às publicadas pela federação. Toda diferença
apontada abaixo vem do modelo novo, não de uma leitura diferente dos arquivos.

### 14.1 Prontidão do cadastro

| Achado | Quantidade |
|---|---:|
| Data de nascimento ausente | 296 |
| Dessas, quantas mudam algum cálculo | **1** |
| Data de nascimento ilegível (número de série do Excel) | 2 |
| `Ord` de torneio duplicado | 0 |

A data de nascimento só muda o fator K de quem já tem 30 partidas ou mais, rating
abaixo de 2100 e nunca atingiu 2200 (seção 5). Nesse recorte cai **um** jogador — que
é, justamente, um dos dois registros com data corrompida. **Duas células precisam ser
corrigidas antes do primeiro ciclo oficial**; o resto do cadastro pode ser completado
sem pressa.

### 14.2 O teto de 700 nunca agiu

| Bimestre | Torneios | Partidas por jogador (mediana) | Máximo | Com 18+ partidas |
|---|---:|---:|---:|---:|
| jan-fev | 4 | 5 | 10 | 0 |
| mar-abr | 16 | 5 | 16 | 0 |
| mai-jun | 15 | 4 | 26 | 3 |

O teto começa a agir em 18 partidas sob K=40 e em 36 sob K=20. Os três jogadores que
passaram de 18 partidas já estavam em K=20. **Nenhum K foi reduzido pelo teto.**

### 14.3 Quanto o rating muda

348 jogadores terminam o semestre com rating nos dois modelos e podem ser comparados:

| Diferença | Jogadores | % |
|---|---:|---:|
| até 10 pontos | 163 | 47% |
| 11 a 25 | 85 | 24% |
| 26 a 50 | 53 | 15% |
| 51 a 100 | 25 | 7% |
| acima de 100 | 22 | 6% |

Mediana de **11,5 pontos**. **Não há viés de direção**: 173 sobem, 162 descem, 13
ficam iguais. As maiores mudanças concentram-se em rating baixo e recém-chegados,
onde ficam as regras aposentadas (seção 12).

### 14.4 O que o modelo novo faz e o atual não fazia

Somando os três bimestres: **50 jogadores** conquistaram o primeiro rating pela regra
da seção 6, **111** seguem acumulando rumo às 5 partidas, e o descarte do primeiro
torneio zerado (seção 6.1) foi acionado **23 vezes**. Na conversão, **1.361** jogadores
entram com rating, dos quais **60 no piso de 1200**.

### 14.5 Por que o bimestre roda de uma vez

Rodar os seis meses como **um período único**, em vez de três bimestres, muda o rating
final de **182 jogadores**, com diferença de até **75 pontos**. Nenhum dos dois está
errado — são períodos diferentes. É a razão de o recorte precisar ser fixo e combinado
de antemão (seção 4.1).
