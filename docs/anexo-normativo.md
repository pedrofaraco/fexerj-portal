# Anexo Normativo — Modelo de rating da FEXERJ

**Rascunho 2 — 13/08/2026.** Documento em revisão com a FEXERJ; não é versão final.
Vigência prevista a partir de 01/03/2027.

Regras do modelo de rating **por partida** da FEXERJ, aplicável às modalidades Clássico,
Rápido e Blitz. Alinhado ao Handbook FIDE B02, com as adaptações numéricas da federação.

- **Base normativa:** [FIDE Rating Regulations](https://handbook.fide.com/chapter/B022024)
  (vigente desde 01/03/2024, com emenda de 01/10/2025 em 8.3.1) e
  [FIDE Rapid and Blitz Rating Regulations](https://handbook.fide.com/chapter/B02RBRegulations2024).

> Este anexo contém **apenas o que permanece verdadeiro depois da virada**, e é a ele que
> se remete ao citar uma regra do modelo. O que vale uma única vez na passagem do modelo
> antigo para este — conversão da lista atual, formatos de arquivo, regras aposentadas —
> está no **Anexo de Transição**. As conferências que sustentam os números, com data e
> escopo declarados, estão no **Anexo de Testes**.

---

## Sumário

- **1. Modalidades** — Clássico, Rápido e Blitz; transpasse entre elas
- **2. Parâmetros** — os números da FIDE e as adaptações da FEXERJ
- **3. Cálculo para jogador já rated** — a conta, passo a passo
- **4. Período de cálculo** — o que é um período e como é delimitado
- **5. Fator K** — a tabela, o teto de 700 e a dependência da data de nascimento
- **6. Rating inicial de jogador não-rated** — as 5 partidas, o descarte, a janela de 26
  meses, o rating vindo da FIDE
- **7. Piso de rating**
- **8. Tabela 8.1.2** — diferença de rating para probabilidade
- **9. Tabela 8.1.1** — percentual de pontos para diferença de rating

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
transpasse nem pelo cálculo de rating inicial — ver a seção 6.4.

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
foi medida e está documentada na seção 1 do Anexo de Testes.

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

**Todos os torneios do bimestre são processados numa execução única.** O fator K
(seção 5), o teto de 700 (seção 5.1) e o arredondamento (seção 3, passo 5) são
definidos por período; processar torneio a torneio dentro do mesmo bimestre fraciona
os três e produz resultado diferente do bimestre processado de uma vez.

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

A condição de "já atingiu 2200" é registrada, e não deduzida do rating corrente: um
jogador que chegou a 2210 e caiu para 2150 mantém K=10, e o rating atual não distingue
esse caso de quem nunca passou de 2150. O registro é por modalidade e é atualizado pelo
programa sempre que o rating publicado cruzar 2200.

**O indicador é a própria coluna de fator K** da modalidade, `K_` (Anexo de Transição, seção 2.1): `K = 10`
é o registro de que a marca foi atingida. Não há campo separado. Três consequências, e
as três são regra:

- **O K gravado é o da seção 5, antes do teto de 700** (seção 5.1). O teto pode reduzir
  um K de 20 a 10 num período de muitas partidas, e um K assim reduzido, gravado no
  arquivo, marcaria como "atingiu 2200" quem nunca chegou perto. O fator com que cada
  partida foi efetivamente calculada fica no arquivo de auditoria.
- **O K gravado é o do estado em que o período termina**, não aquele com que o período
  foi calculado. Quem entra com 2.150 e termina com 2.210 precisa sair do ciclo com 10
  no arquivo; gravar o K de entrada perderia a permanência no mesmo ciclo em que ela foi
  conquistada.
- **Um `10` digitado por engano congela o fator daquele jogador.** É a contrapartida de
  dispensar o campo separado: nesta coluna, e só nela, uma edição manual muda resultado.
  O arquivo de auditoria assinala o caso — um K de 10 em jogador abaixo de 2.200 — para
  conferência do operador, sem recusar o arquivo: o mesmo estado aparece, legitimamente,
  em quem atingiu a marca e caiu depois.

Essa condição **prevalece sobre as demais** da tabela acima: nem a regra de sub-18 nem
a de jogador novo elevam o K depois que ele chega a 10.

O registro é **por modalidade**. Um jogador que estreia numa modalidade nova (seção 1.1)
entra nela com K=40 ainda que tenha K=10 na modalidade de origem, porque naquela
modalidade não atingiu 2200.

O K é determinado **uma vez por período** e vale para todas as partidas dele, sem
exceção.

### 5.1 Teto de 700 (8.3.3)

Cláusula da FIDE, aplicada ao pé da letra: *"If the number of games (n) for a player
on any list for a rating period multiplied by K exceeds 700, then K shall be the
largest whole number such that K x n does not exceed 700."*

Um K, um n, o período inteiro: `n` é o número de partidas do jogador **no período** e
`K` é o fator único da seção 5. Se `n × K > 700`, `K` passa a ser o **maior inteiro**
tal que `K × n ≤ 700`.

**O teto é de 700, aplicado por período e não por torneio.** Sobre o valor: no ciclo
real de 2026 (Anexo de Testes, seção 2) o teto não chegou a atuar — a mediana foi de 4 a 5 partidas por
jogador por bimestre, com máximo de 26, contra as 18 partidas necessárias para o teto
atuar sob K=40. O valor de 700 é o da própria FIDE.

Sobre o recorte: aplicado torneio a torneio, o total do período ultrapassaria o limite
por um múltiplo dele. Um jogador com 40 partidas sob K=40, em dois torneios de 20,
chegaria a K=35 em cada torneio (700 ÷ 20) — 1.400 no período, o dobro do teto. Com o
teto sobre as 40 partidas do período, K resulta em 17 (40 × 17 = 680).

### 5.2 Dependência de data de nascimento

A regra de sub-18 exige a **data de nascimento**, hoje presente na coluna `Birthday`
do arquivo de jogadores mas **nunca usada** pelo cálculo. Passa a ser insumo com
efeito direto no rating, o que torna a qualidade desse dado relevante.

**A data de nascimento é dado obrigatório para o jogador cujo fator K ela decide.** Não
há comportamento padrão para o caso ausente nesse recorte: o arquivo é recusado. Tratar a
data ausente como "não é sub-18" tiraria o K=40 de um jovem em silêncio, e ninguém
descobriria. Nos torneios IRT e FEXERJ a informação já está disponível pelo cadastro; a
lacuna aparece nos internos.

**Quem está nesse recorte.** A data é lida por uma regra só — o K=40 de sub-18 — e as
condições acima dela na seção 5 decidem antes. Ela só muda o resultado do jogador que, na
modalidade, cumpre as três ao mesmo tempo:

1. **não** tem o indicador permanente de K=10 — se tem, o K é 10 e a idade não altera;
2. tem **30 partidas ou mais**, ou tem rating FIDE registrado (seção 6.4), que dispensa a
   contagem — abaixo disso o K já é 40 pela regra de jogador novo, o mesmo 40 que a regra
   de sub-18 daria;
3. tem rating **abaixo de 2.100** — no teto ou acima dele a regra de sub-18 não alcança, e
   sem rating não há a que aplicá-la.

Fora desse recorte o arquivo é aceito sem a data, porque o fator K sai idêntico com ela e
sem ela. **Efeito medido na lista atual da federação:** a exigência recai sobre **1**
jogador dos 2.385, em vez dos 298 sem data legível — e é justamente o jogador que poderia
perder o K=40 que continua protegido. Preencher os demais é trabalho de cadastro que não
altera rating nenhum, e não precisa bloquear a execução de um ciclo.

O recorte é verificado a cada execução, não uma vez: um jogador fora dele hoje entra nele
ao completar 30 partidas, e aí a data passa a ser exigida dele.

**Basta o ano.** O cálculo só usa o ano de nascimento, então os formatos que o cadastro
produz na prática — `00/00/AAAA`, comum nos IRT, e registros antigos que trazem apenas
`AAAA` — são aceitos como estão, sem precisar completar dia e mês.

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

Disso decorre um registro próprio. Como o torneio descartado não movimenta a contagem, um
jogador descartado termina o período com a contagem em zero, indistinguível de quem nunca
jogou — e ganharia o descarte de novo no torneio seguinte, contra o "só o primeiro" acima.
A coluna `FirstTrn_` da modalidade (Anexo de Transição, seção 2.1) guarda que o primeiro torneio já foi
disputado. Ela é ligada pelo primeiro torneio em que o jogador enfrenta ao menos um
adversário com rating, tenha esse torneio sido descartado ou não, e **nunca é desligada**:
nem pela janela de 26 meses (seção 6.2), nem pelo piso (seção 7).

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
- **Essa regra de K vale enquanto houver rating FIDE registrado** na modalidade, e não
  apenas no período de entrada. No período seguinte o jogador ainda tem menos de 30
  partidas na federação, e a regra de jogador novo devolveria a ele exatamente o K=40 que
  a alínea anterior afasta. A regra de sub-18 continua valendo: ela depende da idade e do
  rating, não da contagem de partidas.
- **A entrada pelo rating FIDE ocorre uma vez, com zero partidas na modalidade.** Tendo o
  jogador qualquer partida disputada ali, o rating da federação é o dele e o rating FIDE
  registrado deixa de ser porta de entrada. Sem esse limite, um jogador que perdeu o
  rating pelo piso (seção 7) seria reinserido pelo rating FIDE a cada período, e o piso
  nunca produziria efeito sobre ele.
- **O rating FIDE registrado é de 1.200 ou mais**, o mesmo piso exigido do rating da
  federação (seção 7). Um valor abaixo do piso faria o jogador entrar rated abaixo dele,
  estado que o modelo não admite.
- **Rating de 2.200 ou mais liga o indicador permanente de K=10** naquela modalidade,
  como se o jogador tivesse atingido a marca numa lista da federação.
- **Quando o rating é registrado.** O rating FIDE é informado no cadastro **no momento
  da filiação** e **reconferido antes do primeiro uso**: na montagem da lista inicial e,
  depois dela, sempre que o jogador for entrar numa modalidade em que ainda tenha **zero
  partidas** na federação. Vale o valor da reconferência, não o guardado na filiação.
- **Substituição do rating local parado no tempo.** O rating da federação de um jogador é
  substituído pelo rating FIDE dele naquela modalidade quando as **três** condições
  valerem ao mesmo tempo, no início do período:

  1. o jogador tem rating da federação **abaixo de 1.600**;
  2. tem rating FIDE registrado de **2.000 ou mais**;
  3. está **há mais de 26 meses sem disputar partida** naquela modalidade.

  A substituição ocorre **antes do cálculo do período**: todas as partidas do período,
  do jogador e dos adversários dele, são calculadas contra o rating novo. A **contagem
  de partidas não é alterada** — nenhuma partida foi disputada que justificasse mexer
  nela. Um rating substituído de **2.200 ou mais liga o indicador permanente de K=10**,
  como qualquer rating FIDE que entra na lista.

  A substituição fica registrada no arquivo de auditoria do ciclo, com o rating
  anterior, a origem do valor adotado e a data em que ele foi conferido. Sem esse
  registro, a lista publicada mostraria um salto de centenas de pontos sem nada, em
  lugar nenhum, que o explicasse.

  **A regra vale outras vezes**, sempre que as três condições voltarem a se cumprir. Não
  há limite de uso e não é preciso registrar que ela já agiu: a própria substituição leva
  o rating a 2.000 ou mais e marca a atividade no período corrente, de modo que as
  condições 1 e 3 só podem voltar a valer depois de outra ausência longa **e** de uma
  queda de volta abaixo de 1.600 — que é justamente a situação em que ela deve agir de
  novo.

  **Por que só para quem parou.** Entre dois jogadores em atividade, uma diferença entre
  o rating da federação e o da FIDE não é defeito: as duas listas medem populações de
  adversários diferentes, e substituir uma pela outra importaria a escala da FIDE para um
  jogador só, deixando o resto da lista na escala da federação. Além disso, cada ponto do
  rating de um jogador ativo saiu de um adversário; substituí-lo injeta pontos que não
  vieram de partida nenhuma, e o adversário que os perdeu não os recebe de volta. Para
  quem parou há anos não existe essa objeção: não há medida local recente a descartar,
  porque não há medida local nenhuma.

  **A conferência do rating FIDE é do operador.** A regra parte do princípio de que o
  rating FIDE é o mais atual dos dois, e o programa não tem como verificar isso: a data
  que ele guarda é a da **conferência**, não a da obtenção do rating. Um jogador parado
  há 26 meses na federação pode ter parado também na FIDE, e a troca seria de um número
  velho por outro igualmente velho. Como a regra só age sobre rating FIDE que o operador
  tenha registrado, a proteção é dele: **não se registra rating FIDE tão parado quanto o
  da federação.**

### 6.5 Não há reaproximação periódica entre os dois ratings

Feita a entrada, o rating é da
federação e evolui pelas partidas disputadas aqui; divergir do rating FIDE é o esperado,
não um defeito, porque as duas listas medem populações de adversários diferentes. A única
troca prevista é a substituição do rating parado no tempo, na seção 6.4, e ela é regra
escrita, com condições fechadas e registro em auditoria — não correção caso a caso, que
seria indistinguível de erro de digitação.

### 6.6 Jogador que recebe rating entre torneios (8.2.4)

Se um jogador não-rated receber rating publicado **antes** de um torneio dele ser
processado, ele é calculado **como rated**, com o rating atual — mas, no cálculo dos
**adversários** daquele torneio, continua contando como **não-rated**.

---

## 7. Piso de rating

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

O piso alcança também os registros **já existentes** na lista de hoje, no momento da
conversão, e ali levanta casos que esta seção não cobre — ela trata de um rating que caiu
durante um período, não de um número herdado do modelo antigo. Esses casos estão na seção
1.1 do Anexo de Transição.

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
