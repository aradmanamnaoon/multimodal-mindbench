# Release approval and audit gate

**Decision: NO-GO as of 2026-10-20.** This document is not authorization for publication.

| Requirement | Local evidence | Gate state |
|---|---|---|
| E1 data adapter, rights attestation, provenance | unit & synthetic EDF integration tests | locally tested; real rights verification absent |
| E2 one-to-one clock-aware pairing, QC, missing masks | synthetic unit tests + `mindbench align` | locally tested; external hardware clock not verified |
| E3 behavior-only and EEG-only baselines, group-safe split | seeded simulated-cohort end-to-end tests | locally tested; empirical EEG baseline not evaluated |
| E4 early/late fusion, ablation, calibration, uncertainty | simulated-cohort end-to-end tests | locally tested; no empirical validation |
| E5 offline accessible model explorer & JSON export | generated HTML checked via automated markup assertions | locally built; no browser E2E/accessibility audit |
| GitHub source commit, draft PR, issue, actual hosted CI | none | **blocked: creation permission** |
| Real eligible dataset, rights, event mapping and provenance | desk-researched only | **blocked** |
| Real public demo, verified end-to-end workflows, security | not run | **blocked: consent/release approval** |
| GitHub profile, portfolio, LinkedIn, Hugging Face | untouched | **correctly deferred** |

## Approvals and safeguards

Do not merge/publish this project, turn a synthetic score into a paper result, include individual EEG/behavior in the report, or deploy to a public URL without documented authorization. Do not call the five epics "Verified Done" until their source rights, real-data, hosted CI and independent scientific gates are passed.

All source and demo artifacts are portable local files. A new **private** `aradmanamnaoon/multimodal-mindbench` repository and GitHub Actions permissions are needed to maintain durable, reviewable commits and hosted CI. The installed GitHub connector cannot create repositories, while the separate Composio GitHub connection has not been authorized. Do not request secrets or local setup.
