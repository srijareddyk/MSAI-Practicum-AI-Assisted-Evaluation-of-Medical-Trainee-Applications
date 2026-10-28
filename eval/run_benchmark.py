"""Score the fictional packets with the local MSAI reviewers and write a results file."""

from __future__ import annotations

import json
import sys
import time
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.pipeline import run_pipeline  # noqa: E402
from llm_score.llm_client import DEFAULT_MODEL  # noqa: E402

EVAL = Path(__file__).resolve().parent
GOLD_PATH = EVAL / "gold.json"
OUT_PATH = EVAL / "benchmark_results.json"
RUN_DIR = EVAL / "runs"


def letter_of(review: dict | None) -> str | None:
    if not review:
        return None
    rec = (review.get("scores") or {}).get("reviewer_recommendation")
    if isinstance(rec, str) and rec in {"A", "B", "C"}:
        return rec
    return None


def majority(letters: list[str]) -> str:
    if not letters:
        return "error"
    counts = Counter(letters)
    top = counts.most_common()
    if len(top) > 1 and top[0][1] == top[1][1]:
        return "split"
    return top[0][0]


def main() -> None:
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    model = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    pdfs = sorted((EVAL / "packets").glob("*.pdf"))
    if len(pdfs) != 12:
        raise SystemExit(f"Expected 12 PDFs, found {len(pdfs)}")

    rows: list[dict] = []
    started = time.perf_counter()
    for pdf in pdfs:
        key = pdf.stem
        label = gold["packets"][key]
        t0 = time.perf_counter()
        row: dict = {
            "file": pdf.name,
            "key": key,
            "name": label["name"],
            "intended": label["band"],
            "expect_split": label["expect_split"],
            "note": label["note"],
        }
        try:
            result = run_pipeline(
                [pdf],
                output_dir=RUN_DIR / key,
                model=model,
            )
            applicant = result.applicants[0]
            recs = {
                "A": letter_of(applicant.get("doc_a")),
                "B": letter_of(applicant.get("doc_b")),
                "C": letter_of(applicant.get("doc_c")),
            }
            present = [v for v in recs.values() if v]
            vote = majority(present)
            row.update(
                {
                    "reviewer_a": recs["A"],
                    "reviewer_b": recs["B"],
                    "reviewer_c": recs["C"],
                    "vote": vote,
                    "matched": vote == label["band"],
                    "split": len(set(present)) > 1,
                    "gpa": (applicant.get("facts") or {}).get("undergraduate_cum_gpa"),
                    "institution": (applicant.get("facts") or {}).get("undergraduate_institution"),
                    "summaries": {
                        "A": (applicant.get("doc_a") or {}).get("summary"),
                        "B": (applicant.get("doc_b") or {}).get("summary"),
                        "C": (applicant.get("doc_c") or {}).get("summary"),
                    },
                    "errors": {
                        "A": (applicant.get("doc_a") or {}).get("error"),
                        "B": (applicant.get("doc_b") or {}).get("error"),
                        "C": (applicant.get("doc_c") or {}).get("error"),
                    },
                }
            )
        except Exception as exc:  # noqa: BLE001 — keep the rest of the batch
            row.update({"vote": "error", "matched": False, "error": str(exc), "trace": traceback.format_exc()})
        row["seconds"] = round(time.perf_counter() - t0, 1)
        rows.append(row)
        OUT_PATH.write_text(
            json.dumps(
                {
                    "model": model,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "rows": rows,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            f"{key}: intended {label['band']} vote {row.get('vote')} "
            f"A {row.get('reviewer_a')} B {row.get('reviewer_b')} C {row.get('reviewer_c')} "
            f"({row['seconds']}s)",
            flush=True,
        )

    votes = Counter(r.get("vote") for r in rows)
    matched = sum(1 for r in rows if r.get("matched"))
    summary = {
        "model": model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.perf_counter() - started, 1),
        "pass_interview_A": votes.get("A", 0),
        "review_B": votes.get("B", 0),
        "fail_do_not_advance_C": votes.get("C", 0),
        "split_votes": votes.get("split", 0),
        "errors": votes.get("error", 0),
        "exact_band_matches": matched,
        "packets": len(rows),
        "rows": rows,
    }
    OUT_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in summary if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()
