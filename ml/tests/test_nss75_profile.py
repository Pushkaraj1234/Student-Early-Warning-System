"""NSS 75th-round profiler on a SYNTHETIC archive in the delivery's layout (no real survey rows)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

import ml.context.nss75 as nss75
from ml.context.nss75 import Nss75FormatError, profile_csv_archive, run

PREFIX = "Data_in_CSV/R75252"

L01 = "HHID,District,MULT\nh1,01,100\nh2,02,200\n"
# h2/2 appears twice (duplicate key); h1/3 is 40 (outside 3-35); one Gender value is blank.
L04 = (
    "HHID,Per_serialno,Age,Gender,Amount\n"
    "h1,1,10,1,11\nh1,2,20,2,12\nh1,3,40,1,13\nh2,1,5,,14\nh2,2,30,2,15\nh2,2,30,2,16\n"
)
L05 = "HHID,Per_serialno,Age\nh1,1,10\nh2,2,30\nh3,1,12\n"  # h3 is not a surveyed household
L06 = "HHID,Per_serialno,Age\nh1,1,10\nh2,1,5\n"  # h2/1 is not in block 5
L07 = "HHID,Per_serialno,Age\nh1,2,20\nh2,2,30\n"  # h2/2 is also in block 5


def _archive(tmp_path: Path, files: dict[str, str]) -> Path:
    path = tmp_path / "Data_in_CSV.zip"
    with zipfile.ZipFile(path, "w") as z:
        for name, text in files.items():
            z.writestr(name, text)
    return path


@pytest.fixture
def archive(tmp_path: Path) -> Path:
    return _archive(
        tmp_path,
        {
            f"{PREFIX}L01 -(Blocks 1, 2 and 11)- Identification.csv": L01,
            f"{PREFIX}L04 (Block-4)-Demographic.csv": L04,
            f"{PREFIX}L05 (Block-5)-Attending.csv": L05,
            f"{PREFIX}L06 (Block 6)-Expenditure.csv": L06,
            f"{PREFIX}L07 (Block 7)-Not attending.csv": L07,
            "Data_in_CSV/readme.txt": "not a block",
        },
    )


def test_rows_duplicates_and_missing_values(archive: Path) -> None:
    blocks = profile_csv_archive(archive)["blocks"]
    assert {b: p["rows"] for b, p in blocks.items()} == {"L01": 2, "L04": 6, "L05": 3, "L06": 2, "L07": 2}
    assert blocks["L04"]["duplicate_keys"] == 1
    assert blocks["L04"]["missing_share"]["Gender"] == pytest.approx(1 / 6, abs=1e-4)


def test_linkage_and_attendance_partition(archive: Path) -> None:
    link = profile_csv_archive(archive)["linkage"]
    assert link["missing_blocks"] == ["L02", "L03", "L08"]
    assert link["households_not_in_L01"] == {"L04": 0, "L05": 1, "L06": 0, "L07": 0}
    assert link["persons_not_in_L04"] == {"L05": 1, "L06": 0, "L07": 0}
    assert link["L06_persons_not_in_L05"] == 1
    assert link["age_3_35_in_L04"] == {
        "persons": 4,
        "attending_only_L05": 1,
        "not_attending_only_L07": 1,
        "in_both_L05_and_L07": 1,
        "in_neither": 1,
    }


def test_identifiers_geography_and_weights_are_never_listed(archive: Path) -> None:
    blocks = profile_csv_archive(archive)["blocks"]
    listed = set(blocks["L01"]["undecoded_code_counts"]) | set(blocks["L04"]["undecoded_code_counts"])
    assert not listed & {"HHID", "District", "MULT", "Per_serialno"}
    assert blocks["L04"]["undecoded_code_counts"]["Gender"] == {"2": 3, "1": 2}  # raw codes, not decoded


def test_high_cardinality_columns_are_not_listed(archive: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nss75, "MAX_LISTED_CODES", 3)
    l04 = profile_csv_archive(archive)["blocks"]["L04"]
    assert "Amount" in l04["not_listed_high_cardinality"] and "Amount" not in l04["undecoded_code_counts"]


def test_format_errors(tmp_path: Path) -> None:
    with pytest.raises(Nss75FormatError, match="no R75252"):
        profile_csv_archive(_archive(tmp_path, {"x.csv": "a\n1\n"}))
    twice = tmp_path / "twice"
    twice.mkdir()
    with pytest.raises(Nss75FormatError, match="more than once"):
        profile_csv_archive(_archive(twice, {f"{PREFIX}L01 a.csv": L01, f"{PREFIX}L01 b.csv": L01}))
    nokey = tmp_path / "nokey"
    nokey.mkdir()
    with pytest.raises(Nss75FormatError, match="lacks key"):
        profile_csv_archive(_archive(nokey, {f"{PREFIX}L04 a.csv": "HHID,Age\nh1,3\n"}))


def test_report_is_aggregate_and_states_its_limits(archive: Path, tmp_path: Path) -> None:
    result = run(archive, tmp_path / "reports")
    out = Path(result["output_dir"])
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "Not used to train or evaluate any SEWS model" in report
    assert "undecoded" in report and "weights are **not applied**" in report
    saved = json.loads((out / "profile.json").read_text(encoding="utf-8"))
    assert saved["codebook_available"] is False and saved["weights_applied"] is False
    text = json.dumps(saved)
    assert "h1" not in text and "h2" not in text  # no household or person identifiers
