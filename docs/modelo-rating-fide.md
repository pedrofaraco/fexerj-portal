# Modelo de rating FEXERJ — regras completas

Especificação do modelo **por partida**, alinhado ao Handbook FIDE B02 com as
adaptações do Art. 68 do regulamento da FEXERJ.

Substitui o modelo por torneio descrito em [`CALCULATOR.md`](../CALCULATOR.md).

- **Base normativa:** [FIDE Rating Regulations](https://handbook.fide.com/chapter/B022024)
  (vigente desde 01/03/2024, com emenda de 01/10/2025 em 8.3.1) e
  [FIDE Rapid and Blitz Rating Regulations](https://handbook.fide.com/chapter/B02RBRegulations2024).
- **Adaptações:** Art. 68 do regulamento FEXERJ.
- **Validação:** o cálculo descrito na seção 3 foi conferido contra uma consulta
  oficial da FIDE — 13 partidas, todas conferem, e a soma do período reproduz o valor
  publicado. Ver seção 10.

> Este documento tem **seis pontos em aberto** — ver "Decisões pendentes" logo
> abaixo. As regras já decididas estão marcadas *Confirmado pela FEXERJ* ou
> *Decidido pela FEXERJ* onde aparecem; o registro completo está na seção 13.

---

## Decisões pendentes

Seis perguntas fechadas, para a diretoria responder de uma vez. Esta seção é
**auto-contida** — basta lê-la para responder tudo. O resto do documento é
referência, para quem quiser conferir o raciocínio por trás de cada regra.

### A. O teto de 700 (partidas × K por período) muda com o bimestre?

Hoje o teto é 700 — o valor que a própria FIDE usa (seção 5.1). Com a lista
bimestral (decisão já tomada, seção 4.1), ele passa a agir a partir de 18 partidas
de um jogador com K=40 no bimestre; em lista mensal, quase nunca agia.

**Opções:** (1) manter 700; (2) adotar um valor pensado para o bimestre.

**Recomendação:** manter 700 — não acrescenta ao modelo um número que não vem de
fonte externa nenhuma.

**Se decidirem diferente:** o time técnico calcula o novo valor a partir da
distribuição real de partidas por jogador num ano de dados passados, para que o
número tenha origem verificável, e não seja uma estimativa.

### B. O descarte do primeiro torneio zerado tira partidas da contagem que alimenta o K?

A federação pediu que o descarte não altere "o número de partidas" do jogador. A
leitura adotada (seção 6.1): o torneio zerado sai do **cálculo do primeiro rating**,
mas as partidas continuam contando no total de partidas disputadas, que é o que
alimenta o fator K (seção 5). O jogador não perde as partidas do currículo — perde o
resultado na hora de calcular o primeiro rating.

**Opções:** (1) confirmar essa leitura; (2) as partidas do torneio descartado também
saem da contagem que alimenta o K.

**Recomendação:** confirmar (opção 1) — é a leitura mais literal de "sem alterar o
número de partidas".

**Se decidirem diferente:** um jogador que zerou o primeiro torneio entraria no
cálculo do fator K com menos partidas do que de fato disputou.

### C. Na conversão da lista atual, jogador com rating e menos de 5 partidas mantém o rating?

Hoje a conversão mantém o rating publicado pelo valor de face. O modelo novo nunca
produziria um rating com menos de 5 partidas (seção 6.1) — a lista convertida
nasceria com números que o próprio modelo, rodando do zero, recusaria.

**Opções:** (1) manter o rating desses jogadores na conversão; (2) zerar e tratá-los
como não-rated, sujeitos à regra do rating inicial (seção 6).

**Recomendação:** manter (opção 1). Esses jogadores entram com K=40 e o rating
converge para o valor real do jogo em um ou dois períodos.

**Se decidirem diferente:** vale levantar antes quantos jogadores estão nessa
situação — o impacto depende do volume.

### D. Na conversão, jogador com rating abaixo de 1200 e 5 partidas ou mais sobe para o piso?

A federação propôs subir esses jogadores para 1200 na conversão.

**Opções:** (1) subir para 1200, entrando rated; (2) não subir — o jogador entra
como não-rated no modelo novo.

**Recomendação:** opção 1. Não é gentileza: se ele virar não-rated na conversão, na
prática sai da lista de forma definitiva, porque o cálculo do rating inicial
raramente devolve alguém acima de 1200. Subindo para o piso, ele entra rated e, se de
fato jogar abaixo disso, cai no período seguinte pela regra normal (seção 7), com
linha de auditoria explicando a queda.

**Se decidirem diferente:** o destino prático é o mesmo — o jogador some da lista —
mas sem auditoria: a migração o remove em silêncio, em vez de a regra do modelo
mostrar o motivo.

### E. Arquivo de rating: um só, ou um de trabalho e uma lista publicada separada?

A federação pediu o fator K e o status do jogador nos arquivos. Os dois são
**derivados** — vêm do rating, da contagem de partidas e da data de nascimento, não
são dados independentes. O arquivo de rating hoje é entrada e saída do mesmo
programa: o que sai de um ciclo é o que entra no seguinte. Se o K estiver nesse
arquivo único, duas coisas ruins podem acontecer: o programa o ignora e recalcula
sempre — e o valor salvo é decoração que alguém vai editar achando que muda algo —
ou o programa confia nele, e um K editado à mão produz rating errado sem aviso.

**Opções:** (1) arquivo único, com K e status incluídos; (2) dois arquivos — um
**arquivo de trabalho** (o programa lê e escreve; guarda só o estado: rating,
contagem, data de nascimento, indicador de 2200) e uma **lista publicada**, para os
filiados, com rating, título, clube, partidas no período, fator K e status — o
conteúdo que a cláusula 7.1.2 da FIDE descreve para lista publicada (a própria FIDE
publica o valor corrente de K).

**Recomendação:** opção 2 — dois arquivos.

**Se decidirem diferente:** decidir antes qual dos dois problemas acima o programa
vai carregar.

### F. Quando o modelo atual se aposenta?

Os dois modelos coexistem, com o atual como padrão. A virada é decisão de calendário
da federação, não uma questão de engenharia.

**Opções:** escolher uma data de virada; ou manter o atual como padrão até nova
decisão.

**Recomendação:** nenhuma — é decisão de calendário da federação, não técnica.

**Se não decidirem agora:** o programa continua publicando pelo modelo atual por
padrão, sem prazo definido.

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

As adaptações numéricas do Art. 68 (seção 2) valem **igualmente para as três
modalidades**. A única divergência em relação ao texto da FIDE é o teto de
2400/2650, que a FEXERJ ignora — substituído por 2200 (seção 2) e pelo teto de 400
sempre aplicado (§3º). *Confirmado pela FEXERJ.*

### 1.1 Transpasse entre modalidades

Espelha o 7.2.1 do regulamento FIDE de Rápido/Blitz.

Jogador **sem rating** numa modalidade que **tenha rating STD** entra no cálculo
daquela modalidade usando o **rating STD** e é tratado como **rated** — não passa
pelo cálculo de rating inicial da seção 6.

O fator K do jogador transposto sai da contagem de partidas **da modalidade nova**,
que é zero — portanto **K=40**. Fatores K e contagens de partidas são independentes
por modalidade; só o rating inicial vem do STD. *Confirmado pela FEXERJ.*

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

**Art. 68 §2º** — revogado pela FEXERJ. Prescrevia reduzir o K pela metade em
**torneio interno** (aquele que não é IRT nem organizado pela federação — as duas
flags do arquivo de torneios, `IsIrt` e `IsFexerj`, desligadas). *Decidido pela
FEXERJ:* com o K único dentro do período (seção 5), as partidas entre jogador rated
e não-rated já fora do cálculo (seção 3) e o teto de 700 pontos mantido (seção 5.1),
a metade não protegia mais nada que esses três mecanismos já não protegessem. O
cálculo passa a ser uniforme, sem exceção por tipo de torneio. As duas flags
continuam existindo no arquivo de torneios — são elas que resolvem os identificadores
da CBX em torneio IRT — só o uso delas para reduzir o K desaparece.

**Art. 68 §3º** — o teto de 400 pontos **sempre** se aplica. A exceção da FIDE para
jogadores com 2650 ou mais **não vale** na FEXERJ.

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

O período passa a ser **fixo: bimestral, com lista publicada em meses ímpares**.
*Decidido pela FEXERJ.* Isso substitui a regra anterior, em que o período era
simplesmente o conjunto de torneios que o operador escolhesse rodar numa execução.

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

**O teto é por período, não por torneio.** *Decidido pela FEXERJ.* Aplicar o teto
torneio a torneio deixava o período total passar do limite por um múltiplo dele: um
jogador com 40 partidas sob K=40, em dois torneios de 20, chegaria a K=35 em cada
torneio (700 ÷ 20) — 1.400 no período, o dobro do teto. Com o teto sobre as 40
partidas do período inteiro, K vira 17 (40 × 17 = 680).

### 5.2 Dependência de data de nascimento

A regra de sub-18 exige a **data de nascimento**, hoje presente na coluna `Birthday`
do arquivo de jogadores mas **nunca usada** pelo cálculo. Passa a ser insumo com
efeito direto no rating, o que torna a qualidade desse dado relevante.

**A data de nascimento passa a ser dado obrigatório.** Nos torneios IRT e FEXERJ a
informação já está disponível pelo cadastro; a lacuna aparece nos internos. A decisão
da FEXERJ é exigi-la, em vez de adotar um comportamento padrão para o caso ausente.
*Confirmado pela FEXERJ.*

Consequência de migração: a lista de jogadores atual aceita `Birthday` em branco, e o
validador precisará passar a rejeitar. Isso se resolve na mesma conversão única que
adiciona as colunas de Rápido e Blitz (seção 11.1) — não exige passo separado, mas
exige que os cadastros estejam completos antes do primeiro ciclo no modelo novo.

---

## 6. Rating inicial de jogador não-rated

### 6.1 Quando o rating é calculado

Só quando o jogador acumular **pelo menos 5 partidas contra adversários rated**
(7.1.4). Até lá, os resultados ficam acumulados e nenhum rating é publicado.

Se o jogador **zerar seu primeiro torneio**, esse resultado é **descartado** do
cálculo do primeiro rating (8.2.1) — mesmo que ele tenha pontuado em outro torneio do
mesmo período. Aqui, "evento" é o **torneio**, não o período: o descarte olha o
primeiro torneio isoladamente. *Decidido pela FEXERJ.* Se essas partidas continuam
ou não contando para o fator K é a pendência B, no início deste documento.

### 6.2 Janela de 26 meses (7.1.4)

Passa a ser guardada a **data em que o acúmulo do jogador sem rating começou** — a
data do primeiro torneio que contribuiu partidas para o cálculo do primeiro rating
dele. *Decidido pela FEXERJ.*

Cláusula da FIDE: *"Results from other tournaments played within consecutive rating
periods of not more than 26 months are pooled to obtain the initial rating."* (7.1.4)

É um limite de **janela**, não uma expiração partida a partida: as partidas
acumuladas não vencem uma a uma. O que se verifica, a cada período, é a distância
entre o período corrente e o período em que o acúmulo começou. Se essa distância
ultrapassar 26 meses, o acúmulo não pode mais ser agrupado — os resultados
anteriores saem do cálculo e o acúmulo do jogador recomeça do zero, a partir do
período corrente.

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

### 6.4 Jogador que recebe rating entre torneios (8.2.4)

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
período:

- jogador com rating publicado e **menos de 5 partidas** — pendência C;
- jogador com rating **abaixo de 1200** e **5 partidas ou mais** — pendência D.

As duas estão na seção "Decisões pendentes", no início deste documento, e ainda não
têm resposta.

---

## 8. Tabela 8.1.2 — diferença de rating (D) para probabilidade (PD)

`H` = jogador de rating **maior**. `L` = jogador de rating **menor** (`L = 1 − H`).

| D | H | L | D | H | L | D | H | L | D | H | L |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0‑3 | .50 | .50 | 92‑98 | .63 | .37 | 198‑206 | .76 | .24 | 345‑357 | .89 | .11 |
| 4‑10 | .51 | .49 | 99‑106 | .64 | .36 | 207‑215 | .77 | .23 | 358‑374 | .90 | .10 |
| 11‑17 | .52 | .48 | 107‑113 | .65 | .35 | 216‑225 | .78 | .22 | 375‑391 | .91 | .09 |
| 18‑25 | .53 | .47 | 114‑121 | .66 | .34 | 226‑235 | .79 | .21 | 392‑411 | .92 | .08 |
| 26‑32 | .54 | .46 | 122‑129 | .67 | .33 | 236‑245 | .80 | .20 | 412‑432 | .93 | .07 |
| 33‑39 | .55 | .45 | 130‑137 | .68 | .32 | 246‑256 | .81 | .19 | 433‑456 | .94 | .06 |
| 40‑46 | .56 | .44 | 138‑145 | .69 | .31 | 257‑267 | .82 | .18 | 457‑484 | .95 | .05 |
| 47‑53 | .57 | .43 | 146‑153 | .70 | .30 | 268‑278 | .83 | .17 | 485‑517 | .96 | .04 |
| 54‑61 | .58 | .42 | 154‑162 | .71 | .29 | 279‑290 | .84 | .16 | 518‑559 | .97 | .03 |
| 62‑68 | .59 | .41 | 163‑170 | .72 | .28 | 291‑302 | .85 | .15 | 560‑619 | .98 | .02 |
| 69‑76 | .60 | .40 | 171‑179 | .73 | .27 | 303‑315 | .86 | .14 | 620‑735 | .99 | .01 |
| 77‑83 | .61 | .39 | 180‑188 | .74 | .26 | 316‑328 | .87 | .13 | > 735 | 1.0 | .00 |
| 84‑91 | .62 | .38 | 189‑197 | .75 | .25 | 329‑344 | .88 | .12 |  |  |  |

Com o teto de 400 sempre aplicado (§3º), **as faixas acima de 411 são inalcançáveis
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

Falta decidir se isso continua num arquivo só, ou se passa a ser um arquivo de
trabalho mais uma lista publicada separada — pendência E, no início deste documento.

### 11.2 Lista de torneios

Ganha uma coluna de **modalidade** (STD/RPD/BLZ). A coluna `Type` existente é
**formato de disputa** (`SS`, `RR`, `ST`) e não ritmo de jogo — são coisas distintas.

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

## 13. Decisões já tomadas

Registro das decisões que a FEXERJ já tomou e que este documento incorpora como
regra vigente. Não confundir com a seção "Decisões pendentes", no início — aquela
lista o que **ainda falta** responder; esta lista o que **já foi** respondido.

| Decisão | Regra | Seção |
|---|---|---|
| Art. 68 vale para as três modalidades? | Sim. Só diverge da FIDE no teto 2400/2650, ignorado | 1 |
| K do jogador transposto entre modalidades | Da modalidade nova — zero partidas, portanto K=40 | 1.1 |
| Metade do K em torneio interno (Art. 68 §2º) | Abolida — os outros três mecanismos do período já protegiam o mesmo risco | 2 |
| Teto de 700 (8.3.3) | Por período, não por torneio | 5.1 |
| K=10 | Permanente — nunca volta a subir, nem com sub-18, nem com modalidade nova (indicador é por modalidade) | 5 |
| Data de nascimento ausente | Passa a ser dado obrigatório | 5.2 |
| Período de cálculo | Fixo, bimestral, lista publicada em meses ímpares — o bimestre inteiro roda numa execução só | 4.1 |
| Descarte do primeiro torneio zerado | "Evento" é o torneio, não o período | 6.1 |
| Janela de acúmulo do rating inicial | 26 meses corridos a partir do início do acúmulo (7.1.4) | 6.2 |
| Cair abaixo de 1200 durante o cálculo | Zera o rating, preserva a contagem de partidas | 7 |

Seis pontos continuam em aberto — ver "Decisões pendentes" no início do documento.

---

## Aprovação

Ao assinar abaixo, a diretoria da FEXERJ declara que as regras descritas neste
documento foram aprovadas e as pendências da seção "Decisões pendentes" (A a F)
foram respondidas.

| Campo | |
|---|---|
| Data | ______________________ |
| Nome | ______________________ |
| Assinatura | ______________________ |
