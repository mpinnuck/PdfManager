"""Model representing a page in a PDF document."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PdfPage:
    """Reference to a page in a source PDF."""

    path: Path
    page_index: int
