# Tesseract

Phase 1 foundation for the SIH26189 investigator intelligence prototype.

## Start locally (Windows PowerShell)

1. Start Docker Desktop and wait until its engine is running.
2. Copy `.env.example` to `.env` and set local values. The default host port is `5433`.
3. From this folder, run `./scripts/setup.ps1`. It starts PostgreSQL, waits for readiness, applies migrations, and seeds the fictional demo metadata.
4. In one terminal run `cd apps/api; uvicorn app.main:app --reload`.
5. In another run `cd apps/web; npm run dev`.

Demo sign-in: `INV-017` with the value of `DEMO_PASSWORD`.

## Evidence processing

Prompt 3 uses the local Tesseract OCR executable plus `pdftoppm` for scanned PDF pages. Set `TESSERACT_CMD` and `PDFTOPPM_CMD` when these tools are not on `PATH`. The default OCR language configuration is `eng+hin`; install the Hindi `hin.traineddata` file in Tesseract's `tessdata` directory for Hindi OCR. Missing language data is reported as a processing warning rather than hidden.
