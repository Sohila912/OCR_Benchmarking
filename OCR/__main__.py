"""Run the configured local API with: python -m OCR."""
from OCR.config import load_settings


def main() -> None:
    import uvicorn
    settings = load_settings()
    uvicorn.run("OCR.app:app", host=settings.api_host, port=settings.api_port, workers=1)


if __name__ == "__main__":
    main()
