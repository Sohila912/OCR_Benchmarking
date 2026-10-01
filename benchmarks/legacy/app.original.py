# from contextlib import asynccontextmanager
# from typing import Dict, List

# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel

# from runners.marker_runner import MarkerRunner
# from runners.paddle_runner import PaddleRunner
# from runners.Tesseract_runner import TesseractRunner


# # ============================================================
# # Initialize OCR engines ONCE when FastAPI starts
# # ============================================================

# @asynccontextmanager
# async def lifespan(app: FastAPI):

#     print("\n========================================")
#     print("Initializing OCR engines...")
#     print("========================================")

#     print("\n--- Initializing Marker ---")
#     app.state.marker = MarkerRunner()

#     print("\n--- Initializing Paddle ---")
#     app.state.paddle = PaddleRunner()

#     print("\n--- Initializing Tesseract ---")
#     app.state.tesseract = TesseractRunner()

#     print("\n========================================")
#     print("OCR engines are ready.")
#     print("========================================\n")

#     yield

#     print("\nShutting down OCR engines...")


# app = FastAPI(
#     title="OCR Benchmarking API",
#     lifespan=lifespan
# )


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


# # ============================================================
# # Map engine names to initialized runners
# # ============================================================

# def get_runner(engine_name: str):

#     if engine_name == "marker":
#         return app.state.marker

#     if engine_name == "paddle":
#         return app.state.paddle

#     if engine_name == "tesseract":
#         return app.state.tesseract

#     raise HTTPException(
#         status_code=400,
#         detail=f"Unsupported engine: {engine_name}"
#     )


# # ============================================================
# # Routes
# # ============================================================

# @app.get("/")
# def root() -> Dict[str, str]:
#     return {
#         "message": "OCR Benchmarking API",
#         "docs": "/docs"
#     }


# @app.get("/health")
# def health() -> Dict[str, str]:
#     return {"status": "ok"}


# @app.get("/tools")
# def tools() -> Dict[str, List[str]]:
#     return {
#         "tools": [
#             "marker",
#             "paddle",
#             "tesseract"
#         ]
#     }


# # ============================================================
# # Single engine extraction
# # ============================================================

# @app.post("/extract", response_model=ExtractResponse)
# def extract(request: ExtractRequest) -> ExtractResponse:

#     engine_name = request.engine.lower()

#     runner = get_runner(engine_name)

#     markdown = runner.extract(request.pdf_path)

#     return ExtractResponse(
#         engine=engine_name,
#         pdf_path=request.pdf_path,
#         markdown=markdown
#     )


# # ============================================================
# # Compare all engines
# # ============================================================

# @app.post("/extract/compare", response_model=CompareResponse)
# def extract_compare(
#     request: CompareRequest
# ) -> CompareResponse:

#     results = []

#     for engine_name in [
#         "marker",
#         "paddle",
#         "tesseract"
#     ]:

#         runner = get_runner(engine_name)

#         markdown = runner.extract(request.pdf_path)

#         results.append({
#             "engine": engine_name,
#             "markdown": markdown
#         })

#     return CompareResponse(
#         pdf_path=request.pdf_path,
#         results=results
#     ) 
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from runners.marker_runner import MarkerRunner
from runners.paddle_runner import PaddleRunner
from runners.Tesseract_runner import TesseractRunner


# ============================================================
# DIRECTORIES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


# ============================================================
# OCR ENGINE INITIALIZATION
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    print("\n========================================")
    print("Initializing OCR engines...")
    print("========================================")

    print("\n--- Initializing Marker ---")
    app.state.marker = MarkerRunner()

    print("\n--- Initializing PaddleOCR ---")
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
    description="OCR Benchmarking Platform",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================================
# RESPONSE MODELS
# ============================================================

class ExtractResponse(BaseModel):
    engine: str
    filename: str
    markdown: str


class CompareResult(BaseModel):
    engine: str
    markdown: str


class CompareResponse(BaseModel):
    filename: str
    results: List[CompareResult]


# ============================================================
# ENGINE MANAGEMENT
# ============================================================

def get_runner(engine_name: str):

    engine_name = engine_name.lower()

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
# SAVE UPLOADED FILE
# ============================================================

async def save_pdf(file: UploadFile) -> Path:

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    file_path = UPLOAD_DIR / file.filename

    content = await file.read()

    with open(file_path, "wb") as f:
        f.write(content)

    return file_path


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root() -> Dict[str, str]:

    return {
        "message": "OCR Benchmarking API",
        "docs": "/docs"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health() -> Dict[str, str]:

    return {
        "status": "ok"
    }


# ============================================================
# AVAILABLE TOOLS
# ============================================================

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
# SINGLE ENGINE EXTRACTION
# ============================================================

@app.post("/extract", response_model=ExtractResponse)
async def extract(
    engine: str = Form(...),
    file: UploadFile = File(...)
):

    engine_name = engine.lower()

    runner = get_runner(engine_name)

    pdf_path = await save_pdf(file)

    try:

        markdown = runner.extract(
            str(pdf_path)
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"{engine_name} extraction failed: {str(e)}"
        )

    return ExtractResponse(
        engine=engine_name,
        filename=file.filename,
        markdown=markdown
    )


# ============================================================
# COMPARE ALL ENGINES
# ============================================================

@app.post("/extract/compare", response_model=CompareResponse)
async def extract_compare(
    file: UploadFile = File(...)
):

    pdf_path = await save_pdf(file)

    results = []

    engines = [
        "marker",
        "paddle",
        "tesseract"
    ]

    for engine_name in engines:

        runner = get_runner(engine_name)

        try:

            print(
                f"\nRunning {engine_name} on "
                f"{file.filename}..."
            )

            markdown = runner.extract(
                str(pdf_path)
            )

            results.append(
                CompareResult(
                    engine=engine_name,
                    markdown=markdown
                )
            )

            print(
                f"{engine_name} completed."
            )

        except Exception as e:

            results.append(
                CompareResult(
                    engine=engine_name,
                    markdown=(
                        f"ERROR: {str(e)}"
                    )
                )
            )

            print(
                f"{engine_name} failed: {str(e)}"
            )

    return CompareResponse(
        filename=file.filename,
        results=results
    )