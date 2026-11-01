# Windows launcher and CLI verification — TASK-008

Completed 2026-11-01 (Africa/Cairo). Shared tools only: no OCR model was
downloaded, installed, initialized or executed. No dependency installation,
environment switch, paid API or cloud provisioning occurred.

Implemented cli.py, scripts/run_benchmark.bat, configs/models.json and
tests/test_cli.py. README.md documents all 13 options, automation commands,
current pending setup behavior, isolated environments, logs and exit codes.
scripts/*.bat has explicit CRLF checkout handling. preflight.authorize_model is
the shared CLI/runner approval gate; authorize delegates to it. The existing
runner approval test uses a fixed temporary pre-model checkpoint, so later real
user approvals do not invalidate the negative test.

| Check | Result |
|---|---|
| CLI tests | 43 passed, using fakes/blocked candidates only |
| Full benchmark suite | 198 passed |
| Ruff | Passed |
| Python `-S ... --help` | Passed without site packages/model imports |
| Batch launcher --help | Passed using the existing detected .venv-ocr interpreter |
| Batch default menu + option 13 | Exact 13 options displayed; clean exit |
| Real cmd.exe path/exit tests | Spaces and ampersand path; arguments and exit codes 0/7 preserved |
| `check-environment --json` | Existing direct shared dependency pins match; metadata/native probes only |
| `validate-datasets --json` | All 1,155 frozen source/reference pairs validated; no network/inference |
| Single-model approval gates | All nine pending candidates refused setup/smoke/run; no factory import or runner call |
| Automation safety | All/repeated models, unrecognized languages/flags and resume overrides rejected |
| Offline evaluation/report routing | No active model/factory/runner needed; shared evaluator used |
| Comparison commands | Explicit PENDING TASK-018/019, exit 4; no fabricated artifacts |
| Error/recovery routing | Nonzero failed-document result; saved run identified after evaluation failure |
| Coordinator state | Read commands/negative execution attempts preserve approvals/status |

The CLI tests simulate future approved registrations at the runner boundary.
They are not real model evaluations. Actual process-death recovery and prediction
cache/offline evaluation semantics remain covered by the TASK-007 fixture tests.

Initial native environment observation during validation: 8,311,836,672 bytes total
RAM; 827,138,048 bytes available (approximately 0.77 GiB); MX350 with 2,048 MiB
dedicated VRAM and compute capability 6.1. Torch build metadata remains CPU-only,
and no GPU Paddle distribution was found. Free resources are a snapshot and must
be rechecked. The available RAM is below the 2-GiB model-loading policy floor;
passing shared dependency checks does not certify any model's compatibility.
A later Surya readiness check observed 1,172,176,896 bytes (~1.09 GiB) free
and returned BLOCKED/exit 3 for missing approval/implementation/environment plus
the hardware blocker, without importing a factory. Both observations remain below
the 2-GiB floor. The historical hardware report is preserved; command observations live in ignored
logs/cli with unique IDs rather than replacing prior evidence.

Current catalog registrations are all null/pending. No model installation action
or factory exists in this checkpoint. Setup currently checks an approved existing
isolated setup; actual setup belongs to each separately approved model task.
Selecting a menu option never grants approval or clears a hardware blocker.
Comparison implementation and comparative/final visualization remain later tasks.

Reproduce from the repository root:

```powershell
.venv-ocr\Scripts\python.exe -m pytest benchmark_suite/tests/test_cli.py -q
.venv-ocr\Scripts\python.exe -m pytest benchmark_suite/tests -q
.venv-ocr\Scripts\python.exe -m ruff check benchmark_suite
.\benchmark_suite\scripts\run_benchmark.bat --help
.venv-ocr\Scripts\python.exe -m benchmark_suite.cli check-environment --json
.venv-ocr\Scripts\python.exe -m benchmark_suite.cli validate-datasets --json
```

Stop at TASK-008. TASK-009 (Surya) requires its own explicit user approval,
current official source/version/license review and successful hardware assessment
before any installation, asset download or inference. Existing blockers remain.
