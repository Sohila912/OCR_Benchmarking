"""HTTP transport only; provider lifecycle and extraction remain in the API."""
import time

import requests

from OCR.schemas import OCRResult


def request_error(exc: requests.RequestException) -> str:
    if exc.response is not None:
        try:
            detail = exc.response.json().get("detail")
            if isinstance(detail, dict):
                return detail.get("message", "Extraction failed.")
            if isinstance(detail, str):
                return detail
        except (ValueError, AttributeError):
            pass
        return f"The service returned HTTP {exc.response.status_code}. Review provider setup and try again."
    if isinstance(exc, requests.Timeout):
        return "The request timed out. Processing may still be running; check provider status before retrying."
    return "Cannot reach the OCR service. Start the API and verify its connection settings."


def extract_document(api_url: str, filename: str, payload: bytes, provider: str) -> dict:
    started = time.monotonic()
    try:
        response = requests.post(f"{api_url}/extract",
                                 files={"file": (filename, payload, "application/pdf")},
                                 data={"engine": provider}, timeout=(5, 3600))
        response.raise_for_status()
        result = OCRResult.model_validate(response.json()).model_dump(mode="json")
        return {"provider": provider, "result": result, "elapsed": time.monotonic() - started}
    except requests.RequestException as exc:
        return {"provider": provider, "error": request_error(exc)}
    except ValueError:
        return {"provider": provider, "error": "The service returned an invalid OCR result. Verify the API version."}
