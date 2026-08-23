#!/usr/bin/env python3
"""Generate RapidOCR drafts for PDF pages without a useful text layer.

Drafts are retrieval aids only. They remain ``ocr_draft`` until a human changes
their status to ``verified`` after comparing every line with the rendered page.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pypdf import PdfReader
from pypdfium2 import PdfDocument
from rapidocr import RapidOCR


ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = ROOT / "resources" / "originals"
OUTPUT = ROOT / "resources" / "derived" / "ocr" / "pages.jsonl"
FORCE_OCR = {
    "resources/originals/rules/iron-bottom-sound-iv-rules-zh.pdf": {14},
}


def needs_ocr(source: str, page: int, text: str) -> bool:
    return len(text.strip()) < 40 or page in FORCE_OCR.get(source, set())


def result_text(result: object) -> tuple[str, list[float]]:
    texts = getattr(result, "txts", None) or []
    scores = getattr(result, "scores", None) or []
    return "\n".join(str(item) for item in texts), [float(item) for item in scores]


def generate(scale: float = 2.0) -> list[dict]:
    engine = RapidOCR()
    items: list[dict] = []
    for path in sorted(SOURCE_ROOT.rglob("*.pdf")):
        source = path.relative_to(ROOT).as_posix()
        reader = PdfReader(str(path))
        document = PdfDocument(str(path))
        for index, page in enumerate(reader.pages, start=1):
            extracted = page.extract_text() or ""
            if not needs_ocr(source, index, extracted):
                continue
            image = document[index - 1].render(scale=scale).to_pil()
            text, scores = result_text(engine(image))
            items.append(
                {
                    "source": source,
                    "page": index,
                    "text": text,
                    "status": "draft",
                    "engine": "rapidocr",
                    "mean_confidence": round(sum(scores) / len(scores), 4) if scores else 0,
                    "line_count": len(scores),
                }
            )
            print(f"OCR {source} page {index}: {len(scores)} lines")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in items), encoding="utf-8")
    return items


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=float, default=2.0)
    arguments = parser.parse_args()
    drafts = generate(arguments.scale)
    print(json.dumps({"draft_pages": len(drafts), "output": str(OUTPUT)}, ensure_ascii=False))
