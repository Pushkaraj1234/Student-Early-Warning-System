"""Causal sequence models over the student-week panel: GRU, LSTM and a temporal convolutional network (TCN).

Each registration is one sequence over weeks 1..T. The model outputs a risk for every week; the output for
week ``k`` depends only on inputs from weeks <= ``k`` (recurrent state / left-padded convolutions), so it uses
the same information as a tabular model at that cutoff. Weeks where the registration is not in the panel
(not yet registered, or already withdrawn) carry zero inputs and no loss.

Inputs: panel features standardised with TRAINING means/SDs; missing values become 0 plus a missing-indicator
channel for every feature that has missing values in training.
"""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd
import torch
from numpy.typing import NDArray
from torch import nn

SequenceKind = Literal["gru", "lstm", "tcn"]
TCN_DILATIONS = (1, 2, 4)
TCN_KERNEL = 3
BATCH_SIZE = 256
LEARNING_RATE = 1e-3


@dataclass(frozen=True)
class Standardizer:
    features: tuple[str, ...]
    mean: NDArray[np.float64]
    std: NDArray[np.float64]
    indicator_features: tuple[int, ...]

    @classmethod
    def fit(cls, frame: pd.DataFrame, features: Sequence[str]) -> Standardizer:
        x = frame.loc[:, list(features)].to_numpy(dtype=np.float64)
        with warnings.catch_warnings():
            # A feature missing in every training row is expected early in a course: mean 0, SD 1 below.
            warnings.simplefilter("ignore", RuntimeWarning)
            mean = np.nanmean(x, axis=0)
            std = np.nanstd(x, axis=0)
        mean = np.where(np.isfinite(mean), mean, 0.0)
        std = np.where(np.isfinite(std) & (std > 0), std, 1.0)
        indicators = tuple(int(i) for i in np.flatnonzero(np.isnan(x).any(axis=0)))
        return cls(features=tuple(features), mean=mean, std=std, indicator_features=indicators)

    @property
    def width(self) -> int:
        return len(self.features) + len(self.indicator_features)

    def transform(self, frame: pd.DataFrame) -> NDArray[np.float32]:
        x = frame.loc[:, list(self.features)].to_numpy(dtype=np.float64)
        missing = np.isnan(x)
        z = np.where(missing, 0.0, (x - self.mean) / self.std)
        flags = missing[:, list(self.indicator_features)].astype(np.float64)
        return np.concatenate([z, flags], axis=1).astype(np.float32)


@dataclass(frozen=True)
class SequenceData:
    """X (n, T, width), y (n, T) with NaN where unlabelled, rows (n, T) = panel row positions or -1."""

    X: NDArray[np.float32]
    y: NDArray[np.float32]
    rows: NDArray[np.int64]


def to_sequences(
    frame: pd.DataFrame, label: str | None, standardizer: Standardizer, *, max_week: int
) -> SequenceData:
    """Pack panel rows (any order) into per-registration sequences; row positions refer to ``frame``."""
    codes = frame.groupby(["context_id", "student_id"], sort=True, observed=True).ngroup().to_numpy()
    t = frame["week"].to_numpy(dtype=np.int64) - 1
    if t.min() < 0 or t.max() >= max_week:
        raise ValueError("week outside 1..max_week")
    n = int(codes.max()) + 1
    X = np.zeros((n, max_week, standardizer.width), dtype=np.float32)
    y = np.full((n, max_week), np.nan, dtype=np.float32)
    rows = np.full((n, max_week), -1, dtype=np.int64)
    X[codes, t] = standardizer.transform(frame)
    if label is not None:
        y[codes, t] = frame[label].to_numpy(dtype=np.float32)
    rows[codes, t] = np.arange(len(frame))
    return SequenceData(X=X, y=y, rows=rows)


class RecurrentNet(nn.Module):
    def __init__(self, kind: Literal["gru", "lstm"], width: int, hidden: int, dropout: float) -> None:
        super().__init__()
        self.rnn: nn.Module = (nn.GRU if kind == "gru" else nn.LSTM)(width, hidden, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Linear(hidden, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.rnn(x)
        logits: torch.Tensor = self.head(self.dropout(out)).squeeze(-1)
        return logits


class CausalBlock(nn.Module):
    def __init__(self, channels_in: int, channels: int, dilation: int, dropout: float) -> None:
        super().__init__()
        self.pad = (TCN_KERNEL - 1) * dilation
        self.conv1 = nn.Conv1d(channels_in, channels, TCN_KERNEL, dilation=dilation)
        self.conv2 = nn.Conv1d(channels, channels, TCN_KERNEL, dilation=dilation)
        self.dropout = nn.Dropout(dropout)
        self.skip = nn.Conv1d(channels_in, channels, 1) if channels_in != channels else nn.Identity()

    def _causal(self, conv: nn.Module, x: torch.Tensor) -> torch.Tensor:
        out: torch.Tensor = conv(nn.functional.pad(x, (self.pad, 0)))
        return out

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.dropout(torch.relu(self._causal(self.conv1, x)))
        h = self.dropout(torch.relu(self._causal(self.conv2, h)))
        skip: torch.Tensor = self.skip(x)
        return torch.relu(h + skip)


class TemporalConvNet(nn.Module):
    def __init__(self, width: int, hidden: int, dropout: float) -> None:
        super().__init__()
        blocks: list[nn.Module] = []
        channels_in = width
        for dilation in TCN_DILATIONS:
            blocks.append(CausalBlock(channels_in, hidden, dilation, dropout))
            channels_in = hidden
        self.blocks = nn.Sequential(*blocks)
        self.head = nn.Linear(hidden, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h: torch.Tensor = self.blocks(x.transpose(1, 2)).transpose(1, 2)
        logits: torch.Tensor = self.head(h).squeeze(-1)
        return logits


def build_sequence_model(kind: SequenceKind, width: int, hidden: int, dropout: float) -> nn.Module:
    if kind in ("gru", "lstm"):
        return RecurrentNet(kind, width, hidden, dropout)
    if kind == "tcn":
        return TemporalConvNet(width, hidden, dropout)
    raise ValueError(f"unknown sequence model: {kind}")


def _masked_loss(logits: torch.Tensor, y: torch.Tensor) -> tuple[torch.Tensor, int]:
    mask = ~torch.isnan(y)
    count = int(mask.sum())
    if count == 0:
        return logits.sum() * 0.0, 0
    loss = nn.functional.binary_cross_entropy_with_logits(logits[mask], y[mask], reduction="sum")
    return loss, count


def _evaluate_loss(model: nn.Module, data: SequenceData) -> float:
    model.eval()
    total, count = 0.0, 0
    with torch.no_grad():
        for start in range(0, len(data.X), BATCH_SIZE):
            loss, n = _masked_loss(
                model(torch.from_numpy(data.X[start : start + BATCH_SIZE])),
                torch.from_numpy(data.y[start : start + BATCH_SIZE]),
            )
            total += float(loss)
            count += n
    return total / max(count, 1)


@dataclass
class TrainingLog:
    train_loss: list[float] = field(default_factory=list)
    val_loss: list[float] = field(default_factory=list)
    best_epoch: int = 0


def train_sequence_model(
    kind: SequenceKind,
    train: SequenceData,
    *,
    hidden: int,
    dropout: float,
    seed: int,
    epochs: int,
    validation: SequenceData | None = None,
    patience: int = 3,
    batch_size: int = BATCH_SIZE,
) -> tuple[nn.Module, TrainingLog]:
    """Train with Adam on the masked weekly loss. With ``validation``: early stopping (best validation loss is
    kept, at most ``epochs``). Without: exactly ``epochs`` epochs (used to refit with a fixed budget)."""
    torch.manual_seed(seed)
    generator = torch.Generator().manual_seed(seed)
    model = build_sequence_model(kind, train.X.shape[2], hidden, dropout)
    optimiser = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    X = torch.from_numpy(train.X)
    y = torch.from_numpy(train.y)
    log = TrainingLog()
    best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
    best_val = float("inf")
    stale = 0
    for epoch in range(1, epochs + 1):
        model.train()
        order = torch.randperm(len(X), generator=generator)
        total, count = 0.0, 0
        for start in range(0, len(order), batch_size):
            batch = order[start : start + batch_size]
            loss, n = _masked_loss(model(X[batch]), y[batch])
            if n == 0:
                continue
            optimiser.zero_grad()
            (loss / n).backward()  # type: ignore[no-untyped-call]  # torch leaves Tensor.backward untyped
            optimiser.step()
            total += float(loss.detach())
            count += n
        log.train_loss.append(total / max(count, 1))
        if validation is None:
            log.best_epoch = epoch
            continue
        val_loss = _evaluate_loss(model, validation)
        log.val_loss.append(val_loss)
        if val_loss < best_val - 1e-5:
            best_val, stale, log.best_epoch = val_loss, 0, epoch
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        else:
            stale += 1
            if stale >= patience:
                break
    if validation is not None:
        model.load_state_dict(best_state)
    model.eval()
    return model, log


def predict_sequences(
    model: nn.Module, data: SequenceData, *, mc_samples: int = 0, seed: int = 0
) -> NDArray[np.float64]:
    """Risk per (sequence, week). With ``mc_samples`` > 0: array (mc_samples, n, T) from MC dropout (dropout
    layers active at inference, everything else in evaluation mode)."""

    def run() -> NDArray[np.float64]:
        parts = []
        with torch.no_grad():
            for start in range(0, len(data.X), BATCH_SIZE):
                parts.append(
                    torch.sigmoid(model(torch.from_numpy(data.X[start : start + BATCH_SIZE]))).numpy()
                )
        return np.concatenate(parts).astype(np.float64)

    model.eval()
    if mc_samples <= 0:
        return run()
    torch.manual_seed(seed)
    for module in model.modules():
        if isinstance(module, nn.Dropout):
            module.train()
    try:
        return np.stack([run() for _ in range(mc_samples)])
    finally:
        model.eval()


def scatter_to_rows(values: NDArray[np.float64], data: SequenceData, n_rows: int) -> NDArray[np.float64]:
    """Map per-(sequence, week) values back onto the panel rows the sequences were built from."""
    out = np.full(n_rows, np.nan)
    present = data.rows >= 0
    out[data.rows[present]] = values[present]
    if np.isnan(out).any():
        raise ValueError("some panel rows received no prediction")
    return out
