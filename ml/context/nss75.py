"""NSS 75th round (2017-18), Schedule 25.2 "Household Social Consumption: Education" (MoSPI, India):
a CODE-AGNOSTIC integrity profile of the unit-level microdata.

Scope (owner decision 2026-09-25): this survey is descriptive context for SEWS only. It is NOT used to
train or evaluate any SEWS risk model, because it has no attendance, grades, assessments or LMS
activity, has no time dimension (features and "currently not attending" come from one interview),
and its strongest signals are protected attributes (religion, social group, gender, disability).

No codebook (schedule 25.2 layout) is available, so this module never interprets a code value and
never applies the survey weights (which weight column to use for combined estimates is itself a
codebook question). It reports only what can be established without decoding:
  * row counts, columns, missing values and key uniqueness per block;
  * how blocks link (households to block 1, persons to block 4);
  * whether persons aged 3-35 split cleanly into "attending" (block 5) and "not attending" (block 7);
  * raw code frequencies for low-cardinality columns, labelled as undecoded;
  * row counts of another delivery format, when it can be read.
Output is aggregate only. Identifier, geography, date and weight columns are never listed with values.

Usage (from the repository root; the archives are read in place and never copied into the repository):
    ml/.venv/Scripts/python -m ml.context.nss75 --csv-zip PATH/Data_in_CSV.zip \
        [--stata-zip PATH/Data_in_STATA.zip] [--out ml/reports]
"""

from __future__ import annotations

import argparse
import io
import json
import re
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

BLOCK_RE = re.compile(r"R75252(L0[1-8])")
CHUNK_ROWS = 50_000
MAX_LISTED_CODES = 50  # columns with more distinct values are treated as amounts/identifiers
TOP_CODES = 15
PERSON_AGE_RANGE = (3, 35)  # the schedule's education blocks cover persons aged 3 to 35


@dataclass(frozen=True)
class BlockSpec:
    title: str
    key: tuple[str, ...]


BLOCKS: dict[str, BlockSpec] = {
    "L01": BlockSpec("Blocks 1, 2 and 11: identification of sample household", ("HHID",)),
    "L02": BlockSpec("Block 3: household characteristics", ("HHID",)),
    "L03": BlockSpec(
        "Block 3.1: erstwhile members aged 3-35 currently attending education", ("HHID", "Person_serialno")
    ),
    "L04": BlockSpec("Block 4: demographic particulars of household members", ("HHID", "Per_serialno")),
    "L05": BlockSpec(
        "Block 5: persons aged 3-35 currently attending (basic course)", ("HHID", "Per_serialno")
    ),
    "L06": BlockSpec(
        "Block 6: expenditure of persons currently attending pre-primary and above", ("HHID", "Per_serialno")
    ),
    "L07": BlockSpec("Block 7: persons aged 3-35 currently not attending", ("HHID", "Per_serialno")),
    "L08": BlockSpec(
        "Block 8: formal vocational/technical training, persons aged 12-59", ("HHID", "Per_serialno")
    ),
}

# Never listed with values: identifiers, fine geography, dates, staff codes and survey weights.
UNLISTED_COLUMNS = frozenset(
    {
        "HHID",
        "FSU",
        "District",
        "StateDistrict",
        "StateDitrict",
        "NSS_Region",
        "Stratum",
        "Sub_stratum",
        "FOD_Sub_Region",
        "Hamlet_Sub_block",
        "Second_stage_stratum",
        "Sample_hhld",
        "Per_serialno",
        "Person_serialno",
        "Employee_code",
        "Employee_code1",
        "Employee_code2",
        "Investigator_Nos",
        "Survey_date",
        "Dispatch_date",
        "Location_district",
        "Present_resid_district_code",
        "MULT",
        "MULT_SubSample",
        "MULT_Combined",
    }
)


class Nss75FormatError(ValueError):
    """The archive does not look like the expected NSS 75th-round schedule 25.2 delivery."""


@dataclass
class BlockProfile:
    block: str
    file: str
    rows: int = 0
    columns: list[str] = field(default_factory=list)
    missing: Counter[str] = field(default_factory=Counter)
    duplicate_keys: int = 0
    codes: dict[str, Counter[str]] = field(default_factory=dict)
    high_cardinality: set[str] = field(default_factory=set)

    def as_dict(self) -> dict[str, Any]:
        return {
            "block": self.block,
            "title": BLOCKS[self.block].title,
            "file": self.file,
            "rows": self.rows,
            "columns": len(self.columns),
            "key": list(BLOCKS[self.block].key),
            "duplicate_keys": self.duplicate_keys,
            "missing_share": {
                c: round(self.missing[c] / self.rows, 4) if self.rows else None for c in self.columns
            },
            "undecoded_code_counts": {
                c: dict(counter.most_common(TOP_CODES)) for c, counter in sorted(self.codes.items())
            },
            "distinct_codes": {c: len(counter) for c, counter in sorted(self.codes.items())},
            "not_listed_high_cardinality": sorted(self.high_cardinality),
        }


def block_members(archive: zipfile.ZipFile, suffix: str) -> dict[str, str]:
    """Map block id (L01..L08) to the archive member with the given extension."""
    members: dict[str, str] = {}
    for name in archive.namelist():
        match = BLOCK_RE.search(name)
        if match and name.lower().endswith(suffix):
            if match.group(1) in members:
                raise Nss75FormatError(f"block {match.group(1)} appears more than once")
            members[match.group(1)] = name
    if not members:
        raise Nss75FormatError("no R75252 block files found in the archive")
    return members


def _profile_block(
    archive: zipfile.ZipFile, block: str, member: str
) -> tuple[BlockProfile, set[tuple[str, ...]], set[tuple[str, ...]]]:
    """Profile one CSV block.

    Returns the profile, its key set and (block 4 only) the keys of persons aged 3-35."""
    profile = BlockProfile(block=block, file=member.rsplit("/", 1)[-1])
    key_cols = list(BLOCKS[block].key)
    keys: set[tuple[str, ...]] = set()
    age_3_35: set[tuple[str, ...]] = set()
    with archive.open(member) as handle:
        reader = pd.read_csv(
            handle,
            dtype=str,
            keep_default_na=False,
            na_values=[""],
            chunksize=CHUNK_ROWS,
            encoding="utf-8-sig",
        )
        for chunk in reader:
            if not profile.columns:
                profile.columns = list(chunk.columns)
                missing_keys = [k for k in key_cols if k not in chunk.columns]
                if missing_keys:
                    raise Nss75FormatError(f"{block} lacks key columns {missing_keys}")
            profile.rows += len(chunk)
            profile.missing.update({str(c): int(n) for c, n in chunk.isna().sum().items()})
            for row_key in chunk[key_cols].itertuples(index=False, name=None):
                if row_key in keys:
                    profile.duplicate_keys += 1
                else:
                    keys.add(row_key)
            for column in chunk.columns:
                if column in UNLISTED_COLUMNS or column in profile.high_cardinality:
                    continue
                counter = profile.codes.setdefault(column, Counter())
                counter.update(chunk[column].dropna().to_list())
                if len(counter) > MAX_LISTED_CODES:
                    profile.high_cardinality.add(column)
                    del profile.codes[column]
            if block == "L04" and "Age" in chunk.columns:
                age = pd.to_numeric(chunk["Age"], errors="coerce")
                in_range = age.between(*PERSON_AGE_RANGE)
                age_3_35.update(chunk.loc[in_range, key_cols].itertuples(index=False, name=None))
    return profile, keys, age_3_35


def profile_csv_archive(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        members = block_members(archive, ".csv")
        profiles: dict[str, BlockProfile] = {}
        keys: dict[str, set[tuple[str, ...]]] = {}
        age_3_35: set[tuple[str, ...]] = set()
        for block in sorted(members):
            profile, block_keys, ages = _profile_block(archive, block, members[block])
            profiles[block], keys[block] = profile, block_keys
            age_3_35 |= ages

    linkage: dict[str, Any] = {"missing_blocks": sorted(set(BLOCKS) - set(members))}
    households = {k[0] for k in keys.get("L01", set())}
    linkage["households_not_in_L01"] = {
        b: len({k[0] for k in ks} - households) for b, ks in keys.items() if b != "L01" and households
    }
    persons = keys.get("L04", set())
    if persons:
        linkage["persons_not_in_L04"] = {
            b: len(keys[b] - persons) for b in ("L05", "L06", "L07", "L08") if b in keys
        }
    if {"L05", "L06"} <= keys.keys():
        linkage["L06_persons_not_in_L05"] = len(keys["L06"] - keys["L05"])
    if {"L04", "L05", "L07"} <= keys.keys():
        attending, not_attending = keys["L05"], keys["L07"]
        linkage["age_3_35_in_L04"] = {
            "persons": len(age_3_35),
            "attending_only_L05": len((age_3_35 & attending) - not_attending),
            "not_attending_only_L07": len((age_3_35 & not_attending) - attending),
            "in_both_L05_and_L07": len(age_3_35 & attending & not_attending),
            "in_neither": len(age_3_35 - attending - not_attending),
        }
    return {"blocks": {b: p.as_dict() for b, p in profiles.items()}, "linkage": linkage}


def stata_row_counts(path: Path) -> dict[str, int]:
    """Row counts of the Stata delivery, counted through the public chunked reader."""
    counts: dict[str, int] = {}
    with zipfile.ZipFile(path) as archive:
        for block, member in sorted(block_members(archive, ".dta").items()):
            with (
                archive.open(member) as handle,
                pd.read_stata(
                    io.BytesIO(handle.read()), chunksize=CHUNK_ROWS, convert_categoricals=False
                ) as reader,
            ):
                counts[block] = sum(len(chunk) for chunk in reader)
    return counts


def compare_formats(csv_rows: dict[str, int], other_rows: dict[str, int]) -> dict[str, Any]:
    return {
        block: {
            "csv": csv_rows.get(block),
            "other": other_rows.get(block),
            "match": csv_rows.get(block) == other_rows.get(block),
        }
        for block in sorted(set(csv_rows) | set(other_rows))
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        f"# NSS 75th round, schedule 25.2 — code-agnostic profile ({result['created_at']})",
        "",
        "> **Descriptive context only. Not used to train or evaluate any SEWS model.** Source: MoSPI "
        "unit-level microdata, India, 2017-18. No codebook was available: code values below are "
        "**undecoded** and survey weights are **not applied**, so none of these counts is a population "
        "estimate.",
        "",
        "| Block | Content | Rows | Columns | Duplicate keys |",
        "|---|---|---:|---:|---:|",
    ]
    for block, p in result["blocks"].items():
        lines.append(f"| {block} | {p['title']} | {p['rows']} | {p['columns']} | {p['duplicate_keys']} |")
    link = result["linkage"]
    lines += ["", "## Linkage", ""]
    lines.append(f"- Blocks missing from the delivery: {', '.join(link['missing_blocks']) or 'none'}")
    for name in ("households_not_in_L01", "persons_not_in_L04"):
        if name in link:
            lines.append(f"- {name.replace('_', ' ')}: {link[name]}")
    if "L06_persons_not_in_L05" in link:
        lines.append(f"- block 6 persons not in block 5: {link['L06_persons_not_in_L05']}")
    if "age_3_35_in_L04" in link:
        a = link["age_3_35_in_L04"]
        lines += [
            f"- Persons aged 3-35 in block 4: {a['persons']} — attending only (block 5): "
            f"{a['attending_only_L05']}; "
            f"not attending only (block 7): {a['not_attending_only_L07']}; both: {a['in_both_L05_and_L07']}; "
            f"neither: {a['in_neither']}",
        ]
    if result.get("format_check"):
        lines += [
            "",
            f"## Row counts vs {result['format_check']['format']}",
            "",
            "| Block | CSV | Other | Match |",
            "|---|---:|---:|---|",
        ]
        for block, c in result["format_check"]["blocks"].items():
            lines.append(f"| {block} | {c['csv']} | {c['other']} | {'yes' if c['match'] else 'NO'} |")
    lines += ["", "## Columns with the most missing values (share of rows)", ""]
    for block, p in result["blocks"].items():
        worst = sorted(p["missing_share"].items(), key=lambda kv: -(kv[1] or 0))[:5]
        lines.append(f"- {block}: " + ", ".join(f"{c} {v:.1%}" for c, v in worst if v))
    lines += [
        "",
        "Raw (undecoded) code frequencies per column are in `profile.json` under `undecoded_code_counts`.",
        "",
    ]
    return "\n".join(lines)


def run(csv_zip: Path, out_root: Path, stata_zip: Path | None = None) -> dict[str, Any]:
    timestamp = datetime.now(UTC).replace(microsecond=0)
    result: dict[str, Any] = {
        "created_at": timestamp.isoformat(),
        "dataset": "NSS 75th round, schedule 25.2 (Household Social Consumption: Education), MoSPI, 2017-18",
        "scope": "descriptive context only; not used for any SEWS model",
        "codebook_available": False,
        "weights_applied": False,
        **profile_csv_archive(csv_zip),
    }
    if stata_zip is not None:
        csv_rows = {b: p["rows"] for b, p in result["blocks"].items()}
        result["format_check"] = {
            "format": "Stata (.dta)",
            "blocks": compare_formats(csv_rows, stata_row_counts(stata_zip)),
        }
    out = out_root / f"nss75-profile-{timestamp:%Y%m%dT%H%M%SZ}"
    out.mkdir(parents=True, exist_ok=False)
    (out / "profile.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (out / "report.md").write_text(render_markdown(result), encoding="utf-8")
    result["output_dir"] = str(out)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--csv-zip", type=Path, required=True)
    parser.add_argument("--stata-zip", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=Path("ml/reports"))
    args = parser.parse_args(argv)
    result = run(args.csv_zip, args.out, args.stata_zip)
    print(f"profile written to {result['output_dir']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
