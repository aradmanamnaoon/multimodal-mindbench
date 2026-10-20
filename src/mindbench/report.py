"""Accessible, static, offline HTML report; does not embed raw EEG or event rows."""
from __future__ import annotations

from html import escape
from typing import Any


def html_report(manifest: dict[str, Any]) -> str:
    eeg = manifest["eeg"]
    audit = manifest["synchronization_audit"]
    ids = manifest["identity"]
    rows = [
        ("Dataset ID", manifest["rights"]["dataset_id"]),
        ("License (importer asserted)", manifest["rights"]["license"]),
        ("Subject", ids["subject"]),
        ("Session", ids["session"]),
        ("Task", ids["task"]),
        ("Recording", eeg["adapter"]),
        ("Sampling frequency (Hz)", eeg["sampling_hz"]),
        ("Channels", len(eeg["channels"])),
        ("Samples", eeg["n_samples"]),
        ("EEG duration (seconds)", eeg["duration_seconds"]),
        ("Stimulus events", manifest["event_count"]),
        ("Behavioral responses", manifest["behavior_count"]),
        ("Hardware synchronization independently verified", "No"),
        ("Manifest SHA-256", manifest["manifest_sha256"]),
    ]
    body = "\n".join(f"<tr><th scope=\"row\">{escape(str(k))}</th><td>{escape(str(v))}</td></tr>" for k, v in rows)
    warnings = audit["warnings"] or ["No data-level boundary warnings; hardware synchronization remains unverified"]
    issues = "\n".join(f"<li>{escape(w)}</li>" for w in warnings)
    limitations = "\n".join(f"<li>{escape(w)}</li>" for w in manifest["limitations"])
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Multimodal MindBench — Source & Clock Audit</title>
<style>
:root{{color-scheme:light}} body{{font:1rem/1.55 system-ui,sans-serif;max-width:64rem;margin:2rem auto;padding:0 1rem;color:#172331;background:#fff}}
h1,h2{{line-height:1.25}} main{{min-width:0}} .skip:focus{{position:static}} .skip{{position:absolute;left:-9999px}}
table{{border-collapse:collapse;width:100%}} th,td{{padding:.65rem;text-align:left;border-bottom:1px solid #b9c3cc;overflow-wrap:anywhere}}th{{width:55%}}
.alert{{border-left:4px solid #8b5717;padding:.35rem 1rem;background:#fff7e8}}a:focus-visible{{outline:3px solid #1757a8;outline-offset:3px}}
@media(max-width:500px){{body{{margin:1rem auto}}th,td{{display:block;width:auto;padding:.3rem}}td{{padding-bottom:1rem}}}}
</style></head><body><a class="skip" href="#main">Skip to audit</a>
<main id="main"><h1>Multimodal MindBench</h1>
<p>Scientific data-layer audit — research software only. Not diagnostic or clinically validated.</p>
<h2>Source and acquisition</h2><table><caption>Ingestion summary</caption><tbody>{body}</tbody></table>
<section class="alert" aria-label="Clock and quality warnings"><h2>Clock and quality warnings</h2><ul>{issues}</ul></section>
<h2>Scientific limitations</h2><ul>{limitations}</ul>
<p>Generated without external scripts, fonts or third-party telemetry. No underlying EEG time series included.</p>
</main></body></html>'''
