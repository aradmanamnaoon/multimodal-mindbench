"""Command line entry points for local OR hosted execution."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .audit import audit_run
from .experiments import synthetic_experiment
from .alignment import align_trials, quality_summary
from .adapters import read_behavior, read_events
from .io import read_json, safe_input
from .schema import ClockContract
from .io import atomic_json
from .report import html_report
from .schema import ResourceLimits, SubjectSession, ValidationError
from .synthetic import generate_fixture


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mindbench", description="Nonclinical EEG+behavior source and clock audit")
    sub = p.add_subparsers(dest="command", required=True)
    synth = sub.add_parser("synthetic", help="Generate no-human-data synthetic EEG+behavior fixture")
    synth.add_argument("--output", type=Path, required=True)
    aud = sub.add_parser("audit", help="Rights-gated bounded-memory EEG+behavior ingestion")
    aud.add_argument("--root", type=Path, required=True)
    aud.add_argument("--output", type=Path, required=True)
    for name in ("subject", "session", "task", "run"):
        aud.add_argument(f"--{name}", required=True)
    aud.add_argument("--max-file-mib", type=int, default=128)
    aud.add_argument("--max-samples", type=int, default=1_000_000)
    bench = sub.add_parser("benchmark", help="Run synthetic, subject-disjoint benchmark and offline accessible explorer")
    bench.add_argument("--output", type=Path, required=True)
    bench.add_argument("--subjects", type=int, default=24)
    bench.add_argument("--trials", type=int, default=30)
    bench.add_argument("--seed", type=int, default=2026)
    bench.add_argument("--missing-rate", type=float, default=0.12)
    bench.add_argument("--bootstrap", type=int, default=300)
    al = sub.add_parser("align", help="Source-audited conservative pairing and QC; NO verified hardware sync")
    al.add_argument("--root", type=Path, required=True)
    al.add_argument("--output", type=Path, required=True)
    for name in ("subject", "session", "task", "run"):
        al.add_argument(f"--{name}", required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "synthetic":
            generate_fixture(args.output)
            print(f"Created synthetic dataset at {args.output}")
        elif args.command == "benchmark":
            result = synthetic_experiment(args.output, n_subjects=args.subjects, trials=args.trials,
                                          seed=args.seed, missing_rate=args.missing_rate, reps=args.bootstrap)
            print(json.dumps({"benchmark": str(args.output / "benchmark.json"), "dashboard": str(args.output / "index.html"),
                              "synthetic": True, "cohort_sha256": result["cohort_digest_sha256"]}))
        elif args.command == "align":
            identity = SubjectSession(args.subject, args.session, args.task, args.run)
            limits = ResourceLimits()
            manifest = audit_run(args.root, identity, limits)
            stem = identity.prefix()
            relative_dir = identity.relative_dir()
            events = read_events(safe_input(args.root, relative_dir / f"{stem}_events.tsv", limits.max_file_bytes), limits)
            behavior = read_behavior(safe_input(args.root, relative_dir / f"{stem}_beh.tsv", limits.max_file_bytes), limits)
            clock = ClockContract(**read_json(safe_input(args.root, Path("clock.json"), limits.max_file_bytes)))
            trials = align_trials(events, behavior, clock, eeg_duration_s=manifest["eeg"]["duration_seconds"])
            result = {"identity": manifest["identity"], "manifest_sha256": manifest["manifest_sha256"],
                      "qc": quality_summary(trials), "trials": [t.to_dict() for t in trials],
                      "hardware_sync_verified": False}
            atomic_json(args.output, result)
            print(json.dumps({"aligned": str(args.output), "n_trials": len(trials)}))
        else:
            identity = SubjectSession(args.subject, args.session, args.task, args.run)
            limits = ResourceLimits(max_file_bytes=args.max_file_mib * 1024 * 1024, max_samples=args.max_samples)
            manifest = audit_run(args.root, identity, limits)
            args.output.mkdir(parents=True, exist_ok=True)
            atomic_json(args.output / "manifest.json", manifest)
            (args.output / "report.html").write_text(html_report(manifest), encoding="utf-8")
            print(json.dumps({"manifest": str(args.output / "manifest.json"), "report": str(args.output / "report.html"), "sha256": manifest["manifest_sha256"]}))
    except (ValidationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"mindbench: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
