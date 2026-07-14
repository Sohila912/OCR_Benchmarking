from typing import Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from runners.marker_runner import MarkerRunner
from runners.paddle_runner import PaddleRunner
from runners.Tesseract_runner import TesseractRunner

app = FastAPI(title="OCR Benchmarking API")


class ExtractRequest(BaseModel):
    engine: str
    pdf_path: str


class CompareRequest(BaseModel):
    pdf_path: str


class ExtractResponse(BaseModel):
    engine: str
    pdf_path: str
    markdown: str


class CompareResponse(BaseModel):
    pdf_path: str
    results: List[Dict[str, str]]


ENGINE_FACTORIES = {
    "marker": MarkerRunner,
    "paddle": PaddleRunner,
    "tesseract": TesseractRunner,
}


@app.get("/")
def root() -> Dict[str, str]:
    return {"message": "OCR Benchmarking API", "docs": "/docs"}


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/tools")
def tools() -> Dict[str, List[str]]:
    return {"tools": list(ENGINE_FACTORIES.keys())}


@app.post("/extract", response_model=ExtractResponse)
def extract(request: ExtractRequest) -> ExtractResponse:
    engine_name = request.engine.lower()
    if engine_name not in ENGINE_FACTORIES:
        raise HTTPException(status_code=400, detail=f"Unsupported engine: {request.engine}")

    runner = ENGINE_FACTORIES[engine_name]()
    markdown = runner.extract(request.pdf_path)
    return ExtractResponse(engine=engine_name, pdf_path=request.pdf_path, markdown=markdown)


@app.post("/extract/compare", response_model=CompareResponse)
def extract_compare(request: CompareRequest) -> CompareResponse:
    results = []
    for engine_name in ["marker", "paddle", "tesseract"]:
        runner = ENGINE_FACTORIES[engine_name]()
        markdown = runner.extract(request.pdf_path)
        results.append({"engine": engine_name, "markdown": markdown})

    return CompareResponse(pdf_path=request.pdf_path, results=results)
