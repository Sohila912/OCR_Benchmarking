"""SQLite metrics-only history. Source documents and extracted content are never stored here."""
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

class BenchmarkStore:
    def __init__(self, path: Path, retention_days=90):
        self.path = path
        self.retention_days = retention_days
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, dataset TEXT NOT NULL, provider TEXT NOT NULL, payload TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS run_filters ON runs(dataset, provider, timestamp)")

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute("PRAGMA secure_delete=ON")
        return connection

    def prune(self):
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).isoformat()
        with self.connect() as db:
            db.execute("DELETE FROM runs WHERE timestamp < ?", (cutoff,))

    def save(self, row):
        if not all(row.get(k) for k in ("id", "timestamp", "dataset_id", "provider", "document_id", "reference_hash")):
            raise ValueError("Incomplete benchmark metadata.")
        if row.get("status") not in ("success", "failed", "running"):
            raise ValueError("Invalid benchmark status.")
        if row["status"] == "success":
            from OCR.evaluation import Normalization, METHOD
            Normalization.model_validate(row.get("normalization"))
            metrics = row.get("metrics")
            if not isinstance(metrics, dict) or row.get("method") != METHOD:
                raise ValueError("Invalid evaluation method or metrics.")
            for unit, rate in (("characters", "cer"), ("words", "wer")):
                counts = metrics.get(unit, {})
                if not all(isinstance(counts.get(k), int) and counts[k] >= 0 for k in ("edits", "substitutions", "deletions", "insertions", "reference_length")):
                    raise ValueError("Invalid edit counts.")
                if counts["reference_length"] <= 0 or counts["edits"] != sum(counts[k] for k in ("substitutions", "deletions", "insertions")):
                    raise ValueError("Invalid reference length or edit total.")
                if metrics.get(rate) != counts["edits"] / counts["reference_length"]:
                    raise ValueError("Inconsistent error rate.")
        # Explicit whitelist prevents accidental persistence of customer text.
        allowed = {k: row.get(k) for k in ("id", "batch_id", "timestamp", "dataset_id", "dataset_name", "document_id",
            "reference_hash", "provider", "model_name", "model_version", "model_digest", "package_version", "metrics", "normalization",
            "method", "runtime_versions", "duration_seconds", "initialization_seconds", "inference_seconds", "status", "error", "origin")}
        payload = json.dumps(allowed, ensure_ascii=False, allow_nan=False)
        with self.connect() as db:
            changed = db.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload WHERE json_extract(runs.payload, '$.status')='running'",
                       (row["id"], row["timestamp"], row["dataset_id"], row["provider"], payload)).rowcount
            if not changed:
                raise ValueError("Completed benchmark records cannot be overwritten.")
        self.prune()

    def recover_interrupted(self):
        with self.connect() as db:
            for run_id, payload in db.execute("SELECT id, payload FROM runs WHERE json_extract(payload, '$.status')='running'").fetchall():
                row = json.loads(payload)
                row.update(status="failed", error="interrupted: API stopped before benchmark completion; no accuracy score is available.")
                db.execute("UPDATE runs SET payload=? WHERE id=?", (json.dumps(row, ensure_ascii=False), run_id))

    def history(self, provider=None, dataset=None, since=None, until=None):
        self.prune()
        clauses, values = [], []
        for column, value, op in (("provider", provider, "="), ("dataset", dataset, "="),
                                  ("timestamp", since, ">="), ("timestamp", until, "<=")):
            if value:
                clauses.append(column + op + "?")
                values.append(value)
        query = "SELECT payload FROM runs" + (" WHERE " + " AND ".join(clauses) if clauses else "")
        with self.connect() as db:
            return [json.loads(r[0]) for r in db.execute(query + " ORDER BY timestamp DESC LIMIT 2000", values)]

    def delete(self, run_id):
        with self.connect() as db:
            return db.execute("DELETE FROM runs WHERE id=?", (run_id,)).rowcount

def compare_runs(rows):
    from OCR.evaluation import aggregate
    groups = {}
    for row in rows:
        key = (row["provider"], row.get("model_version"), row["dataset_id"],
               json.dumps(row["normalization"], sort_keys=True), row["method"], row.get("model_name"), row.get("package_version"), row.get("model_digest"))
        groups.setdefault(key, []).append(row)
    summaries = []
    for key, group in groups.items():
        # One measurement per document/reference per group; newest selected run wins.
        unique = {}
        for row in sorted(group, key=lambda r: r["timestamp"]):
            unique[(row["document_id"], row["reference_hash"])] = row
        summaries.append({"provider": key[0], "model_version": key[1], "dataset_id": key[2],
                          "model_name": key[5], "package_version": key[6], "model_digest": key[7], "selected_runs": len(group), **aggregate(list(unique.values()))})
    signatures = [{(r["document_id"], r["reference_hash"]) for r in group} for group in groups.values()]
    policies = {(json.dumps(r["normalization"], sort_keys=True), r["method"]) for r in rows}
    return {"same_document_and_reference": bool(signatures) and all(s == signatures[0] for s in signatures), "same_evaluation_policy": len(policies) == 1,
            "summaries": summaries,
            "aggregation": "Micro rates = total edits / total reference units; newest selected run per document/reference/provider/model/dataset/policy. Failed outputs are excluded; inspect coverage. Different datasets or policies are not equivalent."}
