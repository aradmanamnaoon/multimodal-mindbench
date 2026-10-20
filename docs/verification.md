# Verification checkpoint — 2026-10-20

- Stage: **P09-E1 partial development**, **NOT VERIFIED DONE**, **NOT a release**.
- Environment: ChatGPT hosted container, Python 3.13.5, pytest 9.0.2, MNE 1.11.0.
- Command: `PYTHONPATH=src python -m pytest --cov=mindbench --cov-report=term-missing -q`
- Observed outcome: **23 passed in 7.17s**, **90% line coverage (399 statements, 39 missed)** for `src/mindbench`.
- A second no-MNE unit run before EDF test: **22 passed in 0.16s**.
- Programmatic synthetic CLI smoke check: produced `manifest.json` and `report.html` for sub-01/ses-01/oddball/run-01 with EEG 300 samples, 2 channels, 3 events, 3 behavioral responses. `hardware_sync_verified` = false. Full manifest digest printed by that smoke run: `3960455259330089239c93bb473a4b43fa02a12ddcced0f94e5e61339948eb0c`.
- Python compilation: `python -m compileall -q src` succeeded.
- Test EDF fixture: generated entirely synthetic EDF for MNE reader, not externally licensed human data.
- GitHub Actions workflow created but **not executed**: no dedicated MindBench repository exists in connected GitHub account; connected direct GitHub plugin has no repository creation action. Composio GitHub toolkit not authorized. **No GitHub commit, PR, issue, workflow run, deployment or public release** has occurred.
- Real-dataset audit: research desk check only; candidate `ds008496` lists CC0 on OpenNeuro but paired behavior input and physical synchronization remain unverified. **No external human recordings have been ingested**.

## Unresolved acceptance gates

1. Create/reuse authorized separate private MindBench repository, push code on review branch, open draft PR and issue, run hosted GitHub Actions and inspect logs.
2. Integrate and independently check at least one rights-verified small real EEG recording with behavior/event provenance, ensuring dataset metadata and file license match the catalog.
3. Audit event/behavior clock origin and recording semantics against source, document actual limitations, review accessibility and data governance.
4. Do not mark E1 `Verified Done` until all evidence is captured; downstream E2 stays dependent.

## Continued offline implementation checkpoint (2026-10-20)

- Python 3.13.5 in hosted ChatGPT container; sklearn 1.8.0, MNE 1.11.0, pytest 9.0.2.
- Exact command: `PYTHONPATH=src python -m pytest --cov=mindbench --cov-report=term -q`: **36 passed, 91% line coverage** (815 statements, 72 misses); run took 3.18 seconds. No external/human data ingested.
- Synthetic cohort (`seed=2026`, 24 subjects, 30 simulated trials/subject, 300 subject-bootstrap draws), generated `benchmark.json` and standalone `index.html`; cohort SHA-256 `feef29680294574f6dfc7a21edf97c4d7b193e736c829fb235ffe5663758a843`.
- Conservative E2 stimulus-response pairing CLI ran on original three-trial synthetic dataset and generated `alignment.json` with three trials.
- Headless local Chromium through Playwright `page.set_content` executed interactive metric/scope filters, verified 4 complete-case and 1 missing-modality cards, and captured desktop and mobile screenshots without JS errors or mobile page overflow. Direct `file://` navigation was blocked by sandbox policy; this browser test validates DOM/UI logic, not a hosted deployment or full WCAG conformance.
- `python -m compileall -q src tests` passed.
- No GitHub commit, PR, issue or hosted Actions CI occurred because repository creation is not authorized. No software release, browser-hosted demo, public portfolio, external message or Hugging Face publication.

### Reproducibility and candid limitations

Local evidence runs may not reproduce across other Python/sklearn/MNE versions without exact dependency lock. CI YAML includes Python 3.11/3.13 and EDF checks, but workflow is **not executed** until committed on GitHub. Real-data rights, clinical validity, external sampling clocks and subject-generalization on humans are unverified. Numerical simulation metrics are NOT evidence of improved EEG+behavior prediction in humans. This is an engineering experiment, not an original empirical finding.

## Expanded reproducible QA — 2026-10-20 (latest; supersedes earlier local numbers)

- **Exact command:** `MINDBENCH_REQUIRE_BROWSER=1 PYTHONPATH=src python -m pytest -q --cov=mindbench --cov-fail-under=90 --cov-report=term`
- **Observed environment:** Python 3.13.5, pytest 9.0.2, Playwright with locally installed Chromium, MNE 1.11.0, scikit-learn 1.8.0.
- **Observed outcome:** **71 passed; 0 failed; 91.73% line coverage** (859 statements, 71 missed), in 5.77 s. The 90% coverage gate passed. Two actual headless Chromium tests ran at 1440×900 and 375×812, exercising keyboard skip navigation, scope/metric controls, download generation, no horizontal overflow and no JavaScript errors or external network requests.
- **Added scientific/defensive QA:** negative tests for malformed rights/clock provenance, duplicate/NaN JSON, feature count and finiteness, numeric labels, missing modality QC, and randomized one-to-one response matching. A discovered invalid-label validation-order error was corrected; direct benchmark API now conservatively marks arbitrary feature origin as **unverified**, while only the explicitly synthetic-experiment entry point claims synthetic provenance.
- **Installed package check:** `pip wheel --no-deps --no-build-isolation` produced a `.whl`; package was installed from that wheel to a separate target and executed from `/tmp`. Synthetic EEG fixture → audited manifest → trial alignment → 24-subject/30-trial synthetic multimodal benchmark → offline browser report assertions all passed. A separate clean environment without the optional benchmark extra correctly rejected benchmark execution with the documented dependency error; this is not a library defect.
- **Source syntax:** Python 3.11 grammar parsed all 22 Python source/test files; `compileall` succeeded. The application has **not** been executed under a Python 3.11 interpreter.
- **CI workflow:** configured three jobs: Python 3.11/3.13 unit + coverage gate, synthetic EDF integration, and Playwright Chromium browser checks. **Workflow has never run on GitHub** because no authorized target repository exists. These are local tests, not hosted-CI verification.
- **Scientific gate:** tests are synthetic and prove software invariants only. **No empirical EEG/behavior data imported, no genuine hardware clock verified, no external scientific validity established, no deployment and no public release.** Do not mark E1–E5 `Verified Done` solely because automated tests are green.
