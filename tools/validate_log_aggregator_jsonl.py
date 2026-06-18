#!/usr/bin/env python3
"""Validate JSONL output from tools/log_aggregator.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGGREGATOR = ROOT / "tools" / "log_aggregator.py"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="log-aggregator-jsonl-") as tmp:
        workspace = Path(tmp)
        app_log = workspace / "app.log"
        nginx_log = workspace / "nginx.log"
        output = workspace / "records.jsonl"

        app_log.write_text(
            "\n".join(
                [
                    '{"timestamp":"2024-01-01T00:00:03Z","level":"ERROR","service":"api","message":"late json error","request_id":"r-2"}',
                    "",
                    "2024-01-01 00:00:01 INFO [worker] early text message",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        nginx_log.write_text(
            '127.0.0.1 - - [01/Jan/2024:00:00:02 +0000] "GET /health HTTP/1.1" 200 12 "-" "curl"\n',
            encoding="utf-8",
        )

        subprocess.run(
            [
                sys.executable,
                str(AGGREGATOR),
                "--input",
                str(workspace / "*.log"),
                "--format",
                "jsonl",
                "--output",
                str(output),
            ],
            cwd=ROOT,
            check=True,
        )

        records = [
            json.loads(line)
            for line in output.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    assert len(records) == 4, records
    assert all(set(["timestamp", "level", "source", "message", "metadata"]).issubset(record) for record in records)

    timestamped = [record for record in records if record["timestamp"] is not None]
    assert [record["timestamp"] for record in timestamped] == sorted(record["timestamp"] for record in timestamped)
    assert [record["source"] for record in timestamped] == ["worker", "nginx", "api"]

    warnings = [record for record in records if record["metadata"].get("warning")]
    assert len(warnings) == 1, records
    assert warnings[0]["level"] == "warn"
    assert warnings[0]["source"] == "log_aggregator"
    assert warnings[0]["metadata"]["line_number"] == 2

    print("log aggregator JSONL validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
