"""Read-only metric-readiness audit; prints metadata only, never model scores."""

from collections import Counter
import json
from pathlib import Path
import re
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from benchmark_suite.metrics import references, tables


def audit(root):
    config = json.loads((root / "configs/evaluation.json").read_text(encoding="utf-8"))
    counts = Counter()
    exclusions = []
    for split in ("development", "evaluation"):
        for line in (root / f"datasets/manifest/{split}.jsonl").read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            language = record["language"]
            payload = (root / record["ground_truth_reference"]).read_text(encoding="utf-8")
            counts[f"{split}:{language}:pages"] += 1
            if language == "en":
                page = json.loads(payload)
                scope = references.english_regions(page)
                counts[f"{split}:en:explicit_text_regions"] += len(scope["regions"])
                if "layout" in record["evaluation_capabilities"]:
                    references.layout_reference(page, config["layout"]["omnidocbench_labels"])
                    counts[f"{split}:en:layout_validated"] += 1
                if "reading_order" in record["evaluation_capabilities"]:
                    references.ordered_reference(page)
                    counts[f"{split}:en:order_validated"] += 1
                html = [r["html"] for r in page["layout_dets"] if not r.get("ignore", False) and r.get("html")]
            else:
                references.markdown_content(payload)
                html = re.findall(r"<table\b[^>]*>.*?</table\s*>", payload, flags=re.I | re.S)
            for index, markup in enumerate(html):
                counts[f"{split}:{language}:table_fragments"] += 1
                if "tables" not in record["evaluation_capabilities"]:
                    reason = "MANIFEST_TABLE_GATE"
                else:
                    try:
                        node = tables.parse_table(markup)
                        tables.grid(node)
                        reason = "TREE_EDIT_NODE_LIMIT" if tables._size(node) > config["tables"]["max_nodes"] else "READY"
                    except (ValueError, RecursionError):
                        reason = "INVALID_REFERENCE_TABLE"
                counts[f"{split}:{language}:table_{reason}"] += 1
                if reason != "READY":
                    exclusions.append({"document_id": record["document_id"], "table_index": index, "reason": reason})
    return {"kind": "reference_readiness_not_model_results", "counts": dict(sorted(counts.items())),
            "table_exclusions": exclusions, "tree_state_limit": "Evaluated at scoring time; readiness is not a guarantee"}


if __name__ == "__main__":
    print(json.dumps(audit(Path(__file__).resolve().parents[1]), indent=2, ensure_ascii=True))
