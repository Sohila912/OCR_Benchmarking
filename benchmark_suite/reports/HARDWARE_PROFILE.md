# Hardware profile

Captured: 2026-10-28T14:45:18+03:00 (Africa/Cairo).
Read-only native/metadata probes; no model or framework imports, installations or inference.

| Field | Observation |
|---|---|
| CPU | 11th Gen Intel(R) Core(TM) i7-1165G7 @ 2.80GHz; 4 cores / 8 threads |
| RAM total / available | 7.74 GiB / 0.61 GiB |
| Windows | {'caption': 'Microsoft Windows 11 Pro', 'build': '26200', 'version': '10.0.26200'} |
| Collector / target Python | 3.13.7 / Python 3.13.7 |
| Architecture | AMD64 |
| Display adapter | NVIDIA GeForce MX350; WMI driver 32.0.15.8267; AdapterRAM is not reliable dedicated VRAM |
| Display adapter | Intel(R) Iris(R) Xe Graphics; WMI driver 32.0.101.7088; AdapterRAM is not reliable dedicated VRAM |
| NVIDIA GPU | NVIDIA GeForce MX350; 2048 MiB dedicated VRAM; 1965 MiB free; CC 6.1; driver 582.67 |
| Driver CUDA ceiling | 13.0 |
| CUDA toolkit (nvcc) | NOT_FOUND |
| Disk free / total | 24.78 GiB / 237.38 GiB |
| WSL status | Default Distribution: docker-desktop; Default Version: 2 |
| WSL distributions | NAME              STATE           VERSION; * docker-desktop    Running         2;   Ubuntu            Stopped         2 |
| Tesseract version | tesseract v5.4.0.20240606 |
| Tesseract language assets | eng, osd |
| Poppler | pdftoppm version 26.07.0 |
| Model loading gate | {'status': 'BLOCKED_BY_HARDWARE', 'reason': 'Less than 2 GiB free RAM; block model loading until rechecked.', 'floor_basis': 'Conservative suite policy; not a vendor minimum.'} |

## Installed package evidence

| Distribution | Version / evidence |
|---|---|
| torch | {"version": "2.14.1", "requires_python": ">=3.10", "__version__": "2.14.1+cpu", "cuda": null, "hip": null} |
| torchvision | {"version": "0.29.1", "requires_python": ">=3.10,!=3.14.1"} |
| paddlepaddle | {"version": "3.2.2", "requires_python": null} |
| paddlepaddle-gpu | NOT_INSTALLED |
| paddleocr | {"version": "3.6.0", "requires_python": ">=3.8"} |
| docling | {"version": "2.80.0", "requires_python": "<4.0,>=3.10"} |
| easyocr | NOT_INSTALLED |
| transformers | {"version": "4.57.6", "requires_python": ">=3.9.0"} |
| surya-ocr | NOT_INSTALLED |
| marker-pdf | NOT_INSTALLED |

## Interpretation and limits

- RAM/free VRAM/disk are a point-in-time snapshot. Recheck immediately before each model; availability can fall.
- NVIDIA-SMI's CUDA number is driver capability, not an installed toolkit or usable framework CUDA build. nvcc NOT_FOUND means not on PATH, not proof no toolkit exists anywhere.
- A torch version.py cuda=null / +cpu build is CPU-only. paddlepaddle installed without paddlepaddle-gpu provides no evidence of a GPU-enabled Paddle runtime. Framework runtime calls were intentionally skipped to avoid memory pressure; no torch/paddle imports occurred.
- Integrated Intel AdapterRAM is a WMI display value, not a separate dedicated VRAM bank; never add it to NVIDIA VRAM.
- WSL inventory does not start a distribution or certify CUDA passthrough. WSL2 presence cannot fix insufficient physical RAM/VRAM or GPU architecture.
- The 2 GiB available-RAM gate is a conservative suite safety floor, not a documented minimum for any model. Passing it still requires model-specific preflight in TASK-007.
- Exact native probe statuses and sanitized evidence are in HARDWARE_PROFILE.json. No machine hostname, serials, environment secrets or running-process inventory is stored.
