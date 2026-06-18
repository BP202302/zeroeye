#!/usr/bin/env python3
"""Validate deterministic output from tools/data_generator.py."""

from __future__ import annotations

import filecmp
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "tools" / "data_generator.py"
SEEDS = [1, 42, 8675309]


def run_generator(output_dir: Path, seed: int) -> None:
    subprocess.run(
        [
            sys.executable,
            str(GENERATOR),
            "--output-dir",
            str(output_dir),
            "--seed",
            str(seed),
            "--format",
            "both",
            "--users",
            "5",
            "--orders",
            "8",
            "--trades",
            "8",
            "--ticks",
            "5",
            "--candles",
            "5",
        ],
        cwd=ROOT,
        check=True,
    )


def files_by_relative_path(directory: Path) -> dict[Path, Path]:
    return {
        path.relative_to(directory): path
        for path in directory.rglob("*")
        if path.is_file()
    }


def assert_byte_identical(left: Path, right: Path, seed: int) -> None:
    left_files = files_by_relative_path(left)
    right_files = files_by_relative_path(right)
    if set(left_files) != set(right_files):
        missing_left = sorted(set(right_files) - set(left_files))
        missing_right = sorted(set(left_files) - set(right_files))
        raise AssertionError(
            f"seed {seed}: file sets differ; missing_left={missing_left}, "
            f"missing_right={missing_right}"
        )

    for relpath in sorted(left_files):
        if not filecmp.cmp(left_files[relpath], right_files[relpath], shallow=False):
            raise AssertionError(f"seed {seed}: {relpath} differs")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="data-generator-seed-") as tmp:
        workspace = Path(tmp)
        for seed in SEEDS:
            first = workspace / f"seed-{seed}-a"
            second = workspace / f"seed-{seed}-b"
            run_generator(first, seed)
            run_generator(second, seed)
            assert_byte_identical(first, second, seed)
            print(f"seed {seed}: deterministic")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
