"""Check hosted Dart/Flutter dependencies (pubspec.lock) against the OSV vulnerability database.

Usage (from the repository root, any Python 3.12+; standard library only):
    python scripts/security/osv_check_pub.py apps/mobile/pubspec.lock

Only package names and versions are sent to https://api.osv.dev (ecosystem "Pub"). SDK and
path/git packages are skipped because OSV cannot resolve them. Exit code 1 if any
vulnerability is reported, 2 on a usage or network error.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"
TIMEOUT_SECONDS = 30
PACKAGE_RE = re.compile(r"^  ([A-Za-z0-9_]+):\s*$")
FIELD_RE = re.compile(r'^    (source|version):\s*"?([^"\s]+)"?\s*$')


def hosted_packages(lock_text: str) -> list[tuple[str, str]]:
    packages: list[tuple[str, str]] = []
    name: str | None = None
    fields: dict[str, str] = {}
    in_packages = False

    def flush() -> None:
        if name and fields.get("source") == "hosted" and "version" in fields:
            packages.append((name, fields["version"]))

    for line in lock_text.splitlines():
        if line.startswith("packages:"):
            in_packages = True
            continue
        if in_packages and line and not line.startswith(" "):
            break  # end of the packages section
        if not in_packages:
            continue
        if match := PACKAGE_RE.match(line):
            flush()
            name, fields = match.group(1), {}
        elif match := FIELD_RE.match(line):
            fields[match.group(1)] = match.group(2)
    flush()
    return packages


def query_osv(packages: list[tuple[str, str]]) -> list[tuple[str, str, list[str]]]:
    body = json.dumps(
        {"queries": [{"package": {"name": n, "ecosystem": "Pub"}, "version": v} for n, v in packages]}
    ).encode()
    request = urllib.request.Request(OSV_BATCH_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310 - fixed https URL
        results = json.load(response)["results"]
    if len(results) != len(packages):
        raise RuntimeError("OSV returned an unexpected number of results")
    return [
        (name, version, [v["id"] for v in result.get("vulns", [])])
        for (name, version), result in zip(packages, results, strict=True)
    ]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    packages = hosted_packages(Path(argv[1]).read_text(encoding="utf-8"))
    if not packages:
        print("no hosted packages found; is this a pubspec.lock?", file=sys.stderr)
        return 2
    try:
        findings = [f for f in query_osv(packages) if f[2]]
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"OSV query failed: {exc}", file=sys.stderr)
        return 2
    print(f"checked {len(packages)} hosted packages against OSV")
    for name, version, ids in findings:
        print(f"VULNERABLE {name} {version}: {', '.join(ids)}")
    if not findings:
        print("no known vulnerabilities reported")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
