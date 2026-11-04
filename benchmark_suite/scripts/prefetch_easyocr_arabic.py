"""Resume the publisher's EasyOCR Arabic model archive on D: and verify it."""

import hashlib
import json
from pathlib import Path
import shutil
import time
import zipfile

import requests

ROOT = Path("D:/OCR_Benchmarking_Assets/docling_easyocr")
URL = "https://github.com/JaidedAI/EasyOCR/releases/download/pre-v1.1.6/arabic.zip"
SIZE = 199916962
MODEL_MD5 = "993074555550e4e06a6077d55ff0449a"


def main():
    downloads = ROOT / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    archive = downloads / "arabic-resumable.zip"
    evidence = downloads / "arabic-acquisition.json"
    target = ROOT / "easyocr/model/arabic.pth"
    state = {"url": URL, "expected_archive_bytes": SIZE, "expected_model_md5": MODEL_MD5,
             "archive": str(archive), "target": str(target), "status": "DOWNLOADING", "errors": []}

    def checkpoint():
        state["downloaded_bytes"] = archive.stat().st_size if archive.exists() else 0
        evidence.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    if not archive.exists():
        partials = [ROOT / "easyocr/model/temp.zip", downloads / "arabic-20261104.zip"]
        partials = [p for p in partials if p.is_file() and 0 < p.stat().st_size < SIZE]
        if partials:
            source = max(partials, key=lambda p: p.stat().st_size)
            shutil.copy2(source, archive)
            state["initial_prefix_source"] = str(source)
        else:
            archive.touch(exist_ok=False)
    if archive.stat().st_size > SIZE:
        raise ValueError("Archive exceeds publisher size; preserve and inspect it")
    session = requests.Session()
    session.trust_env = False
    started = last_progress = time.monotonic()
    checkpoint()
    print(f"Resuming Arabic archive at {archive.stat().st_size}/{SIZE} bytes on D:", flush=True)
    try:
        for attempt in range(1, 5):
            offset = archive.stat().st_size
            if offset == SIZE:
                break
            try:
                with session.get(URL, headers={"Range": f"bytes={offset}-"}, stream=True,
                                 timeout=(20, 30)) as response:
                    response.raise_for_status()
                    expected = f"bytes {offset}-{SIZE-1}/{SIZE}"
                    if response.status_code != 206 or response.headers.get("Content-Range") != expected:
                        raise ValueError("Publisher did not honor the exact resume range")
                    with archive.open("ab") as output:
                        for chunk in response.iter_content(64 * 1024):
                            if not chunk:
                                continue
                            output.write(chunk)
                            if time.monotonic() - last_progress >= 15:
                                output.flush()
                                checkpoint()
                                print(f"Arabic download: {archive.stat().st_size}/{SIZE} bytes", flush=True)
                                last_progress = time.monotonic()
                            if time.monotonic() - started > 2700:
                                raise TimeoutError("45-minute acquisition deadline; partial archive preserved")
            except requests.RequestException as exc:
                state["errors"].append({"attempt": attempt, "type": type(exc).__name__, "error": str(exc)})
                checkpoint()
                if isinstance(exc, requests.HTTPError) or attempt == 4:
                    raise
                print(f"Transfer interrupted; resuming saved bytes (attempt {attempt+1}/4)", flush=True)
                time.sleep(2)
        if archive.stat().st_size != SIZE:
            raise ValueError("Incomplete archive length")
        state["archive_sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
        with zipfile.ZipFile(archive) as zipped:
            if zipped.namelist() != ["arabic.pth"]:
                raise ValueError("Unexpected archive member; no extraction performed")
            model = zipped.read("arabic.pth")
        if hashlib.md5(model).hexdigest() != MODEL_MD5:
            raise ValueError("Publisher model MD5 mismatch; no model installed")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(model).digest():
                raise ValueError("Existing model differs; refusing to overwrite")
        else:
            with target.open("xb") as output:
                output.write(model)
        state.update(status="VERIFIED", model_bytes=len(model),
                     model_sha256=hashlib.sha256(model).hexdigest(), elapsed_seconds=time.monotonic()-started)
        checkpoint()
        print(f"Arabic model cached and verified on D: ({len(model)} bytes)", flush=True)
        return 0
    except Exception as exc:
        state.update(status="NOT_COMPLETED", error_type=type(exc).__name__, error=str(exc))
        checkpoint()
        raise


if __name__ == "__main__":
    raise SystemExit(main())
