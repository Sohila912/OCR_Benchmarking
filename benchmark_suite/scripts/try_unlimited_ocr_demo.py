"""Two public frozen pages through Baidu's linked free demo; not a local benchmark."""

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


def main():
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
    session = requests.Session()
    session.trust_env = False  # Do not implicitly use .netrc credentials.
    print(f"Hosted demo trial: {out}", flush=True)
    for lang in ("en", "ar"):
        record = next(r for r in records if r["language"] == lang)
        page = out / lang
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
    summary["status"] = "SUCCESS" if len(summary["attempts"]) == 2 and all(a["status"] == "SUCCESS" for a in summary["attempts"]) else "NOT_COMPLETED"
    save(out / "trial.json", summary)
    return 0 if summary["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
