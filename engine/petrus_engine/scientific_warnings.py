"""Stable scientific codes independent of presentation strings. No message heuristics."""

ERROR_CODES = {
    "errors.invalidTei": "grobid_invalid_response",
    "errors.grobidResponse": "grobid_invalid_response",
    "errors.pdfTooLarge": "pdf_size_limit",
    "errors.grobidUnavailable": "grobid_unavailable",
    "errors.fileUnavailable": "file_unavailable",
    "errors.rescanBeforeReprocess": "rescan_required",
    "errors.fileChanged": "file_changed",
    "errors.grobidFailed": "grobid_failed",
}


def failure_codes(error: Exception) -> list[str]:
    if isinstance(error, TimeoutError):
        return ["grobid_timeout"]
    if isinstance(error, ConnectionError):
        return ["grobid_unavailable"]
    return [ERROR_CODES.get(str(error), "grobid_failed")]


def structure_codes(document: dict) -> list[str]:
    return sorted(
        {
            "page_mapping_partial" if section["spans"] else "page_mapping_missing"
            for section in document["sections"]
            if section["page_start"] is None and section["text"].strip()
        }
    )
