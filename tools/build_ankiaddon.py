#!/usr/bin/env python3
"""Build a release .ankiaddon archive from the source tree."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
PACKAGE_FILES = [
    "__init__.py",
    "config.py",
    "config.json",
    "config.md",
    "manifest.json",
    "LICENSE.txt",
    "README.md",
    "CHANGELOG.md",
]


def main() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    package = manifest["package"]
    version = manifest["version"]
    artifact = DIST / f"bible-verse-displayer-{version}-{package}.ankiaddon"

    DIST.mkdir(exist_ok=True)
    with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative_path in PACKAGE_FILES:
            archive.write(ROOT / relative_path, relative_path)

    print(artifact)


if __name__ == "__main__":
    main()
