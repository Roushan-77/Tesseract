# NLP processing boundary

Prompt 3 provides local PDF/image OCR, page-preserving OCR text, English/Hindi/mixed-script language detection, structured rule-based extraction, and entity mentions through `apps/api/app/processing.py`.

The current implementation does not perform entity resolution, relationship extraction, event extraction, or graph persistence. Those remain later-phase responsibilities.

Local prerequisites:

- Tesseract OCR with `eng` installed; add `hin.traineddata` for Hindi OCR.
- `pdftoppm` for scanned PDF pages.
- Optional `TESSERACT_CMD`, `PDFTOPPM_CMD`, and `TESSERACT_LANG` environment settings.
