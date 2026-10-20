# Multimodal MindBench — transferable implementation checkpoint

**Date:** 2026-10-20. **External status:** NO-GO / no release. **Notion project:** https://app.notion.com/p/3fa977a963b281b880c4c0d1a1063aeb. **Epic queue:** https://app.notion.com/p/2f44e83ead8248fe9e43d551b16b3bf4. **Current first dependency:** https://app.notion.com/p/3fa977a963b281c8bb59ef50c9ffb5b0.

## What actually exists

A Python source package and self-contained offline browser report supporting rights-attested EEG ingestion (MNE EDF or explicitly non-BIDS synthetic TSV), event/response pairing, clock and artifact flags, first-two-channel EEG time-window mean extraction, group-disjoint subject split, three train-only logistic models, train-disjoint sigmoid calibration, late probability fusion with missing-modality fallback, subject-bootstrap accuracy intervals, and an interactive benchmark comparison dashboard. The numerical benchmarking dataset is *invented*, with no patient or participant recordings. Demo data/results and report are separate from source.

## Evidence and limits

- Local suite observed **36 passed, 91% line coverage**, including synthetic EDF integration and Python module import/CLI tests. E2E Chromium DOM actions passed at desktop and mobile dimensions in hosted container using `set_content`. No independently verified accessibility certification.
- No GitHub repository or commit, no actual GitHub Actions runs, and no remotely hosted app. Connector to create a repo remains unauthenticated. No release was authorized or attempted.
- No independently verified real EEG/behavior dataset license, event clock, channel harmonization or reproducibility on empirical data. This is a partial engineering implementation across all E1–E5, NOT finished verified epics.

## Resume/QA sequence

1. Confirm whether authorized GitHub repository creation is now connected. Create a **private** `aradmanamnaoon/multimodal-mindbench` repo only after identity and visibility confirmation. Use a safe feature branch and draft PR; do not publish or merge without approval.
2. Commit exactly this checkpoint, read back GitHub commit SHA, open draft PR, verify real GitHub Actions job conclusions and logs, fix any failures.
3. Perform independently verifiable source-license audit for a *small accessible, eligible* BIDS EEG+behavior dataset with matching subject groups and timebase. Pin dataset version and files, document response/label mappings and verify clocks. If unsuitable, do not claim E1 verified.
4. Run empirical E2–E4 benchmarks with true multi-subject split, compare baselines, inspect calibration and missing modality effects; document metrics without fabricating publication or clinical claims.
5. Run hosted browser E2E/accessibility/security integration, obtain release approval, then deploy properly if authorized. Only afterward update public profiles/portfolio/LinkedIn/HF with separate explicit approval.

## Local commands (for another *agent*, not the user)

- `python -m pip install -e '.[test,benchmark,edf]'`
- `python -m pytest --cov=mindbench -q`
- `mindbench synthetic --output /tmp/mindbench-demo`
- `mindbench audit --root /tmp/mindbench-demo --output /tmp/mindbench-qc --subject 01 --session 01 --task oddball --run 01`
- `mindbench align --root /tmp/mindbench-demo --output /tmp/mindbench-align.json --subject 01 --session 01 --task oddball --run 01`
- `mindbench benchmark --output /tmp/mindbench-bench --subjects 24 --trials 30 --seed 2026 --bootstrap 300`

Re-use the source archive; do not regenerate historic evidence or pretend previous tests were GitHub CI.

## Candidate dataset metadata checked

OpenNeuro `ds003061` v1.1.2 offers a CC0 auditory oddball task with responses and 13 subjects, but raw format is EEGLAB `.set` (current ingestion adapter supports EDF only) and approximately 2.26 GB. `ds007471` v1.0.0 offers CC0 joint-action EEG+behavior in BrainVision format (adapter absent, pair-level data leakage risk). Neither was downloaded. `docs/dataset-review.md` records the source URLs and explicit gaps.

## New QA checkpoint — 2026-10-20 (current test state)

All locally runnable automated test cases **PASS: 71/71**, with **91.73% measured line coverage**, and the repository now enforces 90% minimum in the configured (but unrun) GitHub Actions unit job. The local browser tests are **real headless Chromium interactions** at desktop/mobile sizes (not screenshot-only assertions). Wheel build and separate-target wheel installation + complete synthetic CLI workflow passed. Python 3.11 syntax AST checks passed (Python 3.11 interpreter execution pending). See `docs/verification.md` for exact commands and the observed clean-venv dependency limitation.

The changes include strict metadata/clock and modality feature validation, duplicate-key/nonfinite JSON rejection, modality-specific QC counts, missing-modality validity correction, unverified-origin default for arbitrary benchmark inputs, randomized event matching tests, and a CI browser-E2E job that cannot silently skip if Playwright is absent.

**No inference of project completion:** empirical real-dataset rights/source and timing validation, hosted CI run, independent scientific audit, deployment and approval gates remain open. The next actor needs an authorized private repository on the connected GitHub account before remote tests/PRs can be recorded.
