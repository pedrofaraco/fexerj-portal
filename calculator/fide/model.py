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
class Accumulator:
    """The §6.1 accumulator a player without a rating carries toward their
    first one: how many games have gone into it, the sum of those games'
    opponent ratings, the points scored, and the period the current
    accumulation began (`since`, "YYYY-MM").

    The four fields are zeroed together the moment the player gains a
    rating, and zeroed together again if the floor (§7) later drops them
    back out — the accumulation starts over from zero rather than resuming
    from the lifetime `ModalityState.games` count. `since` is what the
    26-month pooling window (§6.2 / FIDE 7.1.4) is measured against; empty
    means there is no accumulation in progress.
    """

    games: int = 0
    sum_opponents: int = 0
    points: Decimal = Decimal("0")
    since: str = ""


@dataclass(frozen=True)
class ModalityState:
    """A player's rating, game count and §6.1 accumulator in one modality.

    `games` and `accumulator.games` count different things and must not be
    confused: `games` is the lifetime game count — it only grows, it is what
    §5's K factor reads, and §7 preserves it when the floor drops the player
    out of rated status. `accumulator.games` is how many of those games have
    gone into the still-open §6.1 accumulator toward the five needed for a
    first rating.
    """

    rating: int | None = None
    games: int = 0
    reached_2200: bool = False
    accumulator: Accumulator = field(default_factory=Accumulator)

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
    player_id: int
    opponent_id: int
    score: Decimal
