"""Converte a lista de 12 colunas na de 42, na virada para o modelo por partida.

    python3 scripts/converter-lista.py LISTA_ATUAL.csv LISTA_DE_2_ANOS_ANTES.csv AAAA-MM SAIDA.csv

Roda uma vez, na data de corte (Anexo de Transição, seção 1). A lista que sai é
a que entra no primeiro ciclo do modelo novo.

A segunda lista existe por uma regra só, a do jogador com rating publicado e
menos de 5 partidas (seção 1.1): o rating dele é zerado de qualquer jeito, e as
partidas já disputadas valem como acúmulo rumo às 5 se ele estiver ativo —
disputou partida nos 2 anos anteriores à virada. É comparando as duas listas
que se sabe: mudou a contagem de partidas, jogou no intervalo; não constava da
lista antiga, todas as partidas são do intervalo.

`AAAA-MM` é o período da virada. É dele que passam a contar os 26 meses do
acúmulo aproveitado (Anexo Normativo, seção 6.2).

O jogador inativo sai da conversão como sempre saiu: o programa descarta o
acúmulo sem data no primeiro período em que ele jogar.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from calculator.fide.ratinglist import (  # noqa: E402
    LEGACY_HEADER,
    carry_over_active_accumulations,
    read_rating_list,
    write_rating_list,
)


def main() -> None:
    if len(sys.argv) != 5 or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", sys.argv[3]):
        raise SystemExit(__doc__)
    current_path, earlier_path, period, out_path = sys.argv[1:]

    current = Path(current_path).read_text(encoding="utf-8-sig")
    if current.splitlines()[0].strip() != LEGACY_HEADER:
        raise SystemExit(f"{current_path}: não é a lista de 12 colunas — não há o que converter.")

    players = read_rating_list(current)
    carried = carry_over_active_accumulations(
        players, Path(earlier_path).read_text(encoding="utf-8-sig"), period
    )
    Path(out_path).write_text(write_rating_list(players, int(period[:4])), encoding="utf-8")
    print(f"{len(players)} jogadores convertidos para {out_path}")
    print(f"{len(carried)} com menos de 5 partidas estão ativos e aproveitam as partidas")


if __name__ == "__main__":
    main()
