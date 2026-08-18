# from typing import Dict, List

# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel

# from runners.marker_runner import MarkerRunner
# from runners.paddle_runner import PaddleRunner
# from runners.Tesseract_runner import TesseractRunner

# app = FastAPI(title="OCR Benchmarking API")


# class ExtractRequest(BaseModel):
#     engine: str
#     pdf_path: str


# class CompareRequest(BaseModel):
#     pdf_path: str


# class ExtractResponse(BaseModel):
#     engine: str
#     pdf_path: str
#     markdown: str


# class CompareResponse(BaseModel):
#     pdf_path: str
#     results: List[Dict[str, str]]


# ENGINE_FACTORIES = {
#     "marker": MarkerRunner,
#     "paddle": PaddleRunner,
#     "tesseract": TesseractRunner,
# }


# @app.get("/")
# def root() -> Dict[str, str]:
#     return {"message": "OCR Benchmarking API", "docs": "/docs"}


# @app.get("/health")
# def health() -> Dict[str, str]:
#     return {"status": "ok"}


# @app.get("/tools")
# def tools() -> Dict[str, List[str]]:
#     return {"tools": list(ENGINE_FACTORIES.keys())}


# @app.post("/extract", response_model=ExtractResponse)
# def extract(request: ExtractRequest) -> ExtractResponse:
#     engine_name = request.engine.lower()
#     if engine_name not in ENGINE_FACTORIES:
#         raise HTTPException(status_code=400, detail=f"Unsupported engine: {request.engine}")

#     runner = ENGINE_FACTORIES[engine_name]()
#     markdown = runner.extract(request.pdf_path)
#     return ExtractResponse(engine=engine_name, pdf_path=request.pdf_path, markdown=markdown)


# @app.post("/extract/compare", response_model=CompareResponse)
# def extract_compare(request: CompareRequest) -> CompareResponse:
#     results = []
#     for engine_name in ["marker", "paddle", "tesseract"]:
#         runner = ENGINE_FACTORIES[engine_name]()
#         markdown = runner.extract(request.pdf_path)
#         results.append({"engine": engine_name, "markdown": markdown})

#     return CompareResponse(pdf_path=request.pdf_path, results=results)
from contextlib import asynccontextmanager
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from runners.marker_runner import MarkerRunner
from runners.paddle_runner import PaddleRunner
from runners.Tesseract_runner import TesseractRunner


# ============================================================
# Initialize OCR engines ONCE when FastAPI starts
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    print("\n========================================")
    print("Initializing OCR engines...")
    print("========================================")

    print("\n--- Initializing Marker ---")
    app.state.marker = MarkerRunner()

    print("\n--- Initializing Paddle ---")
    app.state.paddle = PaddleRunner()

    print("\n--- Initializing Tesseract ---")
    app.state.tesseract = TesseractRunner()

    print("\n========================================")
    print("OCR engines are ready.")
    print("========================================\n")

    yield

    print("\nShutting down OCR engines...")


app = FastAPI(
    title="OCR Benchmarking API",
    lifespan=lifespan
)


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


# ============================================================
# Map engine names to initialized runners
# ============================================================

def get_runner(engine_name: str):

    if engine_name == "marker":
        return app.state.marker

    if engine_name == "paddle":
        return app.state.paddle

    if engine_name == "tesseract":
        return app.state.tesseract

    raise HTTPException(
        status_code=400,
        detail=f"Unsupported engine: {engine_name}"
    )


# ============================================================
# Routes
# ============================================================

@app.get("/")
def root() -> Dict[str, str]:
    return {
        "message": "OCR Benchmarking API",
        "docs": "/docs"
    }


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/tools")
def tools() -> Dict[str, List[str]]:
    return {
        "tools": [
            "marker",
            "paddle",
            "tesseract"
        ]
    }


# ============================================================
# Single engine extraction
# ============================================================

@app.post("/extract", response_model=ExtractResponse)
def extract(request: ExtractRequest) -> ExtractResponse:

    engine_name = request.engine.lower()

    runner = get_runner(engine_name)

    markdown = runner.extract(request.pdf_path)

    return ExtractResponse(
        engine=engine_name,
        pdf_path=request.pdf_path,
        markdown=markdown
    )


# ============================================================
# Compare all engines
# ============================================================

@app.post("/extract/compare", response_model=CompareResponse)
def extract_compare(
    request: CompareRequest
) -> CompareResponse:

    results = []

    for engine_name in [
        "marker",
        "paddle",
        "tesseract"
    ]:

        runner = get_runner(engine_name)

        markdown = runner.extract(request.pdf_path)

        results.append({
            "engine": engine_name,
            "markdown": markdown
        })

    return CompareResponse(
        pdf_path=request.pdf_path,
        results=results
    )