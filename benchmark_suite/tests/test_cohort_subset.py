import pytest

from benchmark_suite.dataset_io import digest
from benchmark_suite.runners.run import load_records
from benchmark_suite.tests.test_runner import config, fixture_root


def test_round_robin_subset_preserves_frozen_manifest_and_unique_ids(tmp_path):
    root, manifest, original = fixture_root(tmp_path, count=6)
    before = digest(manifest)
    settings = config()
    settings.max_documents = 4
    settings.sampling = "language-round-robin"
    records, cohort = load_records(root, manifest, settings)
    assert [r["language"] for r in records] == ["ar", "en", "en", "en"]
    assert len({r["document_id"] for r in records}) == 4
    assert {r["document_id"] for r in records} <= {r["document_id"] for r in original}
    assert digest(manifest) == before
    assert cohort["selection"]["available_documents"] == 6
    assert cohort["selected_document_ids"] == [r["document_id"] for r in records]
    assert load_records(root, manifest, settings) == (records, cohort)


def test_oversized_subset_and_unbounded_resampling_are_rejected(tmp_path):
    root, manifest, _ = fixture_root(tmp_path)
    settings = config()
    settings.max_documents = 4
    with pytest.raises(ValueError, match="exceeds"):
        load_records(root, manifest, settings)
    settings.max_documents = None
    settings.sampling = "language-round-robin"
    with pytest.raises(ValueError, match="explicit page limit"):
        load_records(root, manifest, settings)
