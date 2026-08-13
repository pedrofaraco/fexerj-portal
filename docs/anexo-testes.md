# Anexo de Testes — Modelo de rating da FEXERJ

**Rascunho 1 — 13/08/2026.** Documento em revisão com a FEXERJ; não é versão final.

As conferências que sustentam os números do modelo. São registros **fechados, com data e
escopo declarados**: não deixam de ser verdade com o tempo, viram histórico. É a seção 2
que justifica ter mantido o teto de 700 do fator K.

As regras estão no **Anexo Normativo**; a passagem do modelo antigo para este, no **Anexo
de Transição**.

---

## Sumário

- **1. Validação contra dado oficial da FIDE** — o cálculo por partida conferido contra
  uma consulta pública de cálculo
- **2. Simulação sobre um ciclo real** — o modelo rodado sobre os 35 torneios de 2026

---

## 1. Validação contra dado oficial da FIDE

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

## 2. Simulação sobre um ciclo real

O modelo foi rodado sobre o último ciclo completo da federação: **35 torneios entre
25/01 e 07/06/2026**, todos de Clássico, com os 2.385 jogadores da lista e 480 deles
disputando partidas. Serve para sair da discussão teórica e ver o efeito das regras
sobre gente real.

**Conferência de base.** O mesmo ciclo foi reprocessado pelo modelo atual e as **35
listas de rating saíram idênticas** às publicadas pela federação. Toda diferença
apontada abaixo vem do modelo novo, não de uma leitura diferente dos arquivos.

### 2.1 Prontidão do cadastro

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

### 2.2 O teto de 700 nunca agiu

| Bimestre | Torneios | Partidas por jogador (mediana) | Máximo | Com 18+ partidas |
|---|---:|---:|---:|---:|
| jan-fev | 4 | 5 | 10 | 0 |
| mar-abr | 16 | 5 | 16 | 0 |
| mai-jun | 15 | 4 | 26 | 3 |

O teto começa a agir em 18 partidas sob K=40 e em 36 sob K=20. Os três jogadores que
passaram de 18 partidas já estavam em K=20. **Nenhum K foi reduzido pelo teto.**

### 2.3 Quanto o rating muda

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
onde ficam as regras aposentadas (Anexo de Transição, seção 3).

### 2.4 O que o modelo novo faz e o atual não fazia

Somando os três bimestres: **50 jogadores** conquistaram o primeiro rating pela regra
da seção 6 do Anexo Normativo, **111** seguem acumulando rumo às 5 partidas, e o descarte do primeiro
torneio zerado (Anexo Normativo, seção 6.1) foi acionado **23 vezes**. Na conversão, **1.361** jogadores
entram com rating, dos quais **60 no piso de 1200**.

### 2.5 Por que o bimestre roda de uma vez

Rodar os seis meses como **um período único**, em vez de três bimestres, muda o rating
final de **182 jogadores**, com diferença de até **75 pontos**. Nenhum dos dois está
errado — são períodos diferentes. É a razão de o recorte precisar ser fixo e combinado
de antemão (Anexo Normativo, seção 4.1).
