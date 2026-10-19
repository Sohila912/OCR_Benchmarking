"""Read-only preflight checks; Ready requires a completed extraction in this process."""
import importlib.util
import requests
from OCR.resources import paddle_memory_issue

def diagnose(service):
    results = []
    settings = service.settings
    packages = {"paddle_vl": ("paddleocr", "paddle"), "docling": ("docling", "torch"), "qwen_ollama": ("ollama",)}
    assets = {"paddle_vl": ((settings.paddle_vl_model_dir, "OCR_PADDLE_VL_MODEL_DIR"),
                            (settings.paddle_layout_model_dir, "OCR_PADDLE_LAYOUT_MODEL_DIR")),
              "docling": ((settings.docling_artifacts_path, "OCR_DOCLING_ARTIFACTS_PATH"),)}
    for name, provider in service.providers.items():
        state, detail = "Not tested", "Preflight passed; run an inference smoke test."
        missing = [p for p in packages.get(name, ()) if importlib.util.find_spec(p) is None]
        if missing:
            state, detail = "Missing dependencies", "Install runtime packages: " + ", ".join(missing) + ". Use the ML image for Docling/Paddle."
        else:
            for path, variable in assets.get(name, ()):
                if path is None:
                    state, detail = "Not configured", "Set " + variable + " and mount existing model assets."
                    break
                if not path.is_dir() or not any(path.iterdir()):
                    state, detail = "Model unavailable", variable + " must point to populated model assets."
                    break
            else:
                issue = paddle_memory_issue(settings) if name == "paddle_vl" else None
                if issue:
                    state, detail = "Insufficient resources", issue
                if name == "qwen_ollama":
                    try:
                        response = requests.get(settings.ollama_host + "/api/tags", timeout=(3, 5))
                        response.raise_for_status()
                        names = {m.get("name") for m in response.json()["models"]}
                        if settings.ollama_ocr_model not in names:
                            state, detail = "Model unavailable", "Configured Ollama model tag is absent; choose an installed tag or explicitly pull it."
                    except (requests.RequestException, ValueError, KeyError, TypeError):
                        state, detail = "Server unreachable", "Check Ollama server binding, firewall and OLLAMA_HOST; Docker Desktop uses host.docker.internal."
                evidence = service.inference_checks.get(name)
                if detail.startswith("Preflight") and evidence:
                    state, detail = evidence["state"], evidence["detail"]
                elif detail.startswith("Preflight") and provider.health().status in ("error", "unavailable"):
                    state, detail = "Initialization failed", "Initialization failed; verify assets and runtime versions."
        results.append({"provider": name, "state": state, "detail": detail,
                        "inference_verified": state == "Ready",
                        "configuration_ready": state in ("Not tested", "Ready", "Initialization failed", "Inference failed", "Insufficient resources"),
                        "lifecycle": provider.health().status})
    return results
