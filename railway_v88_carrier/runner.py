from __future__ import annotations

import csv
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path.cwd()
OUT = ROOT / "research/development/v88"


def log(*args):
    print(*args, flush=True)


def write_env_file(env_name: str, relpath: str) -> None:
    value = os.environ.get(env_name)
    if not value:
        raise RuntimeError(f"missing required environment variable: {env_name}")
    path = ROOT / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    log("SOURCE_READY", env_name, relpath, path.stat().st_size)


def prepare_sources() -> None:
    mapping = {
        "V34_SRC": "research/search/v34_calibrated_dynamic_leverage.py",
        "V42_SRC": "research/search/v42_futures_microstructure.py",
        "V60_SRC": "research/search/v60_positioning_meta.py",
        "V88_SRC": "research/search/v88_v84_quality_ensemble.py",
        "V41_ACQUIRE_SRC": "research/data/acquire_v41_futures_features.py",
        "V59_ACQUIRE_SRC": "research/data/acquire_v59_positioning.py",
        "V89_DIAG_SRC": "research/search/v89_v88_gate_diagnostics.py",
        "V90_SRC": "research/search/v90_v88_dense_exit_screen.py",
        "V91_SRC": "research/search/v91_causal_quantile_density_snapback.py",
    }
    for env_name, relpath in mapping.items():
        write_env_file(env_name, relpath)


def expected_data_ready() -> bool:
    windows = ["202309_202402", "202403_202408", "202409_202502", "202503_202508"]
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    for window in windows:
        for symbol in symbols:
            p1 = ROOT / "research/development/data/v41_futures_features" / window / f"{symbol}_um15m_{window}.csv"
            p2 = ROOT / "research/development/data/v59_positioning" / window / f"{symbol}_positioning15m_{window}.csv.gz"
            if not p1.exists() or not p2.exists():
                return False
    return True


def acquire_data() -> None:
    if expected_data_ready():
        log("DATA_ALREADY_READY")
        return

    log("V41_ACQUIRE_START")
    for symbol in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
        log("V41_SYMBOL_START", symbol)
        subprocess.run(
            [sys.executable, "-u", "research/data/acquire_v41_futures_features.py", "--symbol", symbol],
            cwd=ROOT,
            check=True,
        )
        log("V41_SYMBOL_DONE", symbol)
    log("V41_ACQUIRE_DONE")

    log("V59_ACQUIRE_START")
    subprocess.run(
        [sys.executable, "-u", "research/data/acquire_v59_positioning.py"],
        cwd=ROOT,
        check=True,
    )
    log("V59_ACQUIRE_DONE")

    if not expected_data_ready():
        raise RuntimeError("acquisition completed but required V41/V59 files are missing")
    log("INPUTS_READY")


def top_near_misses(path: pathlib.Path, limit: int = 80):
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    def num(row, key):
        try:
            return float(row.get(key, 0) or 0)
        except Exception:
            return 0.0

    rows.sort(
        key=lambda row: (
            num(row, "normal_pos"),
            num(row, "normal_mintr"),
            num(row, "normal_minwr"),
            num(row, "normal_minpay"),
            num(row, "normal_minpf"),
            num(row, "normal_avg"),
            -num(row, "normal_dd"),
            num(row, "score"),
        ),
        reverse=True,
    )
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
    prepare_sources()
    acquire_data()

    OUT.mkdir(parents=True, exist_ok=True)
    mode = os.environ.get("RUN_MODE", "v88").strip().lower()
    if mode == "diag":
        log("V89_DIAG_START")
        subprocess.run(
            [sys.executable, "-u", "research/search/v89_v88_gate_diagnostics.py"],
            cwd=ROOT,
            check=True,
        )
        log("V89_DIAG_FINISHED")
        return

    if mode == "v90":
        log("V90_START")
        subprocess.run(
            [sys.executable, "-u", "research/search/v90_v88_dense_exit_screen.py"],
            cwd=ROOT,
            check=True,
        )
        log("V90_FINISHED")
        return

    if mode == "v91":
        log("V91_START")
        subprocess.run(
            [sys.executable, "-u", "research/search/v91_causal_quantile_density_snapback.py"],
            cwd=ROOT,
            check=True,
        )
        log("V91_FINISHED")
        return

    n = int(os.environ.get("V88_N", "120000"))
    seeds = [
        int(x.strip())
        for x in os.environ.get("V88_SEEDS", "88001,88002,88003,88004").split(",")
        if x.strip()
    ]
    log("V88_ALL_START", {"n": n, "seeds": seeds})
    for seed in seeds:
        run_seed(seed, n)
    log("V88_ALL_DONE", {"n": n, "seeds": seeds})


if __name__ == "__main__":
    main()
