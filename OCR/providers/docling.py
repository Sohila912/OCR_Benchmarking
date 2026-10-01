"""Docling's standard PDF pipeline, explicitly using Tesseract CLI OCR."""

import os

from OCR.errors import ExtractionError, ProviderInitializationError
from OCR.providers.base import OCRDocument
from OCR.providers.common import LocalProvider, package_version, require_assets
from OCR.providers.tesseract import probe_tesseract
from OCR.schemas import BoundingBox, OCRBlock, OCRIssue, OCRPage, OCRResult, attach_text_provenance


def normalize_docling(document: OCRDocument, result, model_version: str | None,
                      model_revision: str | None) -> OCRResult:
    doc = result.document
    exported = doc.export_to_dict()
    pages = {}
    for key, value in exported.get("pages", {}).items():
        number = int(value.get("page_no", key))
        size = value.get("size") or {}
        pages[number] = OCRPage(page_number=number, width=size.get("width"), height=size.get("height"),
                                dimension_units="points" if size else None, blocks=[])
    warnings = []
    # Iteration preserves Docling's hierarchy order; the source self_ref is retained.
    for item, depth in doc.iterate_items():
        data = item.model_dump(mode="json")
        provenance = data.get("prov", [])
        if not provenance:
            if data.get("text"):
                warnings.append(OCRIssue(code="missing_item_provenance", message=f"Item {data.get('self_ref')} has no page provenance."))
            continue
        for occurrence, prov in enumerate(provenance):
            number = int(prov["page_no"])
            page = pages.setdefault(number, OCRPage(page_number=number, blocks=[]))
            raw_box = prov.get("bbox")
            box = None
            if raw_box:
                origin = raw_box.get("coord_origin")
                if origin in ("TOPLEFT", "BOTTOMLEFT"):
                    box = BoundingBox(x_min=min(raw_box["l"], raw_box["r"]), x_max=max(raw_box["l"], raw_box["r"]),
                                      y_min=min(raw_box["t"], raw_box["b"]), y_max=max(raw_box["t"], raw_box["b"]),
                                      units="points", origin="top_left" if origin == "TOPLEFT" else "bottom_left")
            text = data.get("text")
            span = prov.get("charspan")
            # Docling charspan refers to the item's text, avoiding duplication across pages.
            if text is not None and span is not None:
                start, end = span
                if not 0 <= start <= end <= len(text):
                    raise ValueError("Docling returned an invalid item character span.")
                text = text[start:end]
            if text is None and data.get("data", {}).get("table_cells"):
                # Table text is supplied by cells; structure is preserved in raw metadata.
                # Do not assign a multi-page table's entire content to a single page.
                if len(provenance) == 1:
                    text = "\n".join(cell.get("text", "") for cell in data["data"]["table_cells"])
                else:
                    page.warnings.append(OCRIssue(code="table_text_provenance_unavailable",
                        message="Multi-page table text is retained in item metadata and Markdown; no per-page cell assignment was supplied.",
                        page_number=number))
            source_ref = data.get("self_ref")
            page.blocks.append(OCRBlock(
                block_id=f"{source_ref}:prov{occurrence}" if source_ref else None,
                block_type=data.get("label"), text=text, bounding_box=box,
                provider_metadata={"source_ref": source_ref, "provenance": prov,
                                   "hierarchy_depth": depth, "item": data},
            ))
    ordered = [pages[n] for n in sorted(pages)]
    for page in ordered:
        page.text = "\n\n".join(block.text for block in page.blocks if block.text is not None)
        page.markdown = doc.export_to_markdown(page_no=page.page_number)
    issues = [OCRIssue(code="docling_conversion_error", message=str(e.error_message)) for e in result.errors]
    status = str(getattr(result.status, "value", result.status))
    if status == "partial_success" and not issues:
        issues.append(OCRIssue(code="partial_conversion", message="Docling reported partial conversion."))
    return attach_text_provenance(OCRResult(document_id=document.document_id, filename=document.filename, source=document.source,
                     source_metadata=document.source_metadata,
                     provider="docling", model_name="Docling standard PDF + Tesseract", model_version=model_revision,
                     text="\n\n".join(page.text for page in ordered), markdown=doc.export_to_markdown(), pages=ordered,
                     warnings=warnings + [i for p in ordered for i in p.warnings], errors=issues,
                     provider_metadata={"package_version": model_version, "conversion_status": status,
                                        "text_assembly": "page items; table cells when single-page"}))


class DoclingProvider(LocalProvider):
    provider_id = "docling"

    def initialize(self) -> None:
        if self.health().status == "ready":
            return
        try:
            assets = require_assets(self.settings.docling_artifacts_path, "OCR_DOCLING_ARTIFACTS_PATH")
            self._tesseract_version = probe_tesseract(self.settings.tesseract_cmd, self.settings.tesseract_lang,
                                                     self.settings.operation_timeout)
            # Set before importing Hugging Face-dependent libraries. This process serves local OCR only.
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.accelerator_options import AcceleratorOptions
            from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractCliOcrOptions
            from docling.document_converter import DocumentConverter, PdfFormatOption

            options = PdfPipelineOptions(
                artifacts_path=assets, enable_remote_services=False, do_ocr=True,
                do_table_structure=True, do_picture_classification=False, do_picture_description=False,
                do_code_enrichment=False, do_formula_enrichment=False,
                document_timeout=self.settings.operation_timeout,
                accelerator_options=AcceleratorOptions(device=self.settings.docling_device),
                ocr_options=TesseractCliOcrOptions(lang=self.settings.tesseract_lang.split("+"),
                                                  tesseract_cmd=self.settings.tesseract_cmd),
            )
            converter = DocumentConverter(allowed_formats=[InputFormat.PDF],
                                          format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
            converter.initialize_pipeline(InputFormat.PDF)
            self._converter = converter
        except Exception as exc:
            self._state("unavailable", "Initialization failed; check server logs and local model assets.")
            raise ProviderInitializationError(str(exc), provider=self.provider_id) from exc
        self._state("ready")

    def extract(self, document: OCRDocument) -> OCRResult:
        self._require_ready(document)
        try:
            result = self._converter.convert(document.path, raises_on_error=False,
                                             max_num_pages=self.settings.max_pages,
                                             max_file_size=self.settings.max_upload_bytes)
            status = str(getattr(result.status, "value", result.status))
            if status not in ("success", "partial_success"):
                raise ExtractionError(f"Docling conversion status: {status}.", provider=self.provider_id)
            normalized = normalize_docling(document, result, package_version("docling"), self.settings.docling_model_revision)
            normalized.provider_metadata.update(tesseract_version=self._tesseract_version,
                                                recognition_languages=self.settings.tesseract_lang.split("+"))
            return normalized
        except ExtractionError:
            raise
        except Exception as exc:
            raise ExtractionError("Docling extraction or result normalization failed.", provider=self.provider_id) from exc
