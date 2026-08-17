"""Extracao de texto de curriculos para viabilizar busca e ranking."""

import io

import docx
from pypdf import PdfReader


def extract_text(content: bytes, mime_type: str | None, filename: str) -> str:
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if mime_type == "application/pdf" or suffix == "pdf":
        return _extract_pdf(content)

    if suffix in ("docx",) or mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return _extract_docx(content)

    if suffix == "txt" or (mime_type and mime_type.startswith("text/")):
        return content.decode("utf-8", errors="ignore")

    raise ValueError(f"Formato de curriculo nao suportado para extracao de texto: {filename}")


def _extract_pdf(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx(content: bytes) -> str:
    document = docx.Document(io.BytesIO(content))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)
