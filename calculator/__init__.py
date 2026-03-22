"""FEXERJ rating calculator package.

The primary entry point is :class:`FexerjRatingCycle`, which accepts all
inputs as in-memory strings and bytes and returns output CSV content as a
dictionary of ``{filename: csv_string}``.
"""
from .classes import FexerjRatingCycle

__all__ = ["FexerjRatingCycle"]
