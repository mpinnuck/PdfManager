import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from models.pdf_document import PdfDocument
from models.pdf_page import PdfPage
from services.pdf_service import PdfService
from viewmodels.merge_viewmodel import MergeViewModel


class PageReorderingTests(unittest.TestCase):
    def test_merge_uses_requested_order_across_source_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first_pdf = root / "first.pdf"
            second_pdf = root / "second.pdf"
            output_pdf = root / "merged.pdf"
            self._write_pdf(first_pdf, [101, 102])
            self._write_pdf(second_pdf, [201])

            PdfService().merge(
                [
                    PdfPage(second_pdf, 0),
                    PdfPage(first_pdf, 1),
                    PdfPage(first_pdf, 0),
                ],
                output_pdf,
            )

            merged = PdfReader(str(output_pdf))
            self.assertEqual(len(merged.pages), 3)
            self.assertEqual(
                [float(page.mediabox.height) for page in merged.pages],
                [201, 102, 101],
            )

    def test_document_move_preserves_internal_page_order(self) -> None:
        viewmodel = MergeViewModel()
        first_pdf = Path("first.pdf")
        second_pdf = Path("second.pdf")
        viewmodel.documents = [
            PdfDocument(first_pdf, page_count=2),
            PdfDocument(second_pdf, page_count=1),
        ]
        viewmodel.pages = [
            PdfPage(first_pdf, 0),
            PdfPage(first_pdf, 1),
            PdfPage(second_pdf, 0),
        ]

        viewmodel.move(1, 0)

        self.assertEqual(
            viewmodel.pages,
            [
                PdfPage(second_pdf, 0),
                PdfPage(first_pdf, 0),
                PdfPage(first_pdf, 1),
            ],
        )

    def test_page_order_must_be_a_permutation(self) -> None:
        viewmodel = MergeViewModel()
        first_pdf = Path("first.pdf")
        viewmodel.pages = [PdfPage(first_pdf, 0), PdfPage(first_pdf, 1)]

        with self.assertRaises(ValueError):
            viewmodel.set_page_order([viewmodel.pages[0], viewmodel.pages[0]])

    def test_page_order_accepts_a_valid_permutation(self) -> None:
        viewmodel = MergeViewModel()
        source = Path("source.pdf")
        viewmodel.pages = [
            PdfPage(source, 0),
            PdfPage(source, 1),
            PdfPage(source, 2),
        ]
        reordered = [viewmodel.pages[2], viewmodel.pages[0], viewmodel.pages[1]]

        viewmodel.set_page_order(reordered)

        self.assertEqual(viewmodel.pages, reordered)

    def test_dragging_multiple_pages_preserves_their_relative_order(self) -> None:
        first_pdf = Path("first.pdf")
        second_pdf = Path("second.pdf")
        pages = [
            PdfPage(first_pdf, 0),
            PdfPage(first_pdf, 1),
            PdfPage(second_pdf, 0),
            PdfPage(second_pdf, 1),
        ]

        reordered = MergeViewModel.reorder_page_group(
            pages,
            [pages[1], pages[3]],
            target_index=2,
            insert_after=True,
        )

        self.assertEqual(
            reordered,
            [pages[0], pages[2], pages[1], pages[3]],
        )

    def test_delete_pages_removes_only_the_given_pages(self) -> None:
        viewmodel = MergeViewModel()
        first_pdf = Path("first.pdf")
        second_pdf = Path("second.pdf")
        viewmodel.documents = [
            PdfDocument(first_pdf, page_count=2),
            PdfDocument(second_pdf, page_count=1),
        ]
        viewmodel.pages = [
            PdfPage(first_pdf, 0),
            PdfPage(first_pdf, 1),
            PdfPage(second_pdf, 0),
        ]

        viewmodel.delete_pages([viewmodel.pages[0]])

        self.assertEqual(
            viewmodel.pages,
            [PdfPage(first_pdf, 1), PdfPage(second_pdf, 0)],
        )
        self.assertEqual(
            [doc.path for doc in viewmodel.documents],
            [first_pdf, second_pdf],
        )

    def test_delete_pages_removes_document_once_all_its_pages_are_gone(self) -> None:
        viewmodel = MergeViewModel()
        first_pdf = Path("first.pdf")
        second_pdf = Path("second.pdf")
        viewmodel.documents = [
            PdfDocument(first_pdf, page_count=1),
            PdfDocument(second_pdf, page_count=1),
        ]
        viewmodel.pages = [
            PdfPage(first_pdf, 0),
            PdfPage(second_pdf, 0),
        ]

        viewmodel.delete_pages([viewmodel.pages[0]])

        self.assertEqual(viewmodel.pages, [PdfPage(second_pdf, 0)])
        self.assertEqual([doc.path for doc in viewmodel.documents], [second_pdf])

    @staticmethod
    def _write_pdf(path: Path, page_heights: list[int]) -> None:
        writer = PdfWriter()
        for height in page_heights:
            writer.add_blank_page(width=100, height=height)
        with path.open("wb") as output_file:
            writer.write(output_file)


if __name__ == "__main__":
    unittest.main()
