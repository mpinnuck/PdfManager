"""
pdf_service.py
--------------
Handles PDF file operations: loading metadata and merging selected pages.
Uses pypdf for merge operations.
"""

from pathlib import Path
from pypdf import PdfReader, PdfWriter

from models.pdf_page import PdfPage


class PdfService:
    """
    Provides PDF file operations used by the application.

    Responsibilities:
        - Reading page counts from PDF files.
        - Merging an ordered list of PDF pages into a single output PDF.
    """

    def load_page_count(self, pdf_path: Path) -> int:
        """
        Return the number of pages in a PDF file.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Page count as an integer.
        """
        reader = PdfReader(str(pdf_path))
        return len(reader.pages)

    def merge(self, pages: list[PdfPage], output_path: Path) -> None:
        """
        Merge an ordered list of PDF pages into a single output PDF.

        Args:
            pages:       Ordered page references to merge.
            output_path: Destination path for the merged PDF.

        Raises:
            ValueError: If pages list is empty.
            Exception:  If any source PDF cannot be read or output cannot be written.
        """
        if not pages:
            raise ValueError("No pages provided for merge.")

        writer = PdfWriter()
        readers: dict[Path, PdfReader] = {}
        for page in pages:
            reader = readers.get(page.path)
            if reader is None:
                reader = PdfReader(str(page.path))
                readers[page.path] = reader
            writer.add_page(reader.pages[page.page_index])

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as output_file:
            writer.write(output_file)
