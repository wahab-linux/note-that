"""Read study documents without saving the original upload to disk."""
from __future__ import annotations

import base64
import io
import re
import time
import uuid
import zipfile
from pathlib import PurePosixPath
from typing import Any

import pymupdf
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from PIL import Image, UnidentifiedImageError

MAX_BYTES = 100 * 1024 * 1024
MAX_PAGES = 300
MAX_PIXELS = 40_000_000
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
SUPPORTED = IMAGE_EXTENSIONS | {"pdf", "pptx"}


class DocumentError(ValueError):
    """An actionable problem with an uploaded document."""


def _data_url(data: bytes, mime: str = "image/webp") -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def _image(data: bytes) -> str:
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > MAX_PIXELS:
                raise DocumentError("Please choose an image smaller than 40 megapixels.")
            image.thumbnail((1800, 1800))
            output = io.BytesIO()
            image.convert("RGB").save(output, format="WEBP", quality=88)
            return _data_url(output.getvalue())
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise DocumentError("This image could not be opened. Try another image or a PDF.") from exc


def _pdf(data: bytes, deck: dict[str, Any]) -> None:
    try:
        document = pymupdf.open(stream=data, filetype="pdf")
    except (pymupdf.FileDataError, RuntimeError) as exc:
        raise DocumentError("This PDF could not be opened. Please check the file and try again.") from exc
    with document:
        if document.needs_pass:
            raise DocumentError("This PDF is password protected. Please upload an unlocked copy.")
        if not 1 <= len(document) <= MAX_PAGES:
            raise DocumentError("Please use a PDF with 1–300 pages.")
        for index, page in enumerate(document):
            rect = page.rect
            if rect.width <= 0 or rect.height <= 0:
                raise DocumentError(f"Page {index + 1} has an invalid size. Please re-export this PDF.")
            # Cap both dimensions, including unusually tall or wide slides.
            scale = min(1.7, 1500 / max(rect.width, rect.height))
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
            rendered = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            output = io.BytesIO()
            rendered.save(output, format="WEBP", quality=85)
            deck["slides"].append({
                "id": f"{deck['id']}-{index + 1}",
                "title": " ".join(page.get_text().split())[:100] or f"Page {index + 1}",
                "body": "", "page": index + 1, "image": _data_url(output.getvalue()),
            })
        starts = {page - 1: title.strip() or f"Section {i + 1}"
                  for i, (level, title, page) in enumerate(document.get_toc())
                  if level == 1 and 1 <= page <= len(document)}
        if starts:
            starts.setdefault(0, "Introduction")
            ordered = sorted(starts)
            deck["sections"] = [
                {"id": f"section-{i}", "title": starts[start], "start": start,
                 "end": (ordered[i + 1] if i + 1 < len(ordered) else len(document)) - 1}
                for i, start in enumerate(ordered)
            ]


def _pptx(data: bytes, deck: dict[str, Any]) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if sum(info.file_size for info in archive.infolist()) > 256 * 1024 * 1024:
                raise DocumentError("This presentation expands to more than 256 MB. Please split it into smaller files.")
            names = [name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)]
            if not 1 <= len(names) <= MAX_PAGES:
                raise DocumentError("Please use a presentation with 1–300 slides.")
            # Follow presentation relationships rather than slide filenames: reordered
            # PowerPoint slides often keep their original slideN.xml names.
            if "ppt/presentation.xml" in archive.namelist() and "ppt/_rels/presentation.xml.rels" in archive.namelist():
                relationships = ElementTree.fromstring(archive.read("ppt/_rels/presentation.xml.rels"))
                targets = {item.attrib.get("Id"): item.attrib.get("Target", "") for item in relationships}
                presentation = ElementTree.fromstring(archive.read("ppt/presentation.xml"))
                ordered = []
                for node in presentation.iter():
                    if node.tag.rsplit("}", 1)[-1] != "sldId":
                        continue
                    rid = node.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                    target = targets.get(rid, "")
                    path = target.lstrip("/") if target.startswith("/") else str(PurePosixPath("ppt") / target)
                    if path in names:
                        ordered.append(path)
                if not ordered:
                    raise DocumentError("This presentation has no readable slides. Please export it as PDF.")
                names = ordered
            else:
                names.sort(key=lambda name: int(re.search(r"slide(\d+)", name).group(1)))
            for index, name in enumerate(names):
                if archive.getinfo(name).file_size > 4 * 1024 * 1024:
                    raise DocumentError("One slide contains too much text. Please export this presentation as PDF.")
                root = ElementTree.fromstring(archive.read(name))
                paragraphs = ["".join(node.itertext()).strip() for node in root.iter()
                              if node.tag.rsplit("}", 1)[-1] == "p"]
                paragraphs = [text for text in paragraphs if text]
                deck["slides"].append({
                    "id": f"{deck['id']}-{index + 1}", "page": index + 1,
                    "title": paragraphs[0] if paragraphs else f"Slide {index + 1}",
                    "body": "\n\n".join(paragraphs[1:]) if paragraphs else
                    "This slide has no text. Export your presentation as PDF to study its visual content.",
                })
    except DocumentError:
        raise
    except (zipfile.BadZipFile, KeyError, ValueError, ElementTree.ParseError, DefusedXmlException) as exc:
        raise DocumentError("This presentation could not be opened. Please export it as PDF and try again.") from exc


def import_document(filename: str, data: bytes) -> dict[str, Any]:
    filename = (filename or "document").replace("\\", "/").rsplit("/", 1)[-1]
    extension = filename.rsplit(".", 1)[-1].lower()
    if extension not in SUPPORTED:
        raise DocumentError("Choose a PDF, PowerPoint (.pptx), or slide image.")
    if len(data) > MAX_BYTES:
        raise DocumentError("That file is a little large. Please choose a file under 100 MB.")
    if not data:
        raise DocumentError("This file is empty. Please choose another document.")
    deck: dict[str, Any] = {
        "id": str(uuid.uuid4()), "title": filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " "),
        "filename": filename, "slides": [], "sections": [], "decisions": {},
        "revisited": [], "created": int(time.time() * 1000),
        "kind": extension if extension in {"pdf", "pptx"} else "image",
    }
    if extension == "pdf":
        _pdf(data, deck)
    elif extension == "pptx":
        _pptx(data, deck)
    else:
        deck["slides"] = [{"id": f"{deck['id']}-1", "title": deck["title"], "body": "", "page": 1, "image": _image(data)}]
    count = len(deck["slides"])
    if not deck["sections"]:
        deck["sections"] = [
            {"id": f"section-{i // 5}", "title": "Your slides" if count <= 5 else f"Section {i // 5 + 1}",
             "start": i, "end": min(i + 4, count - 1)} for i in range(0, count, 5)
        ]
    return deck
