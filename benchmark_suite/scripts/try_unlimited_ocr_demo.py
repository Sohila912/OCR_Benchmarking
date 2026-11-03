"""Frozen development pages through Baidu's linked free demo; not a local benchmark."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
from uuid import uuid4

import requests

SUITE = Path(__file__).resolve().parents[1]
ROOT = Path("D:/OCR_Benchmarking_Assets/baidu_unlimited_ocr")
HOST = "https://baidu-unlimited-ocr-2.hf.space"


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def reusable_results(directory, records, seen=None):
    """Reuse only complete, identical-input results with the same request settings."""
    if directory is None:
        return {}
    directory = directory.resolve()
    seen = set() if seen is None else seen
    if directory in seen or len(seen) >= 20:
        raise ValueError("Cyclic or excessively deep reuse chain")
    seen.add(directory)
    if not directory.is_relative_to((ROOT / "demo_trials").resolve()):
        raise ValueError("Reuse requires an explicit trial under the D: demo root")
    prior = json.loads((directory / "trial.json").read_text(encoding="utf-8"))
    if prior["host"] != HOST or prior["model"] != "baidu/Unlimited-OCR-2" or prior["parameters"] != {
        "instruction": "", "mode": "auto", "max_page_tokens": 20000}:
        raise ValueError("Prior trial model, host or parameters differ")
    wanted = {r["document_id"]: r for r in records}
    results = reusable_results(Path(prior["reuse_source"]), records, seen) if prior.get("reuse_source") else {}
    for path in directory.glob("*/result.json"):
        state = json.loads(path.read_text(encoding="utf-8"))
        record = wanted.get(state["document_id"])
        if state["status"] != "SUCCESS" or record is None:
            continue
        saved = json.loads((path.parent / "input.json").read_text(encoding="utf-8"))
        response = json.loads((path.parent / "response.json").read_text(encoding="utf-8"))
        image = path.parent / (record["file_hash"] + Path(record["source_path"]).suffix)
        if (saved != record or state["source_sha256"] != record["file_hash"]
                or hashlib.sha256(image.read_bytes()).hexdigest() != record["file_hash"]
                or not response.get("done") or response.get("truncated") is not False):
            raise ValueError("Prior successful result failed input/completion verification")
        results[record["document_id"]] = dict(state, reused=True, source_directory=str(path.parent),
            source_response_sha256=hashlib.sha256((path.parent / "response.json").read_bytes()).hexdigest())
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development", action="store_true", help="Attempt all 20 frozen development pages")
    parser.add_argument("--reuse", type=Path, help="Explicit previous successful trial; preserve it unchanged")
    parser.add_argument("--authenticated", action="store_true", help="Use an existing local Hugging Face login for free demo quota; never log the token")
    args = parser.parse_args()
    sys.path.insert(0, str(SUITE.parent))
    from benchmark_suite.runners.preflight import authorize_model

    authorize_model("baidu", SUITE / "BENCHMARK_STATUS.json")
    out = ROOT / "demo_trials" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
    out.mkdir(parents=True, exist_ok=False)
    summary = {"scope": "public hosted-demo feasibility; not local or official benchmark evaluation",
        "host": HOST, "model": "baidu/Unlimited-OCR-2", "remote_weight_revision": "UNVERIFIED",
        "authentication": "anonymous; no credentials", "billing": "no paid API or subscription enabled",
        "parameters": {"instruction": "", "mode": "auto", "max_page_tokens": 20000},
        "attempts": [], "accuracy_scores": None}
    records = [json.loads(line) for line in (SUITE / "datasets/manifest/development.jsonl").read_text(encoding="utf-8").splitlines()]
    by_language = {lang: [r for r in records if r["language"] == lang] for lang in ("en", "ar")}
    records = [r for pair in zip(by_language["en"], by_language["ar"], strict=True) for r in pair]
    if not args.development:
        records = records[:2]
    reuse = reusable_results(args.reuse, records)
    summary.update(target_documents=len(records), reuse_source=str(args.reuse) if args.reuse else None)
    session = requests.Session()
    session.trust_env = False  # Do not implicitly use .netrc credentials.
    if args.authenticated:
        from huggingface_hub import get_token
        token = get_token()
        if not token:
            raise RuntimeError("No local Hugging Face login. Run hf auth login locally; never put a token in chat or trial files.")
        session.headers["Authorization"] = "Bearer " + token
        summary["authentication"] = "Saved Hugging Face credential; token not logged"
    deployment = session.get("https://huggingface.co/api/spaces/baidu/Unlimited-OCR-2", timeout=30)
    deployment.raise_for_status()
    metadata = deployment.json()
    save(out / "deployment_before.json", metadata)
    summary["demo_app_revision"] = metadata["sha"]
    if metadata["sha"] != "78c27d176793811cf8b5e74b62ceb04dd773c29a":
        raise RuntimeError("Hosted app deployment changed since inspection; stop before uploading")
    print(f"Hosted demo trial: {out}", flush=True)
    for index, record in enumerate(records, start=1):
        lang = record["language"]
        if record["document_id"] in reuse:
            summary["attempts"].append(reuse[record["document_id"]])
            save(out / "trial.json", summary)
            print(f"Reused verified {lang} result: {record['document_id']}", flush=True)
            continue
        page = out / f"{index:03}-{lang}"
        page.mkdir()
        save(page / "input.json", record)
        source = SUITE / record["source_path"]
        local = page / (record["file_hash"] + source.suffix)
        shutil.copy2(source, local)
        if hashlib.sha256(local.read_bytes()).hexdigest() != record["file_hash"]:
            raise ValueError("Frozen input checksum mismatch")
        state = {"language": lang, "document_id": record["document_id"], "status": "RUNNING",
                 "source_sha256": record["file_hash"], "documents_processed": 0}
        started = time.monotonic()
        try:
            with local.open("rb") as stream:
                reply = session.post(HOST + "/gradio_api/upload", files={"files": (local.name, stream, "image/png")}, timeout=45)
            reply.raise_for_status()
            uploaded = reply.json()[0]
            payload = {"data": [{"path": uploaded, "url": None, "size": local.stat().st_size,
                "orig_name": local.name, "mime_type": "image/png", "is_stream": False,
                "meta": {"_type": "gradio.FileData"}}, "", "auto", 20000]}
            save(page / "request.json", payload)
            reply = session.post(HOST + "/gradio_api/call/parse_page", json=payload, timeout=45)
            reply.raise_for_status()
            event_id = reply.json()["event_id"]
            state["event_id"] = event_id
            final = None
            event = None
            with session.get(HOST + "/gradio_api/call/parse_page/" + event_id,
                             stream=True, timeout=(20, 90)) as response, (page / "events.txt").open("x", encoding="utf-8") as log:
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if time.monotonic() - started > 240:
                        raise TimeoutError("Four-minute hosted request deadline exceeded")
                    if line is None:
                        continue
                    log.write(line + "\n")
                    log.flush()
                    if line.startswith("event:"):
                        event = line.split(":", 1)[1].strip()
                    elif line.startswith("data:"):
                        data = json.loads(line.split(":", 1)[1].strip())
                        if event == "error":
                            raise RuntimeError(f"Hosted demo error: {data}")
                        if event == "complete":
                            final = data[0]
                            break
            if not isinstance(final, dict) or not final.get("done"):
                raise RuntimeError("Hosted response did not contain a completed result")
            save(page / "response.json", final)
            (page / "prediction.md").write_text(final.get("markdown", ""), encoding="utf-8")
            (page / "raw.txt").write_text(final.get("raw", ""), encoding="utf-8")
            state.update(status="INCOMPLETE" if final.get("truncated") else "SUCCESS",
                documents_processed=0 if final.get("truncated") else 1, tokens=final.get("tokens"),
                remote_elapsed_seconds=final.get("elapsed"), truncated=final.get("truncated"),
                markdown_characters=len(final.get("markdown", "")))
        except Exception as exc:
            state.update(status="FAILED", error_type=type(exc).__name__, error=str(exc))
        state["request_wall_seconds"] = time.monotonic() - started
        save(page / "result.json", state)
        summary["attempts"].append(state)
        save(out / "trial.json", summary)
        print(json.dumps(state), flush=True)
        if state["status"] != "SUCCESS":
            break
    summary["status"] = "SUCCESS" if len(summary["attempts"]) == len(records) and all(a["status"] == "SUCCESS" for a in summary["attempts"]) else "NOT_COMPLETED"
    summary["reused_successes"] = sum(bool(a.get("reused")) for a in summary["attempts"])
    summary["fresh_successes"] = sum(a["status"] == "SUCCESS" and not a.get("reused") for a in summary["attempts"])
    summary["unattempted_documents"] = len(records) - len(summary["attempts"])
    save(out / "trial.json", summary)
    return 0 if summary["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
