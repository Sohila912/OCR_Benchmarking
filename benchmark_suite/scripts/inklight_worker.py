"""Read one frozen image inside a bounded Windows worker."""

import json
import sys
from pathlib import Path

from benchmark_suite.scripts.windows_job import limit_current_process


def main():
    request = json.load(sys.stdin.buffer)
    options = request["options"]
    limit_current_process(options["worker_memory_bytes"])

    from inklight import build_commit
    from inklight.config import OCRSettings
    from inklight.ocr.engine import InklightOCR

    if build_commit() != request["revision"]:
        raise RuntimeError("InkLight source revision differs from the pinned spec")
    settings = OCRSettings(model_dir=options["model_dir"], threads=options["threads"], mode=options["mode"])
    reading = InklightOCR(settings).read(Path(request["path"]), max_pages=1)
    sys.stdout.buffer.write(reading.model_dump_json().encode("utf-8"))


if __name__ == "__main__":
    main()
