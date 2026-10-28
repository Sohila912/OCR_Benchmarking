"""Acquire the two approved primary sources and freeze auditable page manifests.

Source references are preserved, not synthesized by OCR. No model imports.
"""

from __future__ import annotations

from collections import Counter
import hashlib
from io import BytesIO
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
from typing import Any
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field

from benchmark_suite.dataset_io import Downloader, atomic_json, digest, safe_path, object_path, replace_file

PINS = {
    "omnidocbench": ("opendatalab/OmniDocBench", "aa1ee96d106dbe53d0ae59474d75c6e6d9b53fec"),
    "misraj": ("Misraj/Misraj-DocOCR", "7177bf70f77ce259890d6af0bef53f18faf26ec9"),
}
SEED = "ocr-benchmark-primary-v1-2026-10-28"


class ManifestRecord(BaseModel):
    """One real source page and an independent preserved reference."""

    model_config = ConfigDict(extra="forbid", strict=True)
    document_id: str = Field(min_length=1)
    dataset_name: str = Field(min_length=1)
    dataset_version: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_path: str = Field(min_length=1)
    file_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    language: str = Field(pattern=r"^(en|ar)$")
    document_category: str | None
    page_count: int = Field(ge=1, le=1)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    ground_truth_reference: str = Field(min_length=1)
    reference_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    upstream_split: str
    source_document_id: str | None
    source_grouping_status: str
    annotation_types: list[str] = Field(min_length=1)
    evaluation_capabilities: list[str] = Field(min_length=1)
    reference_warnings: list[str]
    split: str = Field(pattern=r"^(development|evaluation)$")
    split_group_id: str
    source_metadata: dict[str, Any]


class TableAudit(HTMLParser):
    """Check explicit table/row/cell nesting; not a structural scoring metric."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.tables = self.rows = self.cells = self.merged = 0
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in {"table", "tr", "td", "th"}:
            return
        parent = self.stack[-1] if self.stack else None
        if (tag == "table" and parent is not None) or (tag == "tr" and parent != "table") or (
            tag in {"td", "th"} and parent != "tr"):
            self.errors.append("INVALID_TABLE_NESTING")
        self.stack.append(tag)
        if tag == "table":
            self.tables += 1
        elif tag == "tr":
            self.rows += 1
        else:
            self.cells += 1
            for key, value in attrs:
                if key in {"rowspan", "colspan"}:
                    if value is None or not value.isdecimal() or not 1 <= int(value) <= 1000:
                        self.errors.append("INVALID_CELL_SPAN")
                    elif int(value) > 1:
                        self.merged += 1

    def handle_endtag(self, tag: str) -> None:
        if tag not in {"table", "tr", "td", "th"}:
            return
        if not self.stack or self.stack.pop() != tag:
            self.errors.append("UNBALANCED_TABLE_TAGS")


def audit_tables(text: str) -> dict[str, Any]:
    parser = TableAudit()
    parser.feed(text)
    parser.close()
    if parser.stack:
        parser.errors.append("UNCLOSED_TABLE_TAGS")
    if parser.tables and (not parser.rows or not parser.cells):
        parser.errors.append("EMPTY_TABLE_STRUCTURE")
    return {"tables": parser.tables, "rows": parser.rows, "cells": parser.cells,
            "merged_span_attributes": parser.merged, "errors": sorted(set(parser.errors))}


def resource_check(minimum_ram: int = 512 * 1024 ** 2) -> None:
    import psutil
    if psutil.virtual_memory().available < minimum_ram:
        raise RuntimeError("Insufficient free RAM for bounded reference decoding; preserve downloads and retry after freeing RAM.")


def catalog(suite: Path, downloader: Downloader) -> dict[str, Any]:
    path = suite / "datasets/raw/catalog.json"
    if path.exists():
        result = json.loads(path.read_text(encoding="utf-8"))
    else:
        result = {}
        for key, (repo, revision) in PINS.items():
            url = f"https://huggingface.co/api/datasets/{repo}/revision/{revision}?blobs=true"
            # Metadata is small; include a conservative reservation in the same
            # cumulative byte budget before reading even this API response.
            allowance = 2_000_000
            if downloader.state["charged_bytes"] + allowance > downloader.state["budget_bytes"]:
                raise RuntimeError("No transfer budget remaining for source metadata.")
            downloader.state["charged_bytes"] += allowance
            atomic_json(downloader.path, downloader.state)
            with urlopen(Request(url, headers={"User-Agent": "OCR-Benchmark-Acquisition/1.0"}), timeout=30) as response:
                raw = response.read(allowance)
            downloader.state["charged_bytes"] -= allowance - len(raw)
            atomic_json(downloader.path, downloader.state)
            data = json.loads(raw)
            result[key] = {"id": data["id"], "sha": data["sha"], "files": data["siblings"],
                           "metadata_sha256": hashlib.sha256(raw).hexdigest()}
        atomic_json(path, result)
    for key, (repo, revision) in PINS.items():
        if result[key]["id"] != repo or result[key]["sha"] != revision:
            raise ValueError("Catalog does not match approved source pins.")
    return result


def source_path(suite: Path, key: str, filename: str) -> Path:
    repo, revision = PINS[key]
    root = suite / "datasets/raw"
    legacy = safe_path(root, f"{repo}/{revision}/{filename}")
    canonical = object_path(root, repo, revision, filename)
    return canonical if canonical.is_file() else legacy


def canonicalize_storage(suite: Path) -> None:
    """Normalize this task's early download paths without deleting originals.

    This makes frozen paths match a fresh acquisition, even though early files
    preceded the Windows long-path fix. Never call while a downloader is active.
    """
    downloader = Downloader(suite / "datasets/raw")
    for key, entry in downloader.state["files"].items():
        source = safe_path(downloader.root, entry.get("storage_path", key))
        destination = object_path(downloader.root, entry["dataset"], entry["revision"], entry["filename"])
        if source == destination:
            continue
        if digest(source) != entry["sha256"]:
            raise ValueError("Cannot normalize changed source bytes.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            temporary = destination.with_name(destination.name + ".tmp")
            shutil.copyfile(source, temporary)
            if digest(temporary) != entry["sha256"]:
                raise ValueError("Local canonical copy checksum mismatch.")
            replace_file(temporary, destination)
        elif digest(destination) != entry["sha256"]:
            raise ValueError("Existing canonical bytes differ; preserve all evidence.")
        entry["storage_path"] = destination.relative_to(downloader.root).as_posix()
        entry["legacy_copy_preserved"] = source.relative_to(downloader.root).as_posix()
    atomic_json(downloader.path, downloader.state)


def english_pages(suite: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    resource_check()
    pages = json.loads(source_path(suite, "omnidocbench", "OmniDocBench.json").read_text(encoding="utf-8"))
    if not isinstance(pages, list) or len(pages) != 1651:
        raise ValueError("Pinned OmniDocBench page count/schema changed.")
    counts = Counter(p["page_info"]["page_attribute"]["language"] for p in pages)
    return [p for p in pages if p["page_info"]["page_attribute"]["language"] == "english"], dict(counts)


def acquire(suite: Path) -> dict[str, Any]:
    downloader = Downloader(suite / "datasets/raw")
    sources = catalog(suite, downloader)
    for key, entry in sources.items():
        for item in entry["files"]:
            if item["rfilename"] == "README.md" or (key == "omnidocbench" and item["rfilename"] == "OmniDocBench.json"):
                downloader.fetch(entry["id"], entry["sha"], item)
    # Keep the independent publisher's copyright/usage statement with the data.
    notices = source_path(suite, "omnidocbench", "README.md").read_text(encoding="utf-8")
    if "not for commercial use" not in notices.lower():
        raise ValueError("Pinned English use statement needs review before further acquisition.")
    pages, counts = english_pages(suite)
    english_files = {"images/" + p["page_info"]["image_path"] for p in pages}
    del pages
    requested = []
    for key, entry in sources.items():
        selected = [item for item in entry["files"] if
                    (key == "omnidocbench" and item["rfilename"] in english_files) or
                    (key == "misraj" and item["rfilename"].startswith("data/") and item["rfilename"].endswith(".parquet"))]
        if len(selected) != (len(english_files) if key == "omnidocbench" else 2):
            raise ValueError("Source file allowlist incomplete.")
        for item in sorted(selected, key=lambda x: x["rfilename"]):
            requested.append({"dataset": key, "filename": item["rfilename"], "bytes": item["size"]})
        print(f"Approved selection: {key}: {len(selected)} files, {sum(v['size'] for v in selected):,} bytes", flush=True)
    atomic_json(suite / "datasets/raw/allowlist.json", {"language_counts": counts, "files": requested})
    for row in requested:
        entry = sources[row["dataset"]]
        item = next(v for v in entry["files"] if v["rfilename"] == row["filename"])
        downloader.fetch(entry["id"], entry["sha"], item)
    return downloader.state


def preserve(path: Path, content: bytes) -> None:
    """Idempotent recovery is allowed; overwriting changed originals is not."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"Existing artifact differs; preserved: {path.name}")
        return
    temporary = path.with_name(path.name + ".tmp")
    # This deterministic staging file belongs to the single coordinator and
    # may be replaced after interruption; the published artifact never changes.
    with temporary.open("wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    replace_file(temporary, path)


def image_info(content: bytes) -> tuple[int, int, str]:
    from PIL import Image
    with Image.open(BytesIO(content)) as image:
        width, height = image.size
        extension = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}.get(image.format)
        if extension is None:
            raise ValueError("Unsupported source image format.")
        image.verify()
    return width, height, extension


def geometry_issues(page: dict[str, Any]) -> list[str]:
    """Check supplied polygons/IDs/order, without inventing a canonical taxonomy."""
    info = page["page_info"]
    issues, ids, orders = [], [], []
    for block in page["layout_dets"]:
        if block.get("ignore"):
            continue
        if not isinstance(block.get("category_type"), str):
            issues.append("MISSING_CATEGORY")
        polygon = block.get("poly")
        if not isinstance(polygon, list) or len(polygon) != 8:
            issues.append("INVALID_POLYGON")
        elif not all(isinstance(v, (int, float)) and 0 <= v <= (info["width"] if i % 2 == 0 else info["height"])
                     for i, v in enumerate(polygon)):
            issues.append("POLYGON_OUTSIDE_PAGE")
        if block.get("anno_id") is not None:
            ids.append(str(block["anno_id"]))
        if block.get("order") is not None:
            if type(block["order"]) is not int or block["order"] < 0:
                issues.append("INVALID_ORDER")
            else:
                orders.append(block["order"])
    if len(ids) != len(set(ids)):
        issues.append("DUPLICATE_REGION_ID")
    if len(orders) != len(set(orders)):
        issues.append("NONUNIQUE_READING_ORDER")
    return sorted(set(issues))


def base_record(suite: Path, key: str, identity: str, image: Path, reference: Path,
                width: int, height: int, category: str | None) -> dict[str, Any]:
    repo, revision = PINS[key]
    return {"document_id": f"{key}:{revision}:{identity}", "dataset_name": repo,
            "dataset_version": revision, "source_path": image.relative_to(suite).as_posix(),
            "file_hash": digest(image), "language": "en" if key == "omnidocbench" else "ar",
            "document_category": category, "page_count": 1, "width": width, "height": height,
            "ground_truth_reference": reference.relative_to(suite).as_posix(),
            "reference_hash": digest(reference), "upstream_split": "benchmark" if key == "omnidocbench" else "train",
            "source_document_id": None, "source_grouping_status": "UNKNOWN",
            "annotation_types": [], "evaluation_capabilities": [], "reference_warnings": [],
            "split": "PENDING", "source_metadata": {}}


def prepare_english(suite: Path) -> list[dict[str, Any]]:
    pages, _ = english_pages(suite)
    records = []
    for page in pages:
        info = page["page_info"]
        image = source_path(suite, "omnidocbench", "images/" + info["image_path"])
        identity = hashlib.sha256(info["image_path"].encode()).hexdigest()[:24]
        ref = safe_path(suite / "datasets/english/references", identity + ".json")
        preserve(ref, (json.dumps(page, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
        width, height, _ = image_info(image.read_bytes())
        if (width, height) != (info["width"], info["height"]):
            raise ValueError(f"English reference/image dimensions differ: {identity}")
        record = base_record(suite, "omnidocbench", identity, image, ref, width, height,
                             info["page_attribute"].get("data_source"))
        record["annotation_types"] = ["publisher_region_json"]
        blocks = [b for b in page["layout_dets"] if not b.get("ignore")]
        record["evaluation_capabilities"] = ["layout"]
        if any(isinstance(b.get("text"), str) and b["text"].strip() for b in blocks):
            record["evaluation_capabilities"].insert(0, "text")
        record["reference_warnings"] = geometry_issues(page)
        if any(v in record["reference_warnings"] for v in ["INVALID_POLYGON", "POLYGON_OUTSIDE_PAGE", "DUPLICATE_REGION_ID", "MISSING_CATEGORY"]):
            record["evaluation_capabilities"].remove("layout")
        if ("layout" in record["evaluation_capabilities"] and sum(b.get("order") is not None for b in blocks) >= 2
                and not any("ORDER" in v for v in record["reference_warnings"])):
            record["evaluation_capabilities"].append("reading_order")
        table_audits = [audit_tables(b["html"]) for b in blocks
                        if b.get("category_type") == "table" and b.get("html")]
        if table_audits:
            if all(t["tables"] and not t["errors"] for t in table_audits):
                record["evaluation_capabilities"].append("tables")
                record["annotation_types"].append("html_tables")
            else:
                record["reference_warnings"].append("TABLE_MARKUP_NEEDS_REVIEW")
        record["source_metadata"] = {"image_path": info["image_path"], "publisher_page_number": info["page_no"],
                                      "page_attributes": info["page_attribute"],
                                      "table_markup_audits": table_audits,
                                      "reference_assembly": "Preserved publisher region JSON; content scope defined in TASK-006"}
        records.append(record)
    return records


def prepare_arabic(suite: Path) -> list[dict[str, Any]]:
    resource_check()
    import pyarrow.parquet as parquet
    records, seen = [], set()
    for filename in ["data/train-00000-of-00002.parquet", "data/train-00001-of-00002.parquet"]:
        shard = source_path(suite, "misraj", filename)
        with parquet.ParquetFile(shard, memory_map=True, pre_buffer=False) as source:
            for batch in source.iter_batches(batch_size=1, columns=["uuid", "image", "markdown"], use_threads=False):
                row = batch.to_pylist()[0]
                identity, text, content = row["uuid"], row["markdown"], row["image"].get("bytes")
                if not isinstance(identity, str) or not re.fullmatch(r"[0-9a-f-]{36}", identity) or identity in seen:
                    raise ValueError("Missing or duplicate Arabic source UUID.")
                if not isinstance(text, str) or not text.strip() or "\x00" in text or not content:
                    raise ValueError(f"Missing Arabic image/reference: {identity}")
                seen.add(identity)
                width, height, extension = image_info(content)
                image = safe_path(suite / "datasets/arabic/images", identity + extension)
                ref = safe_path(suite / "datasets/arabic/references", identity + ".md")
                preserve(image, content)
                preserve(ref, text.encode("utf-8"))
                record = base_record(suite, "misraj", identity, image, ref, width, height, None)
                record["annotation_types"] = ["publisher_markdown"]
                record["evaluation_capabilities"] = ["text"]
                table_audit = audit_tables(text)
                if table_audit["tables"]:
                    if not table_audit["errors"]:
                        record["evaluation_capabilities"].append("tables")
                        record["annotation_types"].append("html_tables")
                    else:
                        record["reference_warnings"].append("TABLE_MARKUP_NEEDS_REVIEW")
                record["source_metadata"] = {"uuid": identity, "parquet_shard": shard.name,
                                              "category_status": "NOT_ANNOTATED",
                                              "source_parquet_filename": filename,
                                              "table_markup_audit": table_audit,
                                              "table_status": "Supplied HTML nesting/span checks only; TEDS belongs to TASK-006"}
                records.append(record)
    if len(records) != 400:
        raise ValueError("Pinned Arabic row count differs from 400.")
    return records


def split_records(records: list[dict[str, Any]], development_per_language: int = 10) -> dict[str, Any]:
    """Use content groups to avoid exact-image/reference leakage across splits.

    Source-document IDs are unknown: no claim of book/document independence.
    Conflicting references for identical images block publication rather than
    selecting whichever reference makes a model look better.
    """
    by_image: dict[str, list[dict[str, Any]]] = {}
    for row in records:
        by_image.setdefault(row["file_hash"], []).append(row)
    for group in by_image.values():
        if len({r["reference_hash"] for r in group}) > 1:
            raise ValueError("Identical source images have conflicting references; explicit quarantine review needed.")
    # Union exact image OR reference duplicates, including transitive groups.
    parent = list(range(len(records)))
    def find(n: int) -> int:
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n
    for field in ("file_hash", "reference_hash"):
        seen = {}
        for n, row in enumerate(records):
            value = row[field]
            if value in seen:
                parent[find(n)] = find(seen[value])
            seen[value] = n
    groups: dict[int, list[dict[str, Any]]] = {}
    for n, row in enumerate(records):
        groups.setdefault(find(n), []).append(row)
    ordered = sorted(groups.values(), key=lambda g: hashlib.sha256(
        (SEED + min(r["document_id"] for r in g)).encode()).hexdigest())
    counts = Counter()
    for group in ordered:
        language = group[0]["language"]
        selected = "development" if counts[language] < development_per_language else "evaluation"
        for row in group:
            row["split"] = selected
            row["split_group_id"] = min(r["document_id"] for r in group)
        if selected == "development":
            counts[language] += len(group)
    return {"seed": SEED, "development_counts": dict(counts), "exact_content_groups": len(groups),
            "source_document_grouping": "UNKNOWN; page/content disjoint only; no document-independent CI claim"}


def build(suite: Path) -> dict[str, Any]:
    """Publish the immutable cohort, with provenance as the final completion marker."""
    root = suite / "datasets/manifest"
    if (root / "PROVENANCE.json").exists():
        return validate(suite)
    canonicalize_storage(suite)
    records = prepare_english(suite) + prepare_arabic(suite)
    split_info = split_records(records)
    records = sorted((ManifestRecord.model_validate(row).model_dump() for row in records),
                     key=lambda row: row["document_id"])
    if len({r["document_id"] for r in records}) != len(records):
        raise ValueError("Duplicate manifest document IDs.")
    artifacts = {}
    for split in ("development", "evaluation"):
        content = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                          for row in records if row["split"] == split).encode("utf-8")
        if not content:
            raise ValueError("Cannot freeze an empty split.")
        path = root / (split + ".jsonl")
        preserve(path, content)
        artifacts[path.name] = digest(path)
    schema = (json.dumps(ManifestRecord.model_json_schema(), indent=2) + "\n").encode()
    preserve(root / "schema.json", schema)
    artifacts["schema.json"] = digest(root / "schema.json")
    aliases = {"included_in_official_cohort": False, "reason": "Legacy data source/rights/ground truth unverified",
               "explicit_pairings": [{"dataset": "Mix", "pdf": "benchmarks/datasets/Mix/Dataset/invoice_5.pdf",
                                      "reference": "benchmarks/datasets/Mix/Markdown_Reference/Invoice_5.md"}],
               "policy": "Exact-case paths are explicit. Never globally casefold IDs or rename originals."}
    preserve(root / "LEGACY_ALIASES.json", (json.dumps(aliases, indent=2) + "\n").encode())
    artifacts["LEGACY_ALIASES.json"] = digest(root / "LEGACY_ALIASES.json")
    journal = json.loads((suite / "datasets/raw/acquisition.json").read_text(encoding="utf-8"))
    import importlib.metadata as metadata
    evidence = {
        "schema_version": 1, "status": "COMPLETED", "pins": PINS, "split_policy": split_info,
        "created_from_downloads_through": max(v["downloaded_at"] for v in journal["files"].values()),
        "source_file_count": len(journal["files"]), "charged_transfer_bytes": journal["charged_bytes"],
        "verified_source_bytes": sum(v["bytes"] for v in journal["files"].values()),
        "approved_transfer_budget_bytes": journal["budget_bytes"], "manifest_sha256": artifacts,
        "records": len(records), "language_counts": dict(Counter(r["language"] for r in records)),
        "split_counts": dict(Counter(r["split"] + ":" + r["language"] for r in records)),
        "category_counts": dict(Counter(str(r["document_category"]) for r in records)),
        "capability_page_counts": dict(Counter(c for r in records for c in r["evaluation_capabilities"])),
        "reference_warning_counts": dict(Counter(w for r in records for w in r["reference_warnings"])),
        "source_archives_and_annotations": [v for v in journal["files"].values()
                                            if v["filename"].endswith((".parquet", ".json", ".md"))],
        "all_download_checksums": "datasets/raw/acquisition.json (ignored local complete inventory)",
        "environment": {n: metadata.version(n) for n in ["pyarrow", "Pillow", "pydantic", "psutil"]},
        "reference_policy": "Original source annotations/Markdown preserved; no generated OCR references; no model inference",
        "rights": {"omnidocbench": "noncommercial research only", "misraj": "dataset card Apache-2.0"},
        "limitations": ["Source-document identities unknown: splits are content/page-disjoint, not certified source-book-disjoint",
                        "Near-duplicate/perceptual similarity and public model-training contamination unverified",
                        "Arabic page categories, region geometry and localized reading order are not supplied",
                        "Chart numeric/type annotations absent from selected primary manifest",
                        "Table HTML checks do not certify every merged-cell topology or transcription by human review",
                        "Text content scope/normalization and metric calculations are TASK-006 work"],
    }
    preserve(root / "PROVENANCE.json", (json.dumps(evidence, ensure_ascii=False, indent=2) + "\n").encode())
    return validate(suite)


def verify_downloads(suite: Path) -> dict[str, Any]:
    """Verify originals using bounded byte hashing, without decoding references."""
    root = suite / "datasets/raw"
    journal = json.loads((root / "acquisition.json").read_text(encoding="utf-8"))
    allowlist = json.loads((root / "allowlist.json").read_text(encoding="utf-8"))
    wanted = {(PINS[row["dataset"]][0], row["filename"]) for row in allowlist["files"]}
    wanted |= {(repo, "README.md") for repo, _ in PINS.values()}
    wanted.add((PINS["omnidocbench"][0], "OmniDocBench.json"))
    found, total = set(), 0
    for key, item in journal["files"].items():
        identity = (item["dataset"], item["filename"])
        if identity not in wanted or (item["dataset"], item["revision"]) not in PINS.values():
            raise ValueError("Downloaded file outside the exact approved primary allowlist.")
        path = safe_path(root, item.get("storage_path", key))
        if path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise ValueError("Original downloaded bytes differ from verified acquisition evidence.")
        if item.get("advertised_sha256") and item["sha256"] != item["advertised_sha256"]:
            raise ValueError("Verified checksum contradicts source checksum.")
        found.add(identity)
        total += item["bytes"]
    if wanted != found or journal["charged_bytes"] > journal["budget_bytes"]:
        raise ValueError("Acquisition incomplete or exceeds approved transfer budget.")
    evidence = {"schema_version": 1, "status": "DOWNLOADS_VERIFIED",
                "frozen_manifest_status": "SEPARATE_PREPARATION_REQUIRED",
                "pins": PINS, "source_file_count": len(found), "verified_source_bytes": total,
                "charged_transfer_bytes": journal["charged_bytes"], "budget_bytes": journal["budget_bytes"],
                "download_started_at": min(i["downloaded_at"] for i in journal["files"].values()),
                "download_completed_at": max(i["downloaded_at"] for i in journal["files"].values()),
                "complete_local_inventory": "datasets/raw/acquisition.json",
                "complete_local_inventory_sha256": digest(root / "acquisition.json"),
                "allowlist_sha256": digest(root / "allowlist.json"),
                "source_language_counts": allowlist["language_counts"],
                "selected_english_images": sum(r["dataset"] == "omnidocbench" for r in allowlist["files"]),
                "selected_arabic_shards": sum(r["dataset"] == "misraj" for r in allowlist["files"]),
                "source_archives_and_annotations": [i for i in journal["files"].values()
                                                    if i["filename"].endswith((".parquet", ".json", ".md"))],
                "model_inference_executed": False}
    preserve(suite / "datasets/manifest/ACQUISITION_PROVENANCE.json",
             (json.dumps(evidence, ensure_ascii=False, indent=2) + "\n").encode())
    print(f"Verified {len(found)} downloaded originals ({total:,} bytes); no decoding, network or inference.")
    return evidence


def validate(suite: Path) -> dict[str, Any]:
    """Offline validation rehashes every selected source image and reference."""
    root = suite / "datasets/manifest"
    provenance = json.loads((root / "PROVENANCE.json").read_text(encoding="utf-8"))
    if provenance["status"] != "COMPLETED" or provenance["pins"] != {k: list(v) for k, v in PINS.items()}:
        raise ValueError("Missing complete provenance or mismatched source revisions.")
    for filename, expected in provenance["manifest_sha256"].items():
        if digest(safe_path(root, filename)) != expected:
            raise ValueError(f"Frozen manifest artifact changed: {filename}")
    for item in provenance.get("source_archives_and_annotations", []):
        relative = item.get("storage_path", f"{item['dataset']}/{item['revision']}/{item['filename']}")
        path = safe_path(suite / "datasets/raw", relative)
        if path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise ValueError("Downloaded source archive/annotation changed; originals must remain immutable.")
    seen_ids, content_splits, counts = set(), {}, Counter()
    for split in ("development", "evaluation"):
        with (root / (split + ".jsonl")).open(encoding="utf-8") as stream:
            for line in stream:
                record = ManifestRecord.model_validate(json.loads(line)).model_dump()
                if record["split"] != split or record["document_id"] in seen_ids:
                    raise ValueError("Wrong split or repeated document identity.")
                seen_ids.add(record["document_id"])
                repo, revision = PINS["omnidocbench" if record["language"] == "en" else "misraj"]
                if record["dataset_name"] != repo or record["dataset_version"] != revision:
                    raise ValueError("Record source identity differs from approved pins.")
                for field, hash_field in (("source_path", "file_hash"), ("ground_truth_reference", "reference_hash")):
                    if digest(safe_path(suite, record[field])) != record[hash_field]:
                        raise ValueError(f"Selected image/reference changed: {record['document_id']}")
                    content = (hash_field, record[hash_field])
                    if content in content_splits and content_splits[content] != split:
                        raise ValueError("Exact image/reference content leakage across splits.")
                    content_splits[content] = split
                counts[split + ":" + record["language"]] += 1
    if len(seen_ids) != provenance["records"] or dict(counts) != provenance["split_counts"]:
        raise ValueError("Frozen cohort counts do not match provenance.")
    print(f"Validated {len(seen_ids)} frozen source/reference pairs: {dict(counts)}. No network or inference.", flush=True)
    return provenance
