"""Synthetic fixtures only: never construct an OCR model or download assets."""

import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from OCR.schemas import BoundingBox, OCRBlock, OCRPage, OCRResult
from benchmark_suite.adapters.base import BenchmarkAdapter, RawOutput
from benchmark_suite.adapters.existing import ExistingProviderAdapter
from benchmark_suite.dataset_io import digest
from benchmark_suite.runners import preflight
from benchmark_suite.runners.cache import IntegrityError, coordinator_lock, fingerprint, json_bytes
from benchmark_suite.runners.evaluate import evaluate_record, pixels
from benchmark_suite.runners.report import evaluate_run
from benchmark_suite.runners.run import gpu_bytes, run
from benchmark_suite.runners.schemas import AdapterSpec, Capabilities, Prediction, Requirements, RunConfig, Table

SUITE = Path(__file__).resolve().parents[1]


def observed(root):
    return {"ram_available_bytes": 8*1024**3, "disk_free_bytes": 20*1024**3, "gpus": [],
            "os": "fixture-os", "cpu": "fixture-cpu", "python": "fixture", "logical_cpus": 1, "physical_cpus": 1}


def spec():
    return AdapterSpec(model_id="fixture", model_revision="fixture-v1", adapter_revision="fixture-v1",
        capabilities=Capabilities(text=True, layout=True, reading_order=True),
        label_map={"text": "paragraph"}, raw_level="synthetic-fixture",
        requirements=Requirements(compatibility="COMPATIBLE", evidence="Unit-test fixture only", ram_bytes=0, disk_bytes=0))


def config():
    return RunConfig(purpose="fixture", device="cpu", precision="fixture", preprocessing={"resize": "none"})


def fixture_root(root, count=3):
    root = Path(root)
    (root/"datasets/manifest").mkdir(parents=True)
    (root/"configs").mkdir()
    policy = json.loads((SUITE/"configs/evaluation.json").read_bytes())
    policy["statistics"]["bootstrap_samples"] = 50
    (root/"configs/evaluation.json").write_bytes(json_bytes(policy))
    records = []
    for index in range(count):
        language = "ar" if index == 2 else "en"
        image = root/f"image-{index}.fixture"
        image.write_bytes(f"fixture image {index}".encode())
        ref = root/f"reference-{index}.json"
        content = "مرحبا" if language == "ar" else json.dumps({"page_info": {"width": 100, "height": 100},
            "layout_dets": [{"anno_id": "r", "category_type": "text_block", "text": "hello", "ignore": False,
                             "poly": [0, 0, 100, 0, 100, 20, 0, 20], "order": 1}]})
        ref.write_text(content, encoding="utf-8")
        records.append({"document_id": f"fixture-{index}", "dataset_name": "fixture", "dataset_version": "1"*40,
            "source_path": image.name, "file_hash": digest(image), "language": language, "document_category": None,
            "page_count": 1, "width": 100, "height": 100, "ground_truth_reference": ref.name, "reference_hash": digest(ref),
            "upstream_split": "fixture", "source_document_id": None, "source_grouping_status": "UNKNOWN",
            "annotation_types": ["fixture-independent-truth"], "evaluation_capabilities": ["text"] if language == "ar" else ["text", "layout", "reading_order"],
            "reference_warnings": [], "split": "development", "split_group_id": str(index), "source_metadata": {}})
    manifest = root/"datasets/manifest/development.jsonl"
    manifest.write_bytes(b"".join(json_bytes(r)+b"\n" for r in records))
    (manifest.parent/"PROVENANCE.json").write_bytes(json_bytes({"manifest_sha256": {manifest.name: digest(manifest)}}))
    return root, manifest, records


class Fake(BenchmarkAdapter):
    def __init__(self, root, selected=None, fail=None, bad_identity=False, init_fail=False):
        self.root, self.selected, self.fail = Path(root), selected or spec(), fail
        self.bad_identity, self.init_fail = bad_identity, init_fail
        self.initialized = self.cleaned = 0

    def initialize(self, config):
        self.initialized += 1
        if self.init_fail:
            raise RuntimeError("fixture initialization failure")

    def predict(self, document):
        with (self.root/"calls.log").open("a", encoding="utf-8") as stream:
            stream.write(document.document_id+"\n")
        if self.fail == document.document_id:
            raise ValueError("fixture prediction failure")
        value = "مرحبا" if document.source_metadata["language"] == "ar" else "hello"
        return RawOutput(json_bytes({"id": document.document_id, "text": value}), "application/json")

    def normalize_output(self, raw, document):
        value = json.loads(raw.data)["text"]
        bounds = BoundingBox(x_min=0, y_min=0, x_max=100, y_max=20, units="pixels", origin="top_left")
        return Prediction(result=OCRResult(document_id="wrong" if self.bad_identity else document.document_id,
            filename=document.filename, provider="fixture", text=value, pages=[OCRPage(page_number=1, text=value,
            width=100, height=100, dimension_units="pixels", blocks=[OCRBlock(block_id="p", block_type="text", text=value,
            bounding_box=bounds, confidence=.9, reading_order=0)])]), text_format="plain", coordinate_notes="fixture original pixels")

    def get_capabilities(self):
        return self.selected.capabilities

    def get_metadata(self):
        return self.selected

    def cleanup(self):
        self.cleaned += 1


def calls(root):
    path = root/"calls.log"
    return path.read_text().splitlines() if path.exists() else []


def run_fake(root, manifest, selected=None, settings=None, **kw):
    return run(root, manifest, selected or spec(), settings or config(), lambda: Fake(root, selected), probe=observed, **kw)


def test_lifecycle_raw_schema_and_phase_records(tmp_path):
    root, manifest, _ = fixture_root(tmp_path)
    adapter = Fake(root)
    directory = run(root, manifest, spec(), config(), lambda: adapter, probe=observed)
    assert adapter.initialized == adapter.cleaned == 1
    assert len(calls(root)) == 3
    docs = [json.loads(p.read_bytes())["metadata"] for p in (directory/"documents").glob("*/bundle.json")]
    assert sum(d["inference_temperature"] == "cold" for d in docs) == 1
    assert sum(d["inference_temperature"] == "warm" for d in docs) == 2
    assert all(d["inference_seconds"] >= 0 and d["sampled_peak_rss_bytes"] > 0 for d in docs)
    for p in (directory/"documents").glob("*/raw.bin"):
        assert json.loads(p.read_bytes())["text"] in {"hello", "مرحبا"}


def test_cache_hit_never_initializes_or_measures_fresh_speed(tmp_path):
    root, manifest, _ = fixture_root(tmp_path)
    first = run_fake(root, manifest)
    def forbidden():
        pytest.fail("Cache hit must not construct an adapter")
    second = run(root, manifest, spec(), config(), forbidden, probe=observed)
    assert first != second and len(calls(root)) == 3
    output = evaluate_run(root, second)
    perf = (output/"performance_metrics.csv").read_text()
    assert "fresh_inference_seconds" in perf
    metrics = json.loads((output/"metrics.json").read_bytes())
    assert metrics["cached_documents"] == 3
    assert all(json.loads(p.read_bytes())["metadata"]["cache_hit"] for p in (second/"documents").glob("*/bundle.json"))


def test_real_process_death_after_cache_does_not_repeat_inference(tmp_path):
    root, manifest, _ = fixture_root(tmp_path)
    # Kill only this deliberately spawned fixture worker. Kernel releases lock;
    # successful atomic cache publication is the recovery evidence.
    script = """
import os,runpy,sys
from pathlib import Path
d=runpy.run_path('benchmark_suite/tests/test_runner.py')
root=Path(sys.argv[1])
d['run_fake'](root,root/'datasets/manifest/development.jsonl',after_cache=lambda key: os._exit(77))
"""
    result = subprocess.run([sys.executable, "-c", script, str(root)], timeout=30, check=False)
    assert result.returncode == 77
    directory = next((root/"results/fixture").iterdir())
    assert not (directory/"completion.json").exists()
    assert len(calls(root)) == 1
    run_fake(root, manifest, resume=directory)
    assert calls(root) == ["fixture-0", "fixture-1", "fixture-2"]
    assert (directory/"completion.json").exists()


def test_failure_is_retained_not_cached_and_retry_reuses_successes(tmp_path):
    root, manifest, _ = fixture_root(tmp_path)
    bad = Fake(root, fail="fixture-1")
    directory = run(root, manifest, spec(), config(), lambda: bad, probe=observed)
    assert json.loads((directory/"completion.json").read_bytes())["failed"] == 1
    output = evaluate_run(root, directory)
    metrics = json.loads((output/"metrics.json").read_bytes())
    assert metrics["failed_documents"] == 1
    assert metrics["success_rate"] == 2/3
    run_fake(root, manifest)
    assert calls(root).count("fixture-0") == calls(root).count("fixture-2") == 1
    assert calls(root).count("fixture-1") == 2


def test_initialization_failure_cleanup_and_resume(tmp_path):
    root, manifest, _ = fixture_root(tmp_path)
    bad = Fake(root, init_fail=True)
    with pytest.raises(RuntimeError, match="initialization"):
        run(root, manifest, spec(), config(), lambda: bad, probe=observed)
    assert bad.cleaned == 1 and not calls(root)
    directory = next((root/"results/fixture").iterdir())
    end = json.loads(next((directory/"sessions").glob("*-end.json")).read_bytes())
    assert end["state"] == "FAILED_INITIALIZATION"
    assert end["initialization_seconds"] >= 0
    run_fake(root, manifest, resume=directory)
    assert len(calls(root)) == 3


@pytest.mark.parametrize("change", ["model", "adapter", "precision", "resize", "dpi"])
def test_meaningful_identity_changes_invalidate_cache(tmp_path, change):
    root, manifest, _ = fixture_root(tmp_path, 1)
    run_fake(root, manifest)
    selected, settings = spec(), config()
    if change == "model": selected.model_revision = "changed"
    if change == "adapter": selected.adapter_revision = "changed"
    if change == "precision": settings.precision = "different"
    if change == "resize": settings.preprocessing = {"resize": [50, 50]}
    if change == "dpi": settings.dpi = 200
    run_fake(root, manifest, selected, settings)
    assert len(calls(root)) == 2


def test_tampered_cache_is_preserved_and_not_silently_rerun(tmp_path):
    root, manifest, _ = fixture_root(tmp_path, 1)
    run_fake(root, manifest)
    entry = next((root/"cache/predictions").glob("*/raw.bin"))
    entry.write_bytes(b"tampered")
    with pytest.raises(IntegrityError):
        run_fake(root, manifest)
    assert entry.read_bytes() == b"tampered" and len(calls(root)) == 1


@pytest.mark.parametrize("target", ["source", "reference", "manifest"])
def test_frozen_input_tampering_blocks_before_construction(tmp_path, target):
    root, manifest, _ = fixture_root(tmp_path, 1)
    path = {"source": root/"image-0.fixture", "reference": root/"reference-0.json", "manifest": manifest}[target]
    path.write_bytes(b"tampered")
    with pytest.raises(IntegrityError):
        run(root, manifest, spec(), config(), lambda: pytest.fail("Must not construct"), probe=observed)


def test_unsafe_ram_blocks_before_factory_and_unknown_gpu_build(tmp_path):
    root, manifest, _ = fixture_root(tmp_path, 1)
    selected = spec(); selected.requirements.ram_bytes = 9*1024**3
    with pytest.raises(preflight.PreflightBlocked, match="RAM"):
        run(root, manifest, selected, config(), lambda: pytest.fail("Must not construct"), probe=observed)
    gpu = spec(); gpu.gpu_backend = "torch"; gpu.requirements.vram_bytes = 1
    hardware = dict(observed(root), gpus=[{"vram_free_mib": 20, "compute_capability": "7.0"}])
    with pytest.raises(preflight.PreflightBlocked, match="CUDA build"):
        preflight.check(gpu, config().model_copy(update={"device": "cuda:0"}), hardware, root)


def test_each_real_model_requires_its_own_approval(tmp_path):
    root, manifest, _ = fixture_root(tmp_path, 1)
    shutil.copyfile(SUITE/"BENCHMARK_STATUS.json", root/"BENCHMARK_STATUS.json")
    for model in ("surya", "paddle_vl", "marker", "paddle", "tesseract", "docling_easyocr", "docling_tesseract", "granite_docling", "baidu"):
        selected = spec().model_copy(update={"model_id": model})
        with pytest.raises(preflight.PreflightBlocked):
            run(root, manifest, selected, config().model_copy(update={"purpose": "benchmark"}), lambda: pytest.fail("No model approved"))
        with pytest.raises(preflight.PreflightBlocked, match="restricted"):
            run(root, manifest, selected, config(), lambda: pytest.fail("No fixture bypass"))


def test_coordinator_excludes_other_runners_and_preserves_lock_inode(tmp_path):
    path = tmp_path/"coordinator.lock"
    with coordinator_lock(path):
        with pytest.raises(RuntimeError, match="already active"):
            with coordinator_lock(path):
                pass
    with coordinator_lock(path):
        assert path.exists()


def test_completed_runs_immutable_offline_evaluation_repeats_without_cache(tmp_path):
    root, manifest, _ = fixture_root(tmp_path)
    directory = run_fake(root, manifest)
    hashes = {p.relative_to(directory): digest(p) for p in directory.rglob("*") if p.is_file()}
    # Evaluation consumes run bundles, never requires prediction cache or adapter.
    saved_cache = root/"cache/predictions-saved"
    (root/"cache/predictions").rename(saved_cache)
    one, two = evaluate_run(root, directory), evaluate_run(root, directory)
    assert one != two
    assert (one/"metrics.json").read_bytes() == (two/"metrics.json").read_bytes()
    assert hashes == {p.relative_to(directory): digest(p) for p in directory.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="incomplete"):
        run_fake(root, manifest, resume=directory)
    report = json.loads((one/"metrics.json").read_bytes())
    assert all(s["content_normalized_cer"]["micro"] == 0 for s in report["strata"])
    assert all(s["layout"]["map"]["map"] == 1 for s in report["strata"] if s["language"] == "en")


def test_wrong_output_identity_is_failure_and_preserves_raw(tmp_path):
    root, manifest, _ = fixture_root(tmp_path, 1)
    directory = run(root, manifest, spec(), config(), lambda: Fake(root, bad_identity=True), probe=observed)
    assert json.loads((directory/"completion.json").read_bytes())["failed"] == 1
    assert len(list((directory/"documents").glob("*/raw.bin"))) == 1
    assert not (root/"cache/predictions").exists()


def test_offline_artifact_tampering_rejected(tmp_path):
    root, manifest, _ = fixture_root(tmp_path, 1)
    directory = run_fake(root, manifest)
    next((directory/"documents").glob("*/prediction.json")).write_bytes(b"{}")
    with pytest.raises(IntegrityError):
        evaluate_run(root, directory)


def test_resume_refuses_changed_identity(tmp_path):
    root, manifest, _ = fixture_root(tmp_path, 1)
    bad = Fake(root, init_fail=True)
    with pytest.raises(RuntimeError):
        run(root, manifest, spec(), config(), lambda: bad, probe=observed)
    directory = next((root/"results/fixture").iterdir())
    with pytest.raises(IntegrityError, match="Cannot resume"):
        run_fake(root, manifest, settings=config().model_copy(update={"precision": "changed"}), resume=directory)


def test_coordinate_transform_and_geometry_gate(tmp_path):
    root, _, records = fixture_root(tmp_path, 1)
    doc = records[0]
    page = OCRPage(page_number=1)
    bounds = BoundingBox(x_min=0, y_min=.8, x_max=1, y_max=1, units="normalized", origin="bottom_left")
    assert pixels(bounds, page, doc) == pytest.approx((0, 0, 100, 20))
    prediction = Prediction(result=OCRResult(document_id=doc["document_id"], filename="fixture", provider="fixture", text="hello"),
                            text_format="plain", coordinate_notes="none supplied")
    policy = json.loads((root/"configs/evaluation.json").read_bytes())
    scored = evaluate_record(doc, (root/doc["ground_truth_reference"]).read_text(), prediction, spec(), policy)
    assert scored["text"]["status"] == "NOT_EVALUATED"
    assert "GEOMETRY" in scored["text"]["reason"]


def test_existing_provider_bridge_is_lazy_and_raw_boundary_explicit(tmp_path):
    selected = spec().model_copy(update={"raw_level": "production-provider-OCRResult"})
    class Provider:
        ready = False
        unloaded = False
        def initialize(self): self.ready = True
        def unload(self): self.unloaded = True
        def extract(self, document):
            return OCRResult(document_id=document.document_id, filename=document.filename, provider="fixture", text="original")
    provider = Provider()
    bridge = ExistingProviderAdapter(lambda config: provider, selected)
    assert not provider.ready
    bridge.initialize(config())
    from OCR.providers.base import OCRDocument
    document = OCRDocument(document_id="x", filename="x", path=tmp_path/"x")
    raw = bridge.predict(document)
    assert bridge.normalize_output(raw, document).result.text == "original"
    assert json.loads(raw.data)["text"] == "original"
    bridge.cleanup()
    assert provider.unloaded


def test_source_changed_during_inference_is_not_cached(tmp_path):
    root, manifest, _ = fixture_root(tmp_path, 1)
    class MutatingFake(Fake):
        def predict(self, document):
            output = super().predict(document)
            document.path.write_bytes(b"changed during fixture inference")
            return output
    directory = run(root, manifest, spec(), config(), lambda: MutatingFake(root), probe=observed)
    assert json.loads((directory/"completion.json").read_bytes())["failed"] == 1
    assert not (root/"cache/predictions").exists()


def test_unknown_labels_withhold_layout_and_order_not_text(tmp_path):
    root, _, records = fixture_root(tmp_path, 1)
    record = records[0]
    from OCR.providers.base import OCRDocument
    document = OCRDocument(document_id=record["document_id"], filename="x", path=root/"x")
    prediction = Fake(root).normalize_output(RawOutput(json_bytes({"text": "hello"}), "application/json"), document)
    policy = json.loads((root/"configs/evaluation.json").read_bytes())
    selected = spec(); selected.label_map = {}
    scores = evaluate_record(record, (root/record["ground_truth_reference"]).read_text(), prediction, selected, policy)
    assert scores["text"]["items"][0]["content"]["normalized"]["cer"] == 0
    assert scores["layout"]["reason"] == "MODEL_LABEL_MAPPING_UNAVAILABLE"
    assert scores["reading_order"]["status"] == "NOT_EVALUATED"
    prediction.result.pages[0].blocks[0].confidence = None
    scores = evaluate_record(record, (root/record["ground_truth_reference"]).read_text(), prediction, spec(), policy)
    assert scores["layout"]["detection"]["map"] is None
    assert scores["layout"]["detection"]["micro"]["f1"] == 1


def test_arabic_multiple_table_alignment_is_not_guessed(tmp_path):
    root, _, records = fixture_root(tmp_path)
    record = records[2]; record["evaluation_capabilities"].append("tables")
    selected = spec(); selected.capabilities.tables = True
    markup = '<table><tr><td>independent truth</td></tr></table>'
    prediction = Prediction(result=OCRResult(document_id=record["document_id"], filename="x", provider="fixture", text="x"),
                            text_format="plain", coordinate_notes="no table coordinates",
                            tables=[Table(table_id=str(i), page_number=1, html=markup) for i in range(2)])
    policy = json.loads((root/"configs/evaluation.json").read_bytes())
    scores = evaluate_record(record, markup+markup, prediction, selected, policy)
    assert "ALIGNMENT_UNAVAILABLE" in scores["tables"]["reason"]
    single = evaluate_record(record, markup, prediction.model_copy(update={"tables": prediction.tables[:1]}), selected, policy)
    assert single["tables"]["items"][0]["teds"] == 1
    assert single["chart_numeric"]["value"] is None
    policy["tables"]["max_nodes"] = 1
    limited = evaluate_record(record, markup, prediction.model_copy(update={"tables": prediction.tables[:1]}), selected, policy)
    assert limited["tables"]["status"] == "NOT_EVALUATED"
    assert limited["tables"]["scored_tables"] == 0


def test_gpu_samples_are_owned_process_only_and_wddm_is_null():
    assert gpu_bytes("1, 10\n2, 20\n3, 999", {1, 2}) == 30*1024**2
    assert gpu_bytes("1, [N/A]\n2, 20", {1, 2}) is None
    assert gpu_bytes("3, 999", {1, 2}) is None


def test_asset_dependency_and_disk_preflight_are_fail_closed(tmp_path):
    selected = spec(); selected.assets = {"missing.weights": "0"*64}
    with pytest.raises(preflight.PreflightBlocked, match="checksum"):
        preflight.check(selected, config(), observed(tmp_path), tmp_path)
    selected = spec(); selected.packages = {"not-an-installed-fixture-package": "1"}
    with pytest.raises(preflight.PreflightBlocked, match="Dependency"):
        preflight.check(selected, config(), observed(tmp_path), tmp_path)
    selected = spec(); selected.requirements.disk_bytes = 21*1024**3
    with pytest.raises(preflight.PreflightBlocked, match="disk"):
        preflight.check(selected, config(), observed(tmp_path), tmp_path)
    selected = spec(); selected.requirements.compatibility = "UNKNOWN"
    with pytest.raises(preflight.PreflightBlocked, match="unknown"):
        preflight.check(selected, config(), observed(tmp_path), tmp_path)


def test_changed_adapter_metadata_is_rejected_and_cleaned_up(tmp_path):
    root, manifest, _ = fixture_root(tmp_path, 1)
    changed = spec(); changed.adapter_revision = "unexpected"
    fake = Fake(root, changed)
    with pytest.raises(IntegrityError, match="metadata"):
        run(root, manifest, spec(), config(), lambda: fake, probe=observed)
    assert fake.initialized == 0 and fake.cleaned == 1


def test_word_blocks_allocate_without_using_recognized_text(tmp_path):
    root, _, records = fixture_root(tmp_path, 1)
    record = records[0]
    source = json.loads((root/record["ground_truth_reference"]).read_text())
    source["layout_dets"][0]["text"] = "hello world"
    blocks = [OCRBlock(block_type="text", text=value, reading_order=index, confidence=.9,
              bounding_box=BoundingBox(x_min=index*50, y_min=0, x_max=(index+1)*50, y_max=20, units="pixels", origin="top_left"))
              for index, value in enumerate(("hello", "world"))]
    prediction = Prediction(result=OCRResult(document_id=record["document_id"], filename="x", provider="fixture",
        pages=[OCRPage(page_number=1, width=100, height=100, dimension_units="pixels", blocks=blocks)]),
        text_format="plain", coordinate_notes="original pixels")
    policy = json.loads((root/"configs/evaluation.json").read_bytes())
    scores = evaluate_record(record, json.dumps(source), prediction, spec(), policy)
    assert scores["text"]["items"][0]["matched_blocks"] == 2
    assert scores["text"]["items"][0]["content"]["normalized"]["cer"] == 0
    blocks[0].text = "WRONG"
    scores = evaluate_record(record, json.dumps(source), prediction, spec(), policy)
    assert scores["text"]["items"][0]["matched_blocks"] == 2
    assert scores["text"]["items"][0]["content"]["normalized"]["cer"] > 0


def test_plain_block_fallback_is_not_interpreted_as_markdown(tmp_path):
    root, _, records = fixture_root(tmp_path, 1)
    record = records[0]
    source = json.loads((root/record["ground_truth_reference"]).read_text())
    source["layout_dets"][0]["text"] = r"\*literal\*"
    from OCR.providers.base import OCRDocument
    document = OCRDocument(document_id=record["document_id"], filename="x", path=root/"x")
    prediction = Fake(root).normalize_output(RawOutput(json_bytes({"text": "*literal*"}), "application/json"), document)
    prediction.text_format = "markdown"
    policy = json.loads((root/"configs/evaluation.json").read_bytes())
    scores = evaluate_record(record, json.dumps(source), prediction, spec(), policy)
    assert scores["text"]["items"][0]["content"]["normalized"]["cer"] == 0


def test_excluded_layout_mask_does_not_create_background_false_positive(tmp_path):
    root, _, records = fixture_root(tmp_path, 1)
    record = records[0]
    source = json.loads((root/record["ground_truth_reference"]).read_text())
    source["layout_dets"].append({"anno_id": "mask", "category_type": "text_mask", "poly": [0, 30, 100, 30, 100, 60, 0, 60]})
    from OCR.providers.base import OCRDocument
    document = OCRDocument(document_id=record["document_id"], filename="x", path=root/"x")
    prediction = Fake(root).normalize_output(RawOutput(json_bytes({"text": "hello"}), "application/json"), document)
    extra = prediction.result.pages[0].blocks[0].model_copy(deep=True)
    extra.block_id = "masked"; extra.bounding_box.y_min = 30; extra.bounding_box.y_max = 60
    prediction.result.pages[0].blocks.append(extra)
    policy = json.loads((root/"configs/evaluation.json").read_bytes())
    scores = evaluate_record(record, json.dumps(source), prediction, spec(), policy)
    assert scores["layout"]["detection"]["micro"]["fp"] == 0
    assert scores["layout"]["excluded_prediction_blocks"] == 1
    assert scores["text"]["unassigned_prediction_blocks"] == 1


def test_absent_page_class_is_still_an_annotated_negative(tmp_path):
    root, _, records = fixture_root(tmp_path, 1)
    record = records[0]
    from OCR.providers.base import OCRDocument
    document = OCRDocument(document_id=record["document_id"], filename="x", path=root/"x")
    prediction = Fake(root).normalize_output(RawOutput(json_bytes({"text": "hello"}), "application/json"), document)
    selected = spec(); selected.label_map = {"text": "figure"}
    policy = json.loads((root/"configs/evaluation.json").read_bytes())
    scores = evaluate_record(record, (root/record["ground_truth_reference"]).read_text(), prediction, selected, policy)
    assert scores["layout"]["detection"]["micro"]["fp"] == 1
    assert scores["layout"]["detection"]["micro"]["fn"] == 1
