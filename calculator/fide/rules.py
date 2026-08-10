"""Rating rules: §2 (parameters), §3 (game), §5 (K), §6 (initial rating), §7 (floor).

All numbers come from the table in §2 of the spec, which translates FEXERJ's
Art. 68 onto the FIDE text. Pure functions: none of them reads a file or
holds state.
"""
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
