# Anexo de Testes — Modelo de rating da FEXERJ

**Rascunho 2 — 26/08/2026.** Documento em revisão com a FEXERJ; não é versão final.

As conferências que sustentam os números do modelo. São registros **fechados, com data e
escopo declarados**: não deixam de ser verdade com o tempo, viram histórico. É a seção 3
que justifica ter mantido o teto de 700 do fator K.

As regras estão no **Anexo Normativo**; a passagem do modelo antigo para este, no **Anexo
de Transição**.

---

## Sumário

- **1. Os parâmetros contra a lista da federação** — os cinco números adaptados da FIDE
  conferidos contra a lista de agosto de 2026
- **2. Validação contra dado oficial da FIDE** — o cálculo por partida conferido contra
  uma consulta pública de cálculo
- **3. Simulação sobre um ciclo real** — o modelo rodado sobre os 35 torneios de 2026

---

## 1. Os parâmetros contra a lista da federação

A tabela de parâmetros (Anexo Normativo, seção 2) foi conferida contra a lista da
federação de agosto de 2026 — `FEX2608`, **1.152 jogadores de 42 clubes, 868 deles com
rating** (coluna `Rtg_Nat`). É uma lista de Clássico: Rápido e Blitz ainda não têm
população.

Dos sete parâmetros, **cinco são adaptações numéricas, e as cinco são o mesmo movimento —
o limiar da FIDE, 200 pontos abaixo**. Esta seção pergunta se a população da federação
sustenta esse deslocamento, e responde pelos 868 com rating: limiar de rating não se afere
em quem não tem rating.

> A coluna FIDE é a do regulamento **de 2024** (B02, em vigor desde 01/03/2024), que é a
> base normativa declarada do modelo. Antes dela os números eram outros — o piso da FIDE
> era 1000, e os dois adversários fictícios não existiam. Comparar com o regulamento
> anterior daria conclusão diferente, e errada.

### 1.1 Como a lista se distribui

| Faixa de rating | Jogadores | % dos 868 |
|---|---:|---:|
| abaixo de 1200 | 29 | 3,3% |
| 1200 a 1399 | 116 | 13,4% |
| 1400 a 1599 | 230 | 26,5% |
| 1600 a 1799 | 224 | 25,8% |
| 1800 a 1999 | 166 | 19,1% |
| 2000 a 2199 | 74 | 8,5% |
| 2200 ou mais | 29 | 3,3% |

Mediana **1656,5** — são 868 ratings, e os dois centrais são 1656 e 1657. Quartis em 1474
e 1860. Menor rating 921, maior 2496.

### 1.2 Parâmetro a parâmetro

| Parâmetro | FIDE | FEXERJ | Na lista de agosto de 2026 |
|---|---:|---:|---|
| Rating dos adversários fictícios | 1800 | **1600** | 1600 fica 56,5 pontos abaixo da mediana; 1800 ficaria 143,5 acima dela |
| Rating mínimo | 1400 | **1200** | abaixo de 1200 estão 29 jogadores (3,3%); abaixo de 1400, **145 (16,7%)** |
| Rating inicial máximo | 2200 | **2000** | 103 jogadores (11,9%) têm 2000 ou mais; 29 (3,3%) têm 2200 ou mais |
| Rating que fixa K=10 | 2400 | **2200** | 29 jogadores (3,3%) alcançam 2200; 2400 é alcançado por **1** |
| Teto de rating para o K=40 de sub-18 | 2300 | **2100** | acima de 2100 estão 56 jogadores (6,5%); acima de 2300, 10 (1,2%) |

**Os adversários fictícios são o parâmetro que mais mexe em rating**, porque entram na
conta do primeiro rating de todo estreante (Anexo Normativo, seção 6.3): dois empates
contra um rating fixo puxam a estimativa na direção dele. Em 1800, esse ponto de atração
seria mais forte que **599 dos 868** jogadores com rating — 7 de cada 10 —, e todo
estreante seria puxado para um nível que quase não existe aqui. Em 1600 ele fica logo
abaixo do meio da lista, a 56,5 pontos da mediana. **A lista sustenta 1600.**

**O piso de 1400 da FIDE ficaria acima de um sexto da lista.** Abaixo de 1400 estão 145
jogadores; abaixo de 1200, 29. O piso é um alçapão (Anexo Normativo, seção 7): quem cai
abaixo dele volta a não-rated e refaz as 5 partidas para ter rating de novo.

**Os três limiares do alto da lista.** O teto do rating inicial, na mesma seção 6.3,
contém uma estimativa feita com 5 partidas: em 2000 ele já está acima de 88,1% da lista;
em 2200, uma estimativa de cinco partidas poderia estrear acima de 96,7% dela. O K=10 em
2400 alcançaria **um único jogador** da federação, contra 29 em 2200 — seria letra morta.
E o teto do K=40 de sub-18 marca onde o jogador jovem deixa de receber o fator acelerado:
em 2100 ficam acima dele 56 jogadores; em 2300, dez.

**Os dois parâmetros não adaptados.** O teto de 400 pontos vale sempre porque a exceção da
FIDE é para jogadores de 2650 ou mais, e o maior rating da lista é 2496 — ela não
alcançaria ninguém. As 5 partidas mínimas não são limiar de rating, e esta lista não tem o
que dizer sobre elas: quem as mede é a seção 3.

### 1.3 O que esta conferência não prova

Ela mede **onde está a população**, não se um rating em particular está certo. Diz que
cada limiar da FEXERJ cai onde há jogadores, e quanta gente o número da FIDE alcançaria em
lugar dele. Três limites, declarados:

- **É Clássico.** Os parâmetros valem igualmente para as três modalidades (Anexo
  Normativo, seção 1), e Rápido e Blitz nascem na escala do Clássico, porque é dela que o
  transpasse (seção 1.1) tira o rating de entrada. Isso é previsão, não medida: quando as
  duas tiverem população própria, a conferência se refaz sobre elas.
- **É uma fotografia.** Os parâmetros foram escolhidos para a federação de 2026. Se o
  nível da lista se deslocar, a conferência se refaz — é a mesma conta, sobre a lista
  daquele momento.
- **Não é a lista da seção 3.** Aquela é o cadastro inteiro, 2.385 registros; esta é a
  lista de agosto, e 1.129 dos seus 1.152 jogadores estão lá. Os números das duas não se
  comparam linha a linha.

---

## 2. Validação contra dado oficial da FIDE

O cálculo da seção 3 do Anexo Normativo foi conferido contra uma consulta pública de cálculo da FIDE
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

## 3. Simulação sobre um ciclo real

O modelo foi rodado sobre o último ciclo completo da federação: **35 torneios entre
25/01 e 07/06/2026**, todos de Clássico, com os 2.385 jogadores da lista e 480 deles
disputando partidas. Serve para sair da discussão teórica e ver o efeito das regras
sobre gente real.

**Conferência de base.** O mesmo ciclo foi reprocessado pelo modelo atual e as **35
listas de rating saíram idênticas** às publicadas pela federação. Toda diferença
apontada abaixo vem do modelo novo, não de uma leitura diferente dos arquivos.

### 3.1 Prontidão do cadastro

| Achado | Quantidade |
|---|---:|
| Data de nascimento ausente | 296 |
| Dessas, quantas mudam algum cálculo | **1** |
| Data de nascimento ilegível (número de série do Excel) | 2 |
| `Ord` de torneio duplicado | 0 |

A data de nascimento só muda o fator K de quem já tem 30 partidas ou mais, rating
abaixo de 2100 e nunca atingiu 2200 (Anexo Normativo, seção 5). Nesse recorte cai **um** jogador — que
é, justamente, um dos dois registros com data corrompida. **Duas células precisam ser
corrigidas antes do primeiro ciclo oficial**; o resto do cadastro pode ser completado
sem pressa.

### 3.2 O teto de 700 nunca agiu

| Bimestre | Torneios | Partidas por jogador (mediana) | Máximo | Com 18+ partidas |
|---|---:|---:|---:|---:|
| jan-fev | 4 | 5 | 11 | 0 |
| mar-abr | 16 | 5 | 16 | 0 |
| mai-jun | 15 | 5 | 25 | 3 |

As partidas contadas são as que entram no cálculo — as disputadas contra adversário com
rating —, que são o `n` do teto (Anexo Normativo, seção 5.1).

O teto começa a agir em 18 partidas sob K=40 e em 36 sob K=20. Os três jogadores que
passaram de 18 partidas já estavam em K=20. **Nenhum K foi reduzido pelo teto.**

### 3.3 Quanto o rating muda

347 jogadores terminam o semestre com rating nos dois modelos e podem ser comparados:

| Diferença | Jogadores | % |
|---|---:|---:|
| até 10 pontos | 163 | 47% |
| 11 a 25 | 85 | 24% |
| 26 a 50 | 54 | 16% |
| 51 a 100 | 25 | 7% |
| acima de 100 | 20 | 6% |

Mediana de **11 pontos**. **Não há viés de direção**: 172 sobem, 162 descem, 13
ficam iguais. As maiores mudanças concentram-se em rating baixo e recém-chegados,
onde ficam as regras aposentadas (Anexo de Transição, seção 3).

### 3.4 O que o modelo novo faz e o atual não fazia

Dos **480** jogadores que disputaram partidas, **347** terminam o semestre com rating e
**133** sem. **49** conquistaram o primeiro rating pela regra da seção 6 do Anexo
Normativo.

| Como entraram no ciclo | Jogadores | Terminam com rating | Sem rating |
|---|---:|---:|---:|
| Já com rating | 301 | 298 | 3 |
| Estreantes — sem rating e sem partidas | 162 | 41 | 121 |
| Sem rating, com partidas já acumuladas | 17 | 8 | 9 |

Dos **121 estreantes que terminam sem rating**, **37** têm partidas acumuladas rumo às 5 e
**84 não têm nenhuma**: o torneio que disputaram foi descartado, porque nele não pontuaram
contra adversário com rating. **Todos os 84 disputaram um único torneio.** Os **3** que
entraram com rating e terminam sem ele caíram abaixo do piso de 1200 (Anexo Normativo,
seção 7).

O descarte da seção 6.1 do Anexo Normativo foi acionado **71 vezes, sobre 68 jogadores**.
Este é o número com as duas decisões da FEXERJ de 20/08/2026 — descartam-se tantos
torneios quantos forem os zerados, e "zerar" é não pontuar contra adversário com rating.
No rascunho 1, sob as leituras anteriores — um único descarte, e "zerar" como não pontuar
de forma alguma —, eram 23. É a mudança de maior alcance desta rodada de revisão.

**Os 71 descartes cabem em 68 jogadores porque um deles teve quatro**, e esse caso merece
registro. O jogador entrou no ciclo com rating no piso, caiu abaixo dele no primeiro
bimestre e, refazendo o rating como estreante, disputou **quatro torneios sem pontuar
contra adversário com rating** — os quatro descartados. Termina o semestre sem rating e
sem nada acumulado rumo às 5 partidas, embora a contagem de partidas disputadas esteja
preservada (Anexo Normativo, seção 7). É a regra como está escrita: o piso devolve a
proteção do descarte, e ela vale enquanto o jogador não pontuar contra adversário com
rating. **Entre os estreantes isso não aconteceu** — nenhum dos 84 disputou mais de um
torneio. Aparece em quem refaz o rating.

Na conversão, **1.361** jogadores entram com rating, dos quais **60 no piso de 1200**.

### 3.5 Por que o bimestre roda de uma vez

Rodar os seis meses como **um período único**, em vez de três bimestres, muda o rating
final de **181 jogadores**, com diferença de até **52 pontos** — e, em dois deles, a
diferença é entre ter e não ter rating. Nenhum dos dois está errado — são períodos
diferentes. É a razão de o recorte precisar ser fixo e combinado de antemão (Anexo
Normativo, seção 4.1).
