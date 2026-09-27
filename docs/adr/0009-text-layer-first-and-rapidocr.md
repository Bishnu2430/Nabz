# ADR-0009 · Text layer first, then RapidOCR

**Status:** Accepted · 2026-09-27 · refines the OCR choice in [03 §6](../03-system-architecture.md#6-technology-stack)

## Context

The architecture named PaddleOCR (PP-OCRv5) for reading reports. Two things became clear in Sprint 2:

1. **Most lab reports people receive are digital PDFs** (sent on WhatsApp or email), and they carry an exact text layer with positions. OCR on those would add errors and about 10 seconds per page for nothing.
2. **The full PaddleOCR stack** (the PaddlePaddle framework) is a large dependency for CPU-only inference in a container. RapidOCR runs the same PaddleOCR detection and recognition models on ONNX Runtime, with the models bundled in the package.

## Decision

- **Text layer first.** For each PDF page, read text runs and their boxes from the PDF with PDFium (`pypdfium2`). Fall back to OCR only when a page has less than 40 characters of text (scanned PDFs) or for images.
- **OCR with RapidOCR** (`rapidocr-onnxruntime`: PaddleOCR models, ONNX Runtime, Apache-2.0) on CPU, at 200 dpi.
  - The desktop OpenCV build it pulls in is replaced by `opencv-python-headless` (a uv override).
  - The **line-orientation classifier is disabled**: it flipped upright lines ("mg/dl" became "Ip/6w").
- **Deskew before OCR** with a projection-profile search (error < 0.05° in tests).
- **Layout-agnostic parser.** Group tokens into lines, then classify each segment as name, value, flag, unit or range. There are no fixed column positions, so tabular, boxed and dotted-leader reports all work.

## Consequences

Measured on synthetic reports ([11 §9](../11-test-and-evaluation-plan.md#9-sprint-2-extraction-results)):
- The **text layer is exact**: 100 % on every field.
- **OCR on clean renders** meets the clean-scan target.
- **Simulated phone photos** reach 94.6 % row recall with 100 % precision.

Known limits, handled downstream:
- OCR drops spaces between English words, so the catalogue matcher compares names without spaces.
- OCR occasionally misreads µ, and an occasional digit ("94" read as "944"). Sprint 3's confidence model must treat a value far outside its own printed range as suspicious, so these rows are reviewed first.

If accuracy on real photos falls short (risk R-01), the recognition model can be swapped for an English-only PP-OCR model, or the consent-gated vision fallback can be used ([ADR-0007](0007-groq-gpt-oss-for-explanations.md)).
