FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
ARG INSTALL_LOCAL_MODELS=false
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils tesseract-ocr tesseract-ocr-eng tesseract-ocr-ara libglib2.0-0 libgomp1 libgl1 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements-benchmark.txt requirements-models.txt requirements-docker-models.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-benchmark.txt
RUN if [ "$INSTALL_LOCAL_MODELS" = "true" ]; then pip install --no-cache-dir "torch>=2.7,<3" --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir -r requirements-docker-models.txt; fi
RUN if [ "$INSTALL_LOCAL_MODELS" = "true" ]; then pip install --no-cache-dir --force-reinstall --no-deps torchvision --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir -r requirements.txt -r requirements-benchmark.txt -r requirements-docker-models.txt && pip check; fi
COPY OCR ./OCR
COPY frontend ./frontend
COPY scripts/check_models.py ./scripts/check_models.py
COPY benchmarks/__init__.py benchmarks/run.py ./benchmarks/
COPY benchmarks/evaluation ./benchmarks/evaluation
COPY .streamlit ./.streamlit
RUN useradd --uid 10001 --create-home ocr && mkdir -p runtime /home/ocr/.cache && chown -R ocr:ocr runtime /home/ocr/.cache
USER ocr
EXPOSE 8000 8501
CMD ["python", "-m", "OCR"]
