"""Data structures for the per-game model.

`ModalityState` is frozen on purpose: §4 of the spec requires that the whole
period be calculated against the state at its start, and freezing it prevents
an intermediate calculation from leaking into another by mistake.
"""
from dataclasses import dataclass, field
from decimal import Decimal

MODALITIES: tuple[str, ...] = ("STD", "RPD", "BLZ")

# Column suffix for each modality in players.csv (spec §2.1).
COLUMN_SUFFIX: dict[str, str] = {"STD": "Std", "RPD": "Rpd", "BLZ": "Blz"}


@dataclass(frozen=True)
class ModalityState:
    """A player's rating, game count and accumulators in one modality.

    `games` and `accumulated_games` count different things and must not be
    confused: `games` is the lifetime game count — it only grows, it is what
    §5's K factor reads, and §7 preserves it when the floor drops the player
    out of rated status. `accumulated_games` is how many of those games have
    gone into the still-open §6.1 accumulator toward the five needed for a
    first rating; it travels with `sum_opponents` and `points` — zeroed
    together the moment the player becomes rated, and zeroed together again
    if the floor later drops them back out, because the accumulation starts
    over from zero rather than resuming from the lifetime count.
    """

    rating: int | None = None
    games: int = 0
    reached_2200: bool = False
    sum_opponents: int = 0
    points: Decimal = Decimal("0")
    accumulated_games: int = 0

    @property
    def is_rated(self) -> bool:
        return self.rating is not None


@dataclass
class PlayerState:
    """A player's unique identity, with one `ModalityState` per modality."""

    id_fexerj: int
    id_cbx: str = ""
    title: str = ""
    name: str = ""
    club: str = ""
    birthday: str = ""
    sex: str = ""
    federation: str = ""
    modalities: dict[str, ModalityState] = field(
        default_factory=lambda: {m: ModalityState() for m in MODALITIES}
    )


@dataclass(frozen=True)
class Game:
    """A single game from the period, already resolved to FEXERJ ids."""

    tournament_ord: int
    modality: str
    is_internal: bool
    player_id: int
    opponent_id: int
    score: Decimal
