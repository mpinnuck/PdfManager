"""
pdf_service.py
--------------
Handles PDF file operations: loading metadata and merging documents.
Uses pypdf for merge operations.
"""

from pathlib import Path
from pypdf import PdfReader, PdfWriter

from models.pdf_document import PdfDocument


class PdfService:
    """
    Provides PDF file operations used by the application.

    Responsibilities:
        - Reading page counts from PDF files.
        - Merging an ordered list of PdfDocuments into a single output PDF.
    """

    def load_page_count(self, pdf_path: Path) -> int:
        """
        Return the number of pages in a PDF file.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Page count as an integer.

        Raises:
            FileNotFoundError: If the file does not exist.
            Exception: If pypdf cannot read the file.
        """
        reader = PdfReader(str(pdf_path))
        return len(reader.pages)

    def merge(self, documents: list[PdfDocument], output_path: Path) -> None:
        """
        Merge an ordered list of PdfDocuments into a single PDF file.

        Pages from each document are appended in list order.

        Args:
            documents:   Ordered list of PdfDocument instances to merge.
            output_path: Destination path for the merged PDF.

        Raises:
            ValueError: If documents list is empty.
            Exception:  If any source PDF cannot be read or output cannot be written.
        """
        if not documents:
            raise ValueError("No documents provided for merge.")

        writer = PdfWriter()
        for doc in documents:
            reader = PdfReader(str(doc.path))
            for page in reader.pages:
                writer.add_page(page)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            writer.write(f)
