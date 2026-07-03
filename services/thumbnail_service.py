"""
thumbnail_service.py
--------------------
Renders the first page of a PDF as a PIL Image thumbnail.
Uses pymupdf (fitz) for high-quality, dependency-light rendering on macOS.
"""

from pathlib import Path
from PIL import Image
import fitz  # pymupdf


# Thumbnail dimensions (width in pixels; height is proportional)
THUMBNAIL_WIDTH = 160


class ThumbnailService:
    """
    Renders PDF page thumbnails using pymupdf.

    Each call to render_first_page() opens the PDF, renders page 0
    at a scale that produces THUMBNAIL_WIDTH pixels wide, then closes
    the document.
    """

    def render_first_page(self, pdf_path: Path) -> Image.Image:
        """
        Render the first page of a PDF as a PIL Image.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            PIL Image of the first page scaled to THUMBNAIL_WIDTH wide.

        Raises:
            ValueError: If the PDF has no pages or cannot be opened.
        """
        return self.render_page(pdf_path, page_index=0, max_width=THUMBNAIL_WIDTH)

    def render_page(
        self,
        pdf_path: Path,
        page_index: int = 0,
        max_width: int = THUMBNAIL_WIDTH,
        max_height: int | None = None,
    ) -> Image.Image:
        """
        Render a PDF page as a PIL Image scaled to fit provided bounds.

        Args:
            pdf_path: Path to the PDF file.
            page_index: Zero-based page index to render.
            max_width: Maximum output width in pixels.
            max_height: Optional maximum output height in pixels.

        Returns:
            PIL Image of the rendered page.

        Raises:
            ValueError: If PDF has no pages or page_index is invalid.
        """
        doc = fitz.open(str(pdf_path))
        try:
            if len(doc) == 0:
                raise ValueError(f"PDF has no pages: {pdf_path}")
            if page_index < 0 or page_index >= len(doc):
                raise ValueError(f"Invalid page index {page_index} for: {pdf_path}")

            page = doc[page_index]
            width_scale = max_width / page.rect.width
            if max_height is not None:
                height_scale = max_height / page.rect.height
                zoom = min(width_scale, height_scale)
            else:
                zoom = width_scale
            zoom = max(zoom, 0.05)

            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        finally:
            doc.close()
