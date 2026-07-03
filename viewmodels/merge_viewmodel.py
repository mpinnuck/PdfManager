"""
merge_viewmodel.py
------------------
ViewModel for the PDF merge operation.

Manages the ordered list of PdfDocuments, coordinates thumbnail rendering,
and delegates the merge operation to PdfService.  The view binds to the
observable document list via a callback.
"""

from pathlib import Path
from typing import Callable
from PIL import Image

from models.pdf_document import PdfDocument
from services.pdf_service import PdfService
from services.thumbnail_service import ThumbnailService


class MergeViewModel:
    """
    ViewModel for the merge view.

    The view registers an on_change callback which is called whenever the
    document list changes, so the view can redraw without polling.

    Attributes:
        documents:  Ordered list of PdfDocument instances.
    """

    def __init__(self) -> None:
        self._pdf_service = PdfService()
        self._thumbnail_service = ThumbnailService()
        self.documents: list[PdfDocument] = []
        self._on_change: Callable[[], None] | None = None

    # ------------------------------------------------------------------
    # Callback registration
    # ------------------------------------------------------------------

    def set_on_change(self, callback: Callable[[], None]) -> None:
        """
        Register a callback invoked whenever the document list changes.

        Args:
            callback: Zero-argument callable (typically view.refresh).
        """
        self._on_change = callback

    def _notify(self) -> None:
        """Fire the registered on_change callback if set."""
        if self._on_change:
            self._on_change()

    # ------------------------------------------------------------------
    # Document list management
    # ------------------------------------------------------------------

    def add_files(self, paths: list[Path]) -> list[str]:
        """
        Add PDF files to the document list.

        Skips duplicates (by resolved path).  Renders thumbnails and reads
        page counts for each new file.

        Args:
            paths: List of Path objects pointing to PDF files.

        Returns:
            List of error message strings for any files that could not be
            loaded (empty list on full success).
        """
        existing = {doc.path.resolve() for doc in self.documents}
        errors: list[str] = []

        for path in paths:
            resolved = path.resolve()
            if resolved in existing:
                continue
            try:
                page_count = self._pdf_service.load_page_count(path)
                thumbnail = self._thumbnail_service.render_first_page(path)
                doc = PdfDocument(path=path, page_count=page_count, thumbnail=thumbnail)
                self.documents.append(doc)
                existing.add(resolved)
            except Exception as e:
                errors.append(f"{path.name}: {e}")

        self._notify()
        return errors

    def remove(self, index: int) -> None:
        """
        Remove the document at the given index.

        Args:
            index: Zero-based index into self.documents.
        """
        if 0 <= index < len(self.documents):
            self.documents.pop(index)
            self._notify()

    def move(self, from_index: int, to_index: int) -> None:
        """
        Move a document from one position to another.

        Args:
            from_index: Current zero-based index of the document.
            to_index:   Target zero-based index.
        """
        n = len(self.documents)
        if from_index == to_index:
            return
        if not (0 <= from_index < n and 0 <= to_index < n):
            return
        doc = self.documents.pop(from_index)
        self.documents.insert(to_index, doc)
        self._notify()

    def clear(self) -> None:
        """Remove all documents from the list."""
        self.documents.clear()
        self._notify()

    # ------------------------------------------------------------------
    # Merge
    # ------------------------------------------------------------------

    def merge(self, output_path: Path) -> None:
        """
        Merge all documents in current order to output_path.

        Args:
            output_path: Destination path for the merged PDF.

        Raises:
            ValueError: If the document list is empty.
            Exception:  Propagated from PdfService on read/write failure.
        """
        if not self.documents:
            raise ValueError("No PDF files loaded to merge.")
        self._pdf_service.merge(self.documents, output_path)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def last_folder(self) -> Path | None:
        """Return the folder of the last document in the list, or None."""
        if self.documents:
            return self.documents[-1].folder
        return None

    @property
    def is_empty(self) -> bool:
        """True when no documents are loaded."""
        return len(self.documents) == 0

    def render_preview(
        self,
        index: int,
        max_width: int,
        max_height: int,
        page_index: int = 0,
    ) -> Image.Image | None:
        """
        Render a preview image for a document's first page.

        Args:
            index: Document index in current list.
            max_width: Maximum preview width.
            max_height: Maximum preview height.
            page_index: Zero-based page index to render.

        Returns:
            PIL Image or None if index is out of range.
        """
        if not (0 <= index < len(self.documents)):
            return None
        doc = self.documents[index]
        return self._thumbnail_service.render_page(
            doc.path,
            page_index=page_index,
            max_width=max_width,
            max_height=max_height,
        )

    def get_page_count(self, pdf_path: Path) -> int:
        """Return page count for a specific PDF file path."""
        return self._pdf_service.load_page_count(pdf_path)

    def render_preview_for_file(
        self,
        pdf_path: Path,
        page_index: int,
        max_width: int,
        max_height: int,
    ) -> Image.Image:
        """Render an arbitrary PDF file page for preview usage."""
        return self._thumbnail_service.render_page(
            pdf_path,
            page_index=page_index,
            max_width=max_width,
            max_height=max_height,
        )
