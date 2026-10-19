"""Run the configured local API with: python -m OCR."""
import logging

from OCR.config import load_settings


def main() -> None:
    import uvicorn
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s', force=True)
    settings = load_settings()
    uvicorn.run("OCR.app:app", host=settings.api_host, port=settings.api_port, workers=1)


if __name__ == "__main__":
    main()
