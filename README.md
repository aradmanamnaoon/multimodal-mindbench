# Multimodal MindBench

**EEG + behavior research benchmark — E1–E5 locally implemented research-software slices, NOT VERIFIED/RELEASED.**

The E1 data foundation makes EEG/behavior research inputs auditable, while E2–E5 add separate synthetic-data alignment, scientific evaluation, fusion and browser-review slices. It answers four concrete questions: **(1) may the input be used? (2) what exact bytes were analyzed? (3) which acquisition clock is being assumed? (4) can the input be inspected without loading an entire recording into RAM?**

**Status:** E1–E5 offline development implementations with outstanding scientific and release gates in `docs/release-gate.md`; local test evidence in `docs/verification.md`. GitHub-hosted CI has *not* been run unless linked in a separate audit. This is non-diagnostic research infrastructure. Real dataset correctness and rights must be independently checked; there are no performance or clinical claims.

## Demonstration

```bash
python -m pip install -e '.[test]'
mindbench synthetic --output /tmp/mindbench-synthetic
mindbench audit --root /tmp/mindbench-synthetic --output /tmp/mindbench-audit --subject 01 --session 01 --task oddball --run 01
mindbench align --root /tmp/mindbench-synthetic --output /tmp/mindbench-alignment.json --subject 01 --session 01 --task oddball --run 01
python -m pip install -e ".[test,benchmark]"
mindbench benchmark --output /tmp/mindbench-synthetic-benchmark --subjects 24 --trials 30 --bootstrap 300
python -m pytest -q
```

Outputs: `manifest.json` (versioned, content SHA-256, rights, summary measurements, warnings), `report.html` (keyboard-compatible responsive offline audit, no raw signal embedded), `alignment.json` (one-to-one conservative QC), plus `benchmark.json` and `index.html` (accessible interactive offline evaluation explorer, simulated data only). **For the synthetic adapter only**, two idealized sinusoidal channels and 3 stimulus/response pairs are created. The timestamps are *programmatically invented* and cannot validate hardware synchronization or scientific inference.

## Import contract

A dataset root must have `rights.json` and `clock.json`; expected run file pattern:

```text
rights.json
clock.json
sub-01/ses-01/eeg/sub-01_ses-01_task-oddball_run-01_eeg.json
sub-01/ses-01/eeg/sub-01_ses-01_task-oddball_run-01_eeg.edf  # optional real EDF adapter
sub-01/ses-01/eeg/sub-01_ses-01_task-oddball_run-01_events.tsv
sub-01/ses-01/eeg/sub-01_ses-01_task-oddball_run-01_beh.tsv  # MindBench extension
```

`*_eeg.json` includes `SamplingFrequency` and `MindBenchAdapter` (`edf-mne` for EDF or `synthetic-tsv` for fixture). Real EDF support requires `pip install '.[edf]'` **on a permitted hosted runner**, no user laptop prerequisites. EDF uses `mne.io.read_raw_edf(..., preload=False)` with chunked `get_data()`. The fixture-only EEG TSV is **not BIDS raw-EEG compliant**. Event `onset` and `duration` are seconds from EEG acquisition start (per BIDS); the MindBench behavioral extension also uses acquisition-relative `onset` only when its contract is verified. See `docs/scientific-contract.md`.

### Rights are a gate, not an automatic license verifier

`rights.json` MUST contain `license`, `source_url`, `dataset_id`, `dataset_version`, `citation`, `attested_by`, `synthetic`. Supported declarations: `CC0-1.0`, `CC-BY-4.0`, `synthetic`; all others rejected. The importer is accountable for verifying the source's actual terms; a spoofed JSON license cannot be detected by this package. No redistribution of data is implied. `clock.json` records behavioral origin as either `acquisition_start` or `unverified`, and `hardware_synced` as a claimant-provided flag; the audit **always** reports `hardware_sync_verified=false` until independent verification functionality ships.

## Current quality and privacy boundaries

- Strict BIDS-compatible subject/session/task/run labels; input constrained to dataset root and symlinks rejected.
- Streamed TSV; optional lazily chunked EDF; bounded maximum bytes, rows, channels and events.
- Finite EEG values, contiguous indexed synthetic samples, ordered finite events, nonnegative durations, recorded out-of-coverage flags.
- Immutable source file SHA-256 and deterministic canonical manifest hash, atomic JSON output.
- Reports contain limited summary values and identifiers only, not raw EEG or behavior responses. Identifiers should be pseudonymous and rights to store them must be checked.
- **No hidden claim** of hardware clock validation, empirical modeling, complete artifact removal, independent usability review or deployment. Separate prototype modules demonstrate one-to-one event matching, group-safe synthetic splits, fusion models and calibration. See `docs/experimental-evaluation.md`.

## Reviewer checkpoints

1. Check the scientific contract and whether `rights.json` is enough for desired data governance.
2. Run/link actual hosted CI once a dedicated repository is connected.
3. Accept E1 only after a licensed real EEG+behavior dataset ingest or documented explicit waiver, MNE EDF test, source audit and CI evidence.

## References (primary standards; no paper result claims)

- BIDS events and EEG: https://bids-specification.readthedocs.io/en/stable/modality-specific-files/electroencephalography.html
- BIDS schema columns: https://github.com/bids-standard/bids-specification/blob/master/src/schema/objects/columns.yaml
- MNE EDF reader: https://mne.tools/stable/generated/mne.io.read_raw_edf.html
- OpenNeuro terms: https://docs.openneuro.org/faq
- DANDI license policy: https://docs.dandiarchive.org/terms-policies/policies/

## Roadmap

**Outstanding for full E1–E5 closure:** real rights-inspected source-aligned EEG+behavior corpus, objective clock verification and site/session channel harmonization, empirical grouped baselines/fusion/ablation, hosted CI and logged browser accessibility audit, independent scientific review, and explicitly authorized release. All 5 epics have offline working prototype slices; none meets the final acceptance gate. Read `docs/release-gate.md`.

## License

Project source code is MIT licensed (`LICENSE`). Dataset rights are independent and must not be inferred from the software license.

## Latest automated QA

For a fully provisioned *hosted* test runner, use
`MINDBENCH_REQUIRE_BROWSER=1 PYTHONPATH=src python -m pytest -q --cov=mindbench --cov-fail-under=90`.
The 2026-10-20 local checkpoint recorded **71 passed and 91.73% coverage** including headless Chromium desktop/mobile interaction tests; it does **not** establish real-data scientific validity or remote GitHub CI status. The direct `benchmark()` API labels arbitrary input features **unverified**; `mindbench benchmark` explicitly generates synthetic data and labels that output accordingly. Exact verification protocol: [`docs/verification.md`](docs/verification.md).
