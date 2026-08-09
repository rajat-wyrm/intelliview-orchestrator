"""
tests/benchmark_digest_pipeline.py

Standalone performance benchmark for the Digest Notifications pipeline.
This reproduces the timing/size figures quoted in Section 6.2
(Performance Metrics) of the intern task report.

Not part of the automated test suite (test_digest_notifications.py) --
this is a manual benchmarking script, run on demand, not on every test run.

Usage:
    python tests/benchmark_digest_pipeline.py
    python tests/benchmark_digest_pipeline.py --runs 500 --ref-date 2026-06-27

Notes / limitations (see report Section 6.2 for full discussion):
  - Measured against the existing mock dataset (data/interviews.json,
    9 records as of this writing), capped at DIGEST_BATCH_SIZE (default 5).
  - Single-process, non-concurrent timing on whatever machine this is run
    on -- not a load test and not representative of production hardware.
  - Uses Python's built-in `timeit` module, which runs each statement
    repeatedly and returns total elapsed time; we divide by the run count
    to get an average per-call time.
"""

import argparse
import os
import sys
import timeit

SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, os.path.abspath(SRC_DIR))

from digest import _build_payload, get_upcoming_interviews
from renderer import render_digest_html, render_digest_text


def run_benchmark(runs: int, ref_date: str) -> None:
    print(f"Benchmarking digest pipeline ({runs} runs, ref_date={ref_date})\n")

    # ── Stage 1: read + filter interviews.json ──
    t1 = timeit.timeit(
        lambda: get_upcoming_interviews(ref_date)[0],
        number=runs,
    )
    print(f"Read + filter interviews.json      : {(t1 / runs) * 1000:.3f} ms avg")

    # ── Stage 2: build payload (read + group + cap) ──
    t2 = timeit.timeit(
        lambda: _build_payload("daily", ref_date),
        number=runs,
    )
    print(f"Build digest payload               : {(t2 / runs) * 1000:.3f} ms avg")

    # Build one payload to use for the render stages below
    payload = _build_payload("daily", ref_date)
    unsubscribe_url = "https://example.com/unsubscribe?user_id=u-benchmark"

    # ── Stage 3: render HTML body ──
    t3 = timeit.timeit(
        lambda: render_digest_html(payload, unsubscribe_url=unsubscribe_url),
        number=runs,
    )
    print(f"Render HTML body (Jinja2)          : {(t3 / runs) * 1000:.3f} ms avg")

    # ── Stage 4: render plain-text fallback ──
    t4 = timeit.timeit(
        lambda: render_digest_text(payload, unsubscribe_url=unsubscribe_url),
        number=runs,
    )
    print(f"Render plain-text fallback          : {(t4 / runs) * 1000:.3f} ms avg")

    # ── Stage 5: full end-to-end pipeline (build + html + text) ──
    def full_pipeline():
        p = _build_payload("daily", ref_date)
        render_digest_html(p, unsubscribe_url=unsubscribe_url)
        render_digest_text(p, unsubscribe_url=unsubscribe_url)

    t5 = timeit.timeit(full_pipeline, number=runs)
    print(
        f"End-to-end (build + HTML + text)   : {(t5 / runs) * 1000:.3f} ms avg per digest"
    )

    # ── Output sizes (not timing, but useful alongside it) ──
    html = render_digest_html(payload, unsubscribe_url=unsubscribe_url)
    text = render_digest_text(payload, unsubscribe_url=unsubscribe_url)
    print(f"\nHTML output size                   : {len(html.encode('utf-8'))} bytes")
    print(f"Plain-text output size             : {len(text.encode('utf-8'))} bytes")
    print(f"Interviews included in this digest : {payload.total_count}")

    print(
        "\nNote: these figures reflect the current mock dataset and a "
        "single-process, non-concurrent run on this machine. They are "
        "not load-test or production-scale results."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Benchmark the digest generation pipeline"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=200,
        help="Number of timeit runs per stage (default: 200)",
    )
    parser.add_argument(
        "--ref-date",
        default="2026-06-27",
        help="Reference date YYYY-MM-DD (default: 2026-06-27)",
    )
    args = parser.parse_args()

    run_benchmark(runs=args.runs, ref_date=args.ref_date)
