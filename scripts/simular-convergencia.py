"""Quantas partidas um jogador com rating defasado leva para convergir.

    python3 scripts/simular-convergencia.py [--k 20 40] [--rodadas 6]
                                            [--adversarios 2000] [--alvo 2000]
                                            [--ratings 1200 1300 ...]
                                            [--pcts 50 60 70 ...]

Existe para responder às perguntas da federação sobre o gatilho de rating
defasado (ver a seção "A última rodada com a federação" no handover) sem que
ninguém precise refazer a conta à mão — ou, pior, lembrar dela.

O modelo é o do documento de regras, e não uma aproximação:

- probabilidade vinda da tabela 8.1.2, nunca da fórmula logística;
- teto de 400 pontos na diferença de rating, sempre;
- o K é aplicado **uma vez por período**, sobre a soma das variações — é por
  isso que torneios de 6 rodadas convergem mais devagar que os de 9, com o
  mesmo número de partidas;
- arredondamento uma vez por período.

Uma coluna sai como "—" quando o rating para de subir antes do alvo: com
aproveitamento igual à expectativa, o jogador já está no rating dele.
"""
import argparse
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from calculator.fide import rules  # noqa: E402
from calculator.fide.tables import pd_for_diff  # noqa: E402

LIMITE_PERIODOS = 300


def partidas_ate(inicio, taxa, k, alvo, rodadas, adversarios):
    """Partidas até o rating alcançar `alvo`, ou None se ele estacionar antes."""
    rating, jogos = inicio, 0
    for _ in range(LIMITE_PERIODOS):
        if rating >= alvo:
            return jogos
        pd = pd_for_diff(rules.capped_diff(rating, adversarios))
        soma = (Decimal(str(taxa)) * rodadas) - rodadas * pd
        novo = rating + rules.round_half_away_from_zero(soma * k)
        if novo <= rating:
            return None
        rating, jogos = novo, jogos + rodadas
    return None


def tabela(ratings, pcts, k, alvo, rodadas, adversarios):
    print(f"\nK={k}, torneios de {rodadas} rodadas, adversários de {adversarios}. "
          f"Partidas até chegar a {alvo} (torneios entre parênteses).\n")
    print(f"{'rating':>7} |" + "".join(f"{p:>5}% |" for p in pcts))
    print("-" * (9 + 8 * len(pcts)))
    for inicio in ratings:
        linha = f"{inicio:>7} |"
        for p in pcts:
            jogos = partidas_ate(inicio, p / 100, k, alvo - 10, rodadas, adversarios)
            linha += f" {jogos:>3} ({jogos // rodadas:>2}) |" if jogos else "   —    |"
        print(linha)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, nargs="+", default=[20, 40])
    ap.add_argument("--rodadas", type=int, default=6)
    ap.add_argument("--adversarios", type=int, default=2000)
    ap.add_argument("--alvo", type=int, default=2000)
    ap.add_argument("--ratings", type=int, nargs="+",
                    default=[1200, 1300, 1400, 1500, 1600, 1700, 1800])
    ap.add_argument("--pcts", type=int, nargs="+", default=[50, 60, 70, 80, 90, 100])
    args = ap.parse_args()
    for k in args.k:
        tabela(args.ratings, args.pcts, k, args.alvo, args.rodadas, args.adversarios)


if __name__ == "__main__":
    main()
