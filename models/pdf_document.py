"""
pdf_document.py
---------------
Model representing a single PDF file selected for merging.
Holds the file path, page count, and rendered thumbnail image.
"""

from dataclasses import dataclass, field
from pathlib import Path
from PIL import Image


@dataclass
class PdfDocument:
    """
    Represents a single PDF file in the merge list.

    Attributes:
        path:        Absolute path to the PDF file.
        page_count:  Number of pages in the PDF.
        thumbnail:   PIL Image of the first page, or None if not yet rendered.
    """
    path: Path
    page_count: int = 0
    thumbnail: Image.Image | None = field(default=None, repr=False)

    @property
    def name(self) -> str:
        """Return the filename without directory."""
        return self.path.name

    @property
    def folder(self) -> Path:
        """Return the parent directory of this PDF."""
        return self.path.parent
