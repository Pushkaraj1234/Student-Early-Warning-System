"""Out-of-time splitting.

Rows are assigned to train / validation / test by ``split_group`` (for OULAD: the course
presentation). The split is rejected unless every training group precedes every validation
group, which precedes every test group — observations from the future can never be used to
train a model that is evaluated on the past.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from ml.data.oulad import presentation_sort_key

SortKey = Callable[[str], tuple[int, int]]


class SplitError(ValueError):
    """Raised when a split is not strictly time-ordered or is empty."""


@dataclass(frozen=True)
class TemporalSplit:
    train: tuple[str, ...]
    validation: tuple[str, ...]
    test: tuple[str, ...]

    def validate(self, sort_key: SortKey = presentation_sort_key) -> None:
        parts = {"train": self.train, "validation": self.validation, "test": self.test}
        for name, groups in parts.items():
            if not groups:
                raise SplitError(f"{name} split has no groups")
        all_groups = [*self.train, *self.validation, *self.test]
        if len(set(all_groups)) != len(all_groups):
            raise SplitError("a group appears in more than one split")
        if max(map(sort_key, self.train)) >= min(map(sort_key, self.validation)):
            raise SplitError("every training group must precede every validation group")
        if max(map(sort_key, self.validation)) >= min(map(sort_key, self.test)):
            raise SplitError("every validation group must precede every test group")


@dataclass(frozen=True)
class SplitFrames:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame
    unassigned_rows: int


def split_frame(
    df: pd.DataFrame,
    split: TemporalSplit,
    *,
    group_column: str = "split_group",
    sort_key: SortKey = presentation_sort_key,
) -> SplitFrames:
    split.validate(sort_key)
    groups = df[group_column]
    train = df[groups.isin(split.train)].reset_index(drop=True)
    validation = df[groups.isin(split.validation)].reset_index(drop=True)
    test = df[groups.isin(split.test)].reset_index(drop=True)
    for name, frame in (("train", train), ("validation", validation), ("test", test)):
        if frame.empty:
            raise SplitError(f"{name} split is empty for groups present in the data")
    unassigned = len(df) - len(train) - len(validation) - len(test)
    return SplitFrames(train=train, validation=validation, test=test, unassigned_rows=unassigned)
