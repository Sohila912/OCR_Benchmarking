# Benchmark progress

Updated: 2026-10-28 (Africa/Cairo).

## Checkpoint

- Completed: TASK-001, TASK-002 and TASK-003 (official-source model research and laptop hardware assessment).
- Current / first incomplete task: TASK-004, PENDING. Stop at this checkpoint before dataset research; no model loading is authorized.
- Last completed checkpoint: TASK-003.
- Branch: feature/ocr-comprehensive-benchmark; origin upstream configured.
- TASK-001 commit: 5da494663bf4383321e73c54d80756c357fe3568.
- TASK-002 commit: 0db4fd4 (full hash available in Git history).
- Prior checkpoints successfully pushed to origin/feature/ocr-comprehensive-benchmark on user instruction. TASK-003 is to be committed and pushed after final checks.
- TASK-003 checkpoint subject: `feat(benchmark): assess laptop hardware and model compatibility`. Resolve the final hash using `git log -1 --format=%H -- benchmark_suite/PROGRESS.md`; verify the matching subject and remote ref. Its hash is not embedded in its own commit.

## TASK-003 outputs

Created:
- benchmark_suite/MODEL_REGISTRY.yaml (JSON syntax, valid YAML 1.2; nine research configurations, no execution authorization)
- benchmark_suite/reports/HARDWARE_PROFILE.md
- benchmark_suite/reports/HARDWARE_PROFILE.json
- benchmark_suite/reports/MODEL_HARDWARE_COMPATIBILITY.md
- benchmark_suite/reports/MODEL_CAPABILITIES.md
- benchmark_suite/reports/RESEARCH_METADATA.json (public package/file metadata, revisions, sizes and source hashes; no weights)
- benchmark_suite/scripts/check_hardware.py
- benchmark_suite/tests/test_hardware.py

Modified:
- benchmark_suite/.gitignore (preserve repeated/incomplete local observations without staging them)
- benchmark_suite/README.md (research status, report links and read-only collector usage)
- benchmark_suite/BENCHMARK_PLAN.md (approval/checkpoint and actual output files)
- benchmark_suite/PROGRESS.md
- benchmark_suite/BENCHMARK_STATUS.json

Production pipeline, installed packages, existing datasets/predictions/results and root pytest settings were not changed in this task. Task_codex.txt remains a user-owned untracked input.

## Findings and execution blockers

- i7-1165G7, 4 cores/8 threads; Windows 11 Pro 26200, AMD64; total RAM 7.74 GiB, available 0.61 GiB in the retained snapshot; free disk 24.78 GiB.
- NVIDIA MX350: 2048 MiB VRAM, CC 6.1, driver 582.67; Intel Iris Xe is integrated and its WMI memory value is not an additional dedicated VRAM bank.
- Driver advertises CUDA 13.0 ceiling; nvcc is not on PATH. Inspected existing .venv-ocr has torch 2.14.1+cpu (cuda=null), paddlepaddle 3.2.2 and no paddlepaddle-gpu. No framework runtime imports/allocations were attempted under memory pressure.
- WSL2 exists: docker-desktop running, Ubuntu stopped. No distribution or container was started/stopped by this task.
- Native Tesseract 5.4.0.20240606 and Poppler 26.07.0 exist; eng/osd present, ara absent.
- All eight local model readiness states are BLOCKED with reason BLOCKED_BY_HARDWARE at this snapshot (conservative suite available-RAM stop); their future model tasks remain PENDING. This is not an inference failure. No generic RAM floor can replace future model-specific preflight.
- Compatibility matrix marks local CPU paths LIMITED and identifies incompatible GPU routes separately: PaddleOCR-VL requires CC >=7.0, current vLLM guide >=7.5; MX350 CC 6.1 cannot be fixed through driver/WSL updates. No local model was certified runnable at the saved low-memory snapshot.
- Baidu model readiness BLOCKED pending exact implementation, account/endpoint/quotas/cost confirmation and API authorization; compatibility UNKNOWN. No API calls or credential reads.
- Surya 0.22.1 / Marker 2.0.0 use Surya 2 inference-server architecture and Transformers >=5.12.1, conflicting with installed 4.57.6. Do not assume legacy adapters/current environment work; do not upgrade production silently.
- Latest observed package metadata and current installed versions are distinguished; all memory/storage budgets are explicitly estimates. Granite Arabic is experimental. Baidu endpoint capabilities differ. No new scores/latencies or vendor-reported scores were turned into suite results.

## Successful verification

- Read TASK-001/002 plan/progress/status; branch, prior commit, artifact presence and user authorization validated.
- `git push --set-upstream origin feature/ocr-comprehensive-benchmark`: succeeded for prior checkpoints.
- Real read-only hardware collection produced complete CPU/RAM/Windows/GPU/disk/WSL/native-tool/package metadata; assertions verified exact evidence fields, CPU runtime metadata and language assets.
- `.venv-ocr\Scripts\python.exe -m pytest benchmark_suite/tests -q`: 71 passed (54 tracking + 17 hardware checks).
- After replacing a fixed Windows installation directory with the standard ProgramFiles environment directory, reran all 17 hardware tests: passed.
- `.venv-ocr\Scripts\python.exe -m ruff check benchmark_suite`: passed.
- Registry coverage/evidence/no-execution flags, complete native snapshot, all public metadata requests, Unicode report content and branch/base assertions passed.
- git diff --check passed. Final atomic checkpoint validation, staged scope and staged whitespace are verified before commit.
- No application regression tests or inference tests executed; production code unchanged. No model/dataset download, installation, CUDA/driver/WSL change, paid call or alternate environment trial occurred.

## Errors and uncertainty retained

- Initial collector prototype contained a stray leading + in its fixed PowerShell command; the native inventory probe returned ERROR and RAM UNKNOWN. Corrected the command and reran successfully. Preserved that incomplete observation under ignored reports/hardware_observations/initial_incomplete/ rather than overwriting it. Reports at the canonical paths are the successful second observation.
- Some Baidu docs timed out on repeated browser requests; accessible official product/docs establish endpoint-dependent support, but exact account rates/QPS/limits remain UNKNOWN. Do not promise free entitlement or make a paid request.
- Tesseract live releases API reported newly published 5.5.4; browser release-tag fetch returned 404. Existing 5.4.0 binary remains unchanged; new release distributable not tested.
- Full selected standard-Paddle/Docling/EasyOCR artifact totals and runtime peaks remain unverified. Registry budgets are estimates; model-specific preflight must resolve them before execution.
- Existing pinned production libraries are older than researched current releases; compatibility was researched, not upgraded or tested by inference.
- No unresolved unit-test/lint failures; model/environment readiness limitations remain explicit.

## Decisions

- Completed hardware research is a prerequisite, not permission to execute. Current memory blockers remain until a new profile and validated per-model budget pass.
- Free local priority: Tesseract and standard Paddle CPU after voluntary RAM cleanup and proper Arabic assets. Docling/Granite are restricted later CPU candidates. Original task order remains unless user approves reordering.
- Surya/Marker/Paddle-VL GPU trials need modern hardware. Optional suggested profile: Linux x64, Python 3.12, A10G/L4 24-GiB GPU, 8 vCPUs, 32-GiB RAM, 60-GiB free disk with pinned supported runtime. This is a recommendation, not a vendor minimum; cloud costs and environment approval apply. No provisioning.
- Quantization, smaller variants, resolution changes, reordered model tasks and alternate environments require disclosure and the appropriate approval; none was applied.

## Next exact actions (after approval)

1. Read Task_codex.txt, BENCHMARK_PLAN.md, this file and BENCHMARK_STATUS.json; validate TASK-003 artifacts/commit/remote state and tracker/hardware tests.
2. Complete TASK-004 only: research English and Arabic public ground-truth datasets from credible primary sources, verify versions/licenses/counts/annotation categories and propose supplementary datasets where coverage is missing.
3. Review existing curated datasets for provenance, pairing and limitations; never treat existing OCR predictions as ground truth.
4. Write benchmark_suite/datasets/DATASET_SELECTION.md with all required source/license/size/ground-truth/procedure/limitations/rationale fields and explicit download proposal. No large or restricted download before approval.
5. Update persistent records, make a task-only Git checkpoint and stop. No model loading while hardware headroom is insufficient.

## Recommended next Codex prompt

“Read Task_codex.txt, benchmark_suite/BENCHMARK_PLAN.md, benchmark_suite/PROGRESS.md and benchmark_suite/BENCHMARK_STATUS.json. Validate the TASK-003 checkpoint and Git state. I approve TASK-004 only. Research and document English/Arabic dataset selection and annotation coverage, update progress and commit the task. Do not download models or datasets or perform inference; retain the hardware blockers.”
