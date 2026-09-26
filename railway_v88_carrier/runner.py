from __future__ import annotations

import csv
import json
import os
import pathlib
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path.cwd()
OUT = ROOT / "research/development/v88"


def log(*args):
    print(*args, flush=True)


def download_manifest(env_name: str) -> None:
    items = json.loads(os.environ[env_name])
    for i, item in enumerate(items, 1):
        path = ROOT / item["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        expected = int(item.get("size", 0) or 0)
        if path.exists() and (not expected or path.stat().st_size == expected):
            log("CACHE_OK", env_name, i, len(items), item["path"], path.stat().st_size)
            continue

        log("DOWNLOAD_START", env_name, i, len(items), item["path"], expected)
        req = urllib.request.Request(item["url"], headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=240) as response, path.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)

        got = path.stat().st_size
        if expected and got != expected:
            raise RuntimeError(f"size mismatch {item['path']}: {got} != {expected}")
        log("DOWNLOAD_DONE", env_name, i, got)


def top_near_misses(path: pathlib.Path, limit: int = 80) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    def num(row: dict, key: str) -> float:
        try:
            return float(row.get(key, 0) or 0)
        except Exception:
            return 0.0

    keys = (
        "val_min_trades",
        "min_n",
        "n1",
        "n2",
        "pf_min",
        "wr_min",
        "payoff_min",
        "expectancy_min",
    )
    rows.sort(key=lambda row: tuple(num(row, key) for key in keys), reverse=True)
    return rows[:limit]


def run_seed(seed: int, n: int) -> None:
    tag = f"v88_ensemble_s{seed}"
    log("V88_SEED_START", seed, n)
    subprocess.run(
        [
            sys.executable,
            "-u",
            "research/search/v88_v84_quality_ensemble.py",
            "--n",
            str(n),
            "--seed",
            str(seed),
            "--tag",
            tag,
        ],
        cwd=ROOT,
        check=True,
    )

    audit = OUT / f"{tag}_audit.json"
    survivors = OUT / f"{tag}_survivors.csv"
    near = OUT / f"{tag}_near_misses.csv"

    log("V88_AUDIT_BEGIN", seed)
    log(audit.read_text(encoding="utf-8"))
    log("V88_AUDIT_END", seed)

    if survivors.exists():
        log("V88_SURVIVORS_BEGIN", seed)
        log(survivors.read_text(encoding="utf-8"))
        log("V88_SURVIVORS_END", seed)

    rows = top_near_misses(near)
    log("V88_NEAR_TOP_BEGIN", seed, len(rows))
    for row in rows:
        log(json.dumps(row, sort_keys=True))
    log("V88_NEAR_TOP_END", seed)
    log("V88_SEED_DONE", seed)


def main() -> None:
    log("CARRIER_START", sys.version)
    download_manifest("CODE_MANIFEST")
    download_manifest("DATA_MANIFEST")
    log("INPUTS_READY")

    OUT.mkdir(parents=True, exist_ok=True)
    n = int(os.environ.get("V88_N", "120000"))
    seeds = [int(x) for x in os.environ.get("V88_SEEDS", "88001,88002,88003,88004").split(",") if x.strip()]
    for seed in seeds:
        run_seed(seed, n)
    log("V88_ALL_DONE", seeds, n)


if __name__ == "__main__":
    main()
