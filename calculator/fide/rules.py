"""Rating rules: §2 (parameters), §3 (game), §5 (K), §6 (initial rating), §7 (floor).

All numbers come from the table in §2 of the spec, which translates FEXERJ's
Art. 68 onto the FIDE text. Pure functions: none of them reads a file or
holds state.
"""
import re
from decimal import ROUND_HALF_UP, Decimal

# §2 — parameters with the FEXERJ adaptation
RATING_FLOOR = 1200                 # below this, the player becomes unrated (§7)
FICTITIOUS_OPPONENT_RATING = 1600   # fictitious opponents for the initial rating (§6.2)
INITIAL_RATING_CAP = 2000           # cap on the initial rating (§6.2)
K10_THRESHOLD = 2200                # rating that locks in K=10 (§5)
U18_RATING_CAP = 2100               # rating cap for the under-18 K=40 (§5)
MAX_RATING_DIFF = 400               # diff cap, always applied (Art. 68 §3)
MIN_GAMES_FOR_FIRST_RATING = 5      # §6.1
NEW_PLAYER_GAMES = 30               # §5 — K=40 until 30 games are completed
K_GAMES_PRODUCT_CAP = 700           # §5.1


def capped_diff(player_rating: int, opponent_rating: int) -> int:
    """Rating difference with the 400 cap always applied.

    Art. 68 §3 removes the FIDE exception for players rated 2650 or above: at
    FEXERJ the cap applies to everyone.
    """
    diff = player_rating - opponent_rating
    return max(-MAX_RATING_DIFF, min(MAX_RATING_DIFF, diff))


def round_half_away_from_zero(value: Decimal) -> int:
    """Round to the nearest integer, with .5 ties going away from zero.

    Python's built-in `round()` is banker's rounding (`round(0.5) == 0`,
    `round(2.5) == 2`), which contradicts spec §3 step 5.
    """
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def applies_rating_floor(rating: int) -> bool:
    """True when the rating falls below the floor and the player becomes unrated (§7)."""
    return rating < RATING_FLOOR


_BIRTH_YEAR_RE = re.compile(r"(?:^|\D)(\d{4})(?:\D|$)")


def parse_birth_year(birthday: str) -> int | None:
    """Birth year from the `Birthday` column.

    Accepts `DD/MM/YYYY` and `YYYY-MM-DD`, the two formats found in the
    federation's files. Returns `None` when no recognizable year is present —
    it is the validation that rejects an empty field (§5.3), not this function.
    """
    if not birthday:
        return None
    match = _BIRTH_YEAR_RE.search(birthday.strip())
    return int(match.group(1)) if match else None


def is_under_18_at_year_end(birth_year: int, period_year: int) -> bool:
    """True until the end of the year the player turns 18 (§5)."""
    return period_year <= birth_year + 18


def base_k(
    rating: int | None,
    games: int,
    reached_2200: bool,
    birth_year: int | None,
    period_year: int,
) -> int:
    """K factor from §5, before the internal-tournament halving and the 700 cap.

    The conditions are checked in the order the §5 table lists them, top to
    bottom. That gives the under-18 K=40 branch precedence over the permanent
    K=10 from `reached_2200` whenever both would apply — mirroring FIDE 8.3.3,
    where the age cutoff takes precedence. The collision is real, if rare: a
    player who reached 2200 and then dropped back below 2100 before the end of
    the year they turn 18 still gets K=40, not the "permanent" K=10.
    """
    if games < NEW_PLAYER_GAMES:
        return 40
    if (
        birth_year is not None
        and rating is not None
        and rating < U18_RATING_CAP
        and is_under_18_at_year_end(birth_year, period_year)
    ):
        return 40
    if reached_2200:
        return 10
    return 20


def halve_for_internal(k: int) -> int:
    """Art. 68 §2: in an internal tournament, K is halved (40->20, 20->10, 10->5)."""
    return k // 2


def cap_k_by_games(k: int, games: int) -> int:
    """§5.1 cap: if `games * k > 700`, K becomes the largest integer with `k * games <= 700`.

    Applied last, after any reduction from Art. 68 §2.

    **Open point with FEXERJ** (spec §5.1): the cap is defined over a single
    K, but the internal-tournament exception makes K vary within the period.
    The proposal on record, implemented here, is to apply it per tournament,
    using that tournament's K and game count. If the federation decides
    otherwise, this function and its call site in `cycle.py` are the only
    places that need to change.
    """
    if games <= 0 or k * games <= K_GAMES_PRODUCT_CAP:
        return k
    return K_GAMES_PRODUCT_CAP // games
