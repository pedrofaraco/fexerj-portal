"""Rating rules: §2 (parameters), §3 (game), §5 (K), §6 (initial rating), §7 (floor).

All numbers come from the table in §2 of the spec, which translates FEXERJ's
Art. 68 onto the FIDE text. Pure functions: none of them reads a file or
holds state.
"""
import re
from decimal import ROUND_HALF_UP, Decimal

from .tables import dp_for_score_ratio

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
    """K factor from §5, before the 700 cap (§5.1).

    `reached_2200` is checked first, ahead of every other condition. Decided
    by FEXERJ: the permanent K=10 is a brake that only tightens — once a
    player's rating has reached 2200 on a published list, no other rule is
    allowed to raise K back up. This reverses the §5 table's own top-to-bottom
    order, where the under-18 K=40 branch sits above `reached_2200` and FIDE
    8.3.3's age cutoff wins the collision. Under FEXERJ's reading, a player
    who reached 2200 and then dropped back below 2100 before the end of the
    year they turn 18 keeps K=10, not the under-18 K=40 — and the same goes
    for a player who reached 2200 in a modality but still has fewer than 30
    games in it: K=10 wins over the new-player K=40 too.

    A transposed player (§1.1) is unaffected: `reached_2200` is tracked per
    modality, so a player entering a new modality with the STD rating still
    has it `False` there and gets the new-player K=40, even at a rating of
    2200 or above.
    """
    if reached_2200:
        return 10
    if games < NEW_PLAYER_GAMES:
        return 40
    if (
        birth_year is not None
        and rating is not None
        and rating < U18_RATING_CAP
        and is_under_18_at_year_end(birth_year, period_year)
    ):
        return 40
    return 20


def cap_k_by_games(k: int, games: int) -> int:
    """§5.1 cap, verbatim FIDE: "If the number of games (n) for a player on any list
    for a rating period multiplied by K exceeds 700, then K shall be the largest whole
    number such that K x n does not exceed 700."

    One K, one n, the whole period: `k` is the player's single K factor for the
    period (§5) and `games` is their total game count for the period, not any single
    tournament's.
    """
    if games <= 0 or k * games <= K_GAMES_PRODUCT_CAP:
        return k
    return K_GAMES_PRODUCT_CAP // games


def initial_rating(opponents_sum: int, opponents_count: int, points: Decimal) -> int | None:
    """Initial rating from §6.2, or `None` when it falls below the 1200 floor.

    `opponents_sum` and `opponents_count` describe the **rated** opponents
    faced, and `points` the points scored against them. The two fictitious
    1600 opponents, treated as draws, enter both the average and the score
    percentage.

    Takes a sum and a count rather than a list because that is how the §6.1
    accumulator is kept between periods, and rebuilding a list from the
    average would lose the division remainder.
    """
    total_games = opponents_count + 2
    ra = (Decimal(opponents_sum) + 2 * FICTITIOUS_OPPONENT_RATING) / total_games
    p = (points + 1) / total_games
    ru = round_half_away_from_zero(ra + dp_for_score_ratio(p))
    ru = min(ru, INITIAL_RATING_CAP)
    return None if applies_rating_floor(ru) else ru
