# Modelo de rating FEXERJ — índice dos anexos

Vigência prevista a partir de 01/03/2027.

O modelo de rating **por partida** da FEXERJ está descrito em **três anexos**, gerados de
fontes próprias neste diretório. Este arquivo é só o índice: não vai à federação e não
tem `.docx`.

| Anexo | Rascunho | Fonte | O que contém |
|---|---|---|---|
| **Normativo** | 2 | [`anexo-normativo.md`](anexo-normativo.md) | As regras do modelo: modalidades e transpasse, parâmetros, cálculo por partida, período, fator K, rating inicial, rating vindo da FIDE, piso, e as duas tabelas da FIDE. |
| **Transição** | 2 | [`anexo-transicao.md`](anexo-transicao.md) | A conversão da lista atual, os formatos dos arquivos, e as regras do modelo antigo que são aposentadas. |
| **Testes** | 2 | [`anexo-testes.md`](anexo-testes.md) | Os parâmetros conferidos contra a lista da federação, a validação contra uma consulta oficial da FIDE e a simulação sobre o ciclo real de 2026. |

Os três nascem da **versão 1.5** do documento único, que é onde a numeração de versões
para: daqui em diante cada anexo é revisado com a federação por conta própria e leva o
**seu** rascunho. Numeração compartilhada faria o anexo de testes chegar ao rascunho 3 sem
ter mudado uma vírgula: ele ficou no 1 até 26/08/2026, quando ganhou a seção 1. Os três
estarem hoje no 2 é coincidência — o próximo a mudar sobe sozinho.

**O rascunho 1 dos três foi enviado à federação em 13/08/2026** e está em análise. Os
`.docx` daquele rascunho continuam neste diretório, gerados da fonte como ela estava
naquele momento: é o que permite responder ao que eles comentarem, que é sobre aquele
texto e não sobre este. O que mudou depois — a redação do aviso de K=10 no normativo, a
descrição dos arquivos de auditoria no de transição e a seção 1 nova no de testes — está
nos rascunhos 2, que **ainda não foram enviados**.

## O critério da divisão

**O anexo normativo não pode conter nada que deixe de ser verdade depois da virada.** É
a ele que se remete ao citar uma regra, e regra de conversão dentro de texto normativo
vira letra morta que alguém cita em 2030.

O anexo de transição é o oposto: quase tudo nele perde utilidade depois do primeiro ciclo
no modelo novo — exceto os formatos de arquivo, que ficam ali por serem técnicos, e não
matéria citável por artigo.

O anexo de testes não envelhece por outro motivo: são registros fechados, com data e
escopo declarados. Não deixam de ser verdade, viram histórico. É ele que justifica ter
mantido o teto de 700 do fator K.

## Como gerar os `.docx`

```
.venv/bin/python scripts/build-docx.py
```

Sem argumento, constrói os três. Com um caminho, constrói só aquele.

**O número do rascunho fica no nome do arquivo** —
`anexo-normativo-rascunho-1.docx` —, para que o arquivo que a federação abre diga qual
rascunho é. Ele sai de um lugar só: a linha `**Rascunho N — DD/MM/AAAA.**` no topo da
fonte. **Para revisar: mude a linha, rode o script.** O nome acompanha, e o rascunho
anterior continua onde estava, com o nome dele — que é o que permite responder "no
rascunho 2 a regra dizia outra coisa".

Os `.md` **não levam número no nome**: são a fonte versionada em git, e renomeá-los a cada
rodada quebraria histórico e ligações.

**Confira o resultado no Word, não no LibreOffice.** Os dois calculam tabela de formas
diferentes, e uma conferência no LibreOffice não vale como prova sobre o arquivo que a
federação abre — isso já custou duas rodadas de correção. O script escreve as larguras de
coluna direto no OOXML porque o importador de HTML do LibreOffice ignora o CSS e
dimensiona a tabela pelo conteúdo.

Dois defeitos que só apareceram na renderização, e que valem como lembrete de olhar o
arquivo antes de enviar: hífen não separável (U+2011) vira quadrado vazio na Calibri, e o
LibreOffice marca o documento inteiro como inglês.

## Histórico

| Versão | Data | O que mudou |
|---|---|---|
| 1.5 | 13/08/2026 | Divisão em três anexos. Formato da lista de jogadores fechado em 42 colunas; fator K passa a ser o registro do 2.200 permanente; marcador do descarte; rating vindo da FIDE, com entrada e substituição do rating parado no tempo. Sem pontos em aberto. |
| 1.4 | 11/08/2026 | Simulação sobre o ciclo real de 2026. |
| 1.3 | — | Voz de documento oficial: as regras passam a ser afirmadas, não atribuídas. |
| 1.2 | — | Respostas da federação à segunda rodada de pendências. |
| 1.1 | — | Primeira rodada de pendências enviada à federação. |

Os `.docx` das versões 1.1 e 1.2 estão versionados neste diretório: são o que cada versão
dizia quando foi enviada, que é a que uma decisão vai ser atribuída depois.
