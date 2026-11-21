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
from models.pdf_page import PdfPage
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
        self.pages: list[PdfPage] = []
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
                self.pages.extend(
                    PdfPage(path=path, page_index=page_index)
                    for page_index in range(page_count)
                )
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
            document = self.documents.pop(index)
            resolved_path = document.path.resolve()
            self.pages = [
                page for page in self.pages
                if page.path.resolve() != resolved_path
            ]
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

        resolved_path = doc.path.resolve()
        moved_pages = [
            page for page in self.pages
            if page.path.resolve() == resolved_path
        ]
        remaining_pages = [
            page for page in self.pages
            if page.path.resolve() != resolved_path
        ]
        insertion_index = len(remaining_pages)
        for next_doc in self.documents[to_index + 1:]:
            next_path = next_doc.path.resolve()
            next_index = next(
                (i for i, page in enumerate(remaining_pages)
                 if page.path.resolve() == next_path),
                None,
            )
            if next_index is not None:
                insertion_index = next_index
                break
        self.pages = (
            remaining_pages[:insertion_index]
            + moved_pages
            + remaining_pages[insertion_index:]
        )
        self._notify()

    def set_page_order(self, pages: list[PdfPage]) -> None:
        """Replace the page order with an exact permutation of loaded pages."""
        if len(pages) != len(self.pages) or set(pages) != set(self.pages):
            raise ValueError("Page order must contain each loaded page exactly once.")
        if pages != self.pages:
            self.pages = list(pages)
            self._notify()

    @staticmethod
    def reorder_page_group(
        pages: list[PdfPage],
        selected_pages: list[PdfPage],
        target_index: int,
        insert_after: bool,
    ) -> list[PdfPage]:
        """Return a page order with a selected group placed around a target page."""
        selected = set(selected_pages)
        if (
            not selected
            or len(selected) != len(selected_pages)
            or not selected.issubset(pages)
            or not 0 <= target_index < len(pages)
        ):
            return list(pages)

        target_page = pages[target_index]
        if target_page in selected:
            return list(pages)

        remaining_pages = [page for page in pages if page not in selected]
        insertion_index = sum(
            page not in selected for page in pages[:target_index]
        )
        if insert_after:
            insertion_index += 1
        return (
            remaining_pages[:insertion_index]
            + selected_pages
            + remaining_pages[insertion_index:]
        )

    def clear(self) -> None:
        """Remove all documents from the list."""
        self.documents.clear()
        self.pages.clear()
        self._notify()

    def delete_pages(self, pages: list[PdfPage]) -> None:
        """
        Remove specific pages from the merged page order.

        A source document is also removed from the document list once none
        of its pages remain in the merge order.

        Args:
            pages: PdfPage entries to delete from the merge order.
        """
        pages_to_delete = set(pages)
        if not pages_to_delete:
            return

        self.pages = [page for page in self.pages if page not in pages_to_delete]

        remaining_paths = {page.path.resolve() for page in self.pages}
        self.documents = [
            doc for doc in self.documents
            if doc.path.resolve() in remaining_paths
        ]
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
        self._pdf_service.merge(self.pages, output_path)

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
