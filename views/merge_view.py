"""
merge_view.py
-------------
View for the PDF merge operation.

Displays a two-panel layout:
- Left: selectable, reorderable list of PDF pages.
- Right: preview of the selected page.

The panel split is resizable and the preview expands to fill available space.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from PIL import ImageTk

from models.pdf_page import PdfPage
from viewmodels.merge_viewmodel import MergeViewModel


APP_VERSION = "v2.0.0"

# Page tile dimensions (left-hand reorderable list)
TILE_WIDTH = 120
TILE_THUMB_W = 76
TILE_THUMB_H = 100
TILE_PAD = 6

# Preview zoom (view-only; has no effect on the merged output PDF)
PREVIEW_ZOOM_STEP = 1.6
PREVIEW_MIN_ZOOM = 1.0
PREVIEW_MAX_ZOOM = 6.0
PREVIEW_MAX_RENDER_DIM = 2600


class OutputPreviewWindow(tk.Toplevel):
    """Popup window for previewing the merged output PDF inside the app."""

    def __init__(self, parent: tk.Widget, viewmodel: MergeViewModel, pdf_path: Path):
        super().__init__(parent)
        self._vm = viewmodel
        self._pdf_path = pdf_path
        self._page_index = 0
        self._page_count = 0
        self._photo: ImageTk.PhotoImage | None = None
        self._render_after_id: str | None = None
        self._scrollbar: ttk.Scrollbar | None = None

        self.title(f"Output Preview - {pdf_path.name}")
        self.geometry("900x680")
        self.minsize(520, 420)
        self._center_on_screen()

        try:
            self._page_count = self._vm.get_page_count(self._pdf_path)
        except Exception as e:
            messagebox.showerror("Preview failed", str(e), parent=self)
            self.destroy()
            return

        self._build_ui()
        self._schedule_render()

    def _build_ui(self) -> None:
        controls = tk.Frame(self, bg="#e8e8e8")
        controls.pack(fill=tk.X, side=tk.TOP)

        self._prev_btn = tk.Button(controls, text="◀ Prev", command=self._on_prev,
                                   relief=tk.FLAT, bg="#e8e8e8", padx=10, pady=6)
        self._prev_btn.pack(side=tk.LEFT, padx=(6, 4), pady=4)

        self._next_btn = tk.Button(controls, text="Next ▶", command=self._on_next,
                                   relief=tk.FLAT, bg="#e8e8e8", padx=10, pady=6)
        self._next_btn.pack(side=tk.LEFT, padx=4, pady=4)

        self._page_var = tk.StringVar(value="Page 0 / 0")
        tk.Label(controls, textvariable=self._page_var, bg="#e8e8e8",
                 font=("Helvetica", 11, "bold")).pack(side=tk.LEFT, padx=10)

        tk.Label(controls, text=self._pdf_path.name, bg="#e8e8e8", fg="#555555",
                 anchor="e").pack(side=tk.RIGHT, padx=10)

        content = tk.Frame(self)
        content.pack(fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(content, bg="#262626", highlightthickness=0)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind("<Button-4>", self._on_mousewheel)
        self._canvas.bind("<Button-5>", self._on_mousewheel)

        self._scrollbar = ttk.Scrollbar(content, orient=tk.VERTICAL,
                        command=self._on_scrollbar)
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

    def _center_on_screen(self) -> None:
        """Center this popup window on the current screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _on_prev(self) -> None:
        if self._page_index > 0:
            self._page_index -= 1
            self._schedule_render()

    def _on_next(self) -> None:
        if self._page_index < self._page_count - 1:
            self._page_index += 1
            self._schedule_render()

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self._schedule_render()

    def _on_mousewheel(self, event: tk.Event) -> None:
        if event.num == 4:
            self._change_page(-1)
        elif event.num == 5:
            self._change_page(1)
        elif event.delta > 0:
            self._change_page(-1)
        elif event.delta < 0:
            self._change_page(1)

    def _on_scrollbar(self, *args: str) -> None:
        if self._page_count <= 0:
            return

        if args[0] == "scroll":
            step = int(args[1])
            self._change_page(step)
        elif args[0] == "moveto":
            fraction = float(args[1])
            target = min(max(int(fraction * self._page_count), 0), self._page_count - 1)
            if target != self._page_index:
                self._page_index = target
                self._schedule_render()

    def _change_page(self, step: int) -> None:
        if self._page_count <= 0:
            return
        new_index = min(max(self._page_index + step, 0), self._page_count - 1)
        if new_index != self._page_index:
            self._page_index = new_index
            self._schedule_render()

    def _sync_scrollbar(self) -> None:
        if self._scrollbar is None:
            return
        if self._page_count <= 0:
            self._scrollbar.set(0.0, 1.0)
            return
        first = self._page_index / self._page_count
        last = (self._page_index + 1) / self._page_count
        self._scrollbar.set(first, last)

    def _schedule_render(self) -> None:
        if self._render_after_id is not None:
            self.after_cancel(self._render_after_id)
        self._render_after_id = self.after(100, self._render_page)

    def _render_page(self) -> None:
        self._render_after_id = None
        self._canvas.delete("all")

        if self._page_count <= 0:
            self._canvas.create_text(
                self._canvas.winfo_width() // 2,
                self._canvas.winfo_height() // 2,
                text="PDF has no pages",
                fill="#bbbbbb",
                font=("Helvetica", 14),
            )
            return

        self._page_var.set(f"Page {self._page_index + 1} / {self._page_count}")
        self._prev_btn.configure(state=tk.NORMAL if self._page_index > 0 else tk.DISABLED)
        self._next_btn.configure(
            state=tk.NORMAL if self._page_index < self._page_count - 1 else tk.DISABLED
        )
        self._sync_scrollbar()

        max_width = max(self._canvas.winfo_width() - 30, 200)
        max_height = max(self._canvas.winfo_height() - 30, 200)

        try:
            image = self._vm.render_preview_for_file(
                self._pdf_path,
                page_index=self._page_index,
                max_width=max_width,
                max_height=max_height,
            )
        except Exception as e:
            self._canvas.create_text(
                self._canvas.winfo_width() // 2,
                self._canvas.winfo_height() // 2,
                text=f"Preview failed:\n{e}",
                fill="#ff9f9f",
                font=("Helvetica", 12),
                justify=tk.CENTER,
            )
            return

        self._photo = ImageTk.PhotoImage(image)
        self._canvas.create_image(
            self._canvas.winfo_width() // 2,
            self._canvas.winfo_height() // 2,
            image=self._photo,
            anchor="center",
        )


class PageTile(tk.Frame):
    """
    A single tile in the page list, showing a thumbnail of one page.

    Attributes:
        page:     The PdfPage this tile represents.
        position: Current zero-based index within the merged page order.
    """

    def __init__(self, parent: tk.Widget, page: PdfPage, position: int,
                 photo: ImageTk.PhotoImage | None, **kwargs):
        super().__init__(parent, bd=2, relief=tk.RAISED,
                         bg="#f5f5f5", width=TILE_WIDTH, **kwargs)
        self.page = page
        self.position = position
        self._photo = photo  # keep a reference to prevent garbage collection
        self._build()

    def _build(self) -> None:
        self.pack_propagate(False)
        self.configure(height=TILE_THUMB_H + 46)

        if self._photo is not None:
            thumb_label = tk.Label(self, image=self._photo, bg="#f5f5f5")
        else:
            thumb_label = tk.Label(self, text="[No preview]",
                                   width=TILE_THUMB_W // 7, height=TILE_THUMB_H // 14,
                                   bg="#cccccc")
        thumb_label.pack(pady=(TILE_PAD, 2))

        name = self.page.path.name
        if len(name) > 20:
            name = name[:17] + "…"
        tk.Label(self, text=name, bg="#f5f5f5",
                 font=("Helvetica", 8), wraplength=TILE_WIDTH - 10).pack()

        tk.Label(self, text=f"Page {self.page.page_index + 1}  ·  #{self.position + 1}",
                 bg="#f5f5f5", fg="#666666", font=("Helvetica", 8)).pack()

    def set_style(self, bg: str, relief: str) -> None:
        """Update tile background/relief to reflect selection/drag state."""
        self.configure(bg=bg, relief=relief)
        for child in self.winfo_children():
            try:
                child.configure(bg=bg)
            except tk.TclError:
                pass


class MergeView(tk.Frame):
    """
    Full merge view: toolbar + selectable page list and preview.

    Wires page selection and drag-reorder behaviour to MergeViewModel.
    """

    def __init__(self, parent: tk.Widget, viewmodel: MergeViewModel,
                 config: dict, save_config_fn, **kwargs):
        """
        Args:
            parent:         Parent widget (root window).
            viewmodel:      MergeViewModel instance.
            config:         Loaded config dict (for last_folder).
            save_config_fn: Callable(config) to persist config on save.
        """
        super().__init__(parent, **kwargs)
        self._vm = viewmodel
        self._config = config
        self._save_config = save_config_fn

        self._page_tiles: list[PageTile] = []
        self._thumbnail_cache: dict[tuple[Path, int], ImageTk.PhotoImage] = {}
        self._selected_pages: set[PdfPage] = set()
        self._active_page: PdfPage | None = None
        self._shift_anchor_page: PdfPage | None = None

        self._preview_photo: ImageTk.PhotoImage | None = None
        self._preview_after_id: str | None = None
        self._last_output_path: Path | None = None
        self._output_preview_window: OutputPreviewWindow | None = None

        # Preview zoom/pan state (view-only; does not affect the merged PDF)
        self._preview_zoom = PREVIEW_MIN_ZOOM
        self._preview_pan = (0.5, 0.5)
        self._preview_rendered_page: PdfPage | None = None
        self._preview_render_info: dict[str, int] | None = None
        self._preview_press_pos: tuple[int, int] | None = None
        self._preview_press_pan: tuple[float, float] | None = None
        self._preview_dragging = False

        # Drag state
        self._press_page: PdfPage | None = None
        self._press_mode: str | None = None
        self._press_root: tuple[int, int] | None = None
        self._dragging = False
        self._drag_pages: list[PdfPage] | None = None
        self._drag_target_index: int | None = None
        self._drag_insert_after = False
        self._drop_before_tile: PageTile | None = None
        self._drag_ghost: tk.Toplevel | None = None

        self._vm.set_on_change(self.refresh)
        self._build()
        self._restore_session_state()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self) -> None:
        """Construct toolbar, split content area, and status bar."""
        self._build_toolbar()
        self._build_split_content()
        self._build_status_bar()

    def _build_split_content(self) -> None:
        """Create a resizable left/right panel area."""
        self._panes = tk.PanedWindow(self, orient=tk.HORIZONTAL,
                                     sashrelief=tk.RAISED, sashwidth=8)
        self._panes.pack(fill=tk.BOTH, expand=True)

        self._left_panel = tk.Frame(self._panes, bg="#ffffff")
        self._right_panel = tk.Frame(self._panes, bg="#222222")

        self._panes.add(self._left_panel, minsize=260, width=320)
        self._panes.add(self._right_panel, minsize=320)

        self._build_scroll_area(self._left_panel)
        self._build_preview_area(self._right_panel)

    def _build_toolbar(self) -> None:
        """Top toolbar with Add, Clear, Save As, and output preview buttons."""
        toolbar = tk.Frame(self, bd=1, relief=tk.FLAT, bg="#e8e8e8")
        toolbar.pack(fill=tk.X, side=tk.TOP)

        btn_style = dict(relief=tk.FLAT, bg="#e8e8e8", padx=10, pady=6,
                         font=("Helvetica", 12), cursor="hand2")

        tk.Button(toolbar, text="＋ Add PDFs", command=self._on_add,
                  **btn_style).pack(side=tk.LEFT, padx=(4, 0))
        tk.Button(toolbar, text="✕ Clear All", command=self._on_clear,
                  **btn_style).pack(side=tk.LEFT)
        tk.Button(toolbar, text="🔍 Output Preview", command=self._on_output_preview,
              **btn_style).pack(side=tk.LEFT)
        tk.Button(toolbar, text="💾 Save As…", command=self._on_save,
                  bg="#4a90d9", fg="white", relief=tk.FLAT,
                  padx=12, pady=6, font=("Helvetica", 12, "bold"),
                  cursor="hand2").pack(side=tk.RIGHT, padx=4)

    def _build_scroll_area(self, parent: tk.Widget) -> None:
        """Create the scrollable, thumbnail-based page list."""
        tk.Label(
            parent,
            text="Click to select page(s); drag to reorder",
            anchor=tk.W,
            bg="#ffffff",
            fg="#555555",
            padx=8,
            pady=6,
        ).pack(side=tk.TOP, fill=tk.X)

        self._remove_pdf_button = tk.Button(
            parent,
            text="Remove Source PDF",
            command=self._on_remove_selected_pdf,
            relief=tk.FLAT,
            bg="#e8e8e8",
            padx=8,
            pady=5,
        )
        self._remove_pdf_button.pack(side=tk.BOTTOM, fill=tk.X, padx=6, pady=6)

        container = tk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(container, bg="#ffffff", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL,
                                  command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._tile_frame = tk.Frame(self._canvas, bg="#ffffff")
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._tile_frame, anchor="nw")

        self._tile_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        self._canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind("<Button-4>", self._on_mousewheel)
        self._canvas.bind("<Button-5>", self._on_mousewheel)

        self._empty_page_label = tk.Label(
            container,
            text="Add PDF files to get started.",
            fg="#888888",
            bg="#ffffff",
            font=("Helvetica", 12),
        )
        self._empty_page_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def _build_preview_area(self, parent: tk.Widget) -> None:
        """Right-side preview canvas that grows with the window."""
        preview_container = tk.Frame(parent, bg="#222222")
        preview_container.pack(fill=tk.BOTH, expand=True)

        self._preview_label = tk.Label(
            preview_container,
            text="Select a page to preview",
            anchor=tk.W,
            bg="#222222",
            fg="#dddddd",
            padx=10,
            pady=6,
        )
        self._preview_label.pack(side=tk.TOP, fill=tk.X)

        preview_content = tk.Frame(preview_container, bg="#262626")
        preview_content.pack(fill=tk.BOTH, expand=True)
        self._preview_canvas = tk.Canvas(preview_content, bg="#262626",
                                         highlightthickness=0)
        self._preview_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._preview_canvas.bind("<MouseWheel>", self._on_preview_mousewheel)
        self._preview_canvas.bind("<Button-4>", self._on_preview_mousewheel)
        self._preview_canvas.bind("<Button-5>", self._on_preview_mousewheel)

        # Left-click zooms in (centered on the cursor); click-and-drag pans
        # while zoomed in. Right-click zooms back out. View-only: does not
        # affect the merged output PDF.
        self._preview_canvas.bind("<ButtonPress-1>", self._on_preview_press)
        self._preview_canvas.bind("<B1-Motion>", self._on_preview_drag)
        self._preview_canvas.bind("<ButtonRelease-1>", self._on_preview_release)
        self._preview_canvas.bind("<Button-2>", self._on_preview_zoom_out_click)
        self._preview_canvas.bind("<Button-3>", self._on_preview_zoom_out_click)

        self._preview_scrollbar = ttk.Scrollbar(
            preview_content,
            orient=tk.VERTICAL,
            command=self._on_preview_scrollbar,
        )
        self._preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._preview_canvas.bind("<Configure>", self._on_preview_configure)

    def _build_status_bar(self) -> None:
        """Bottom status bar."""
        self._status_var = tk.StringVar(value="No files loaded.")
        status_bar = tk.Frame(self, bg="#e8e8e8")
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        tk.Label(
            status_bar,
            textvariable=self._status_var,
            anchor=tk.W,
            bg="#e8e8e8",
            padx=6,
            pady=3,
            font=("Helvetica", 10),
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(
            status_bar,
            text=APP_VERSION,
            anchor=tk.E,
            bg="#e8e8e8",
            fg="#666666",
            padx=8,
            pady=3,
            font=("Helvetica", 8),
        ).pack(side=tk.RIGHT)

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Rebuild the page tile list from the current viewmodel page order."""
        pages = self._vm.pages
        valid_keys = {(page.path.resolve(), page.page_index) for page in pages}
        self._thumbnail_cache = {
            key: photo for key, photo in self._thumbnail_cache.items()
            if key in valid_keys
        }

        self._selected_pages.intersection_update(pages)
        if self._active_page not in pages:
            self._active_page = pages[0] if pages else None

        self._rebuild_page_tiles()

        if pages:
            self._empty_page_label.place_forget()
        else:
            self._empty_page_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self._remove_pdf_button.configure(
            state=tk.NORMAL if pages else tk.DISABLED
        )

        # Status bar
        if self._vm.documents:
            self._status_var.set(
                f"{len(self._vm.documents)} file"
                f"{'s' if len(self._vm.documents) != 1 else ''} · "
                f"{len(pages)} pages total")
        else:
            self._status_var.set("No files loaded.")

        self._schedule_preview_render()
        self._persist_session_state()


    def _restore_session_state(self) -> None:
        """Restore input files and last output path from saved config."""
        stored_output = self._config.get("session_last_output")
        if isinstance(stored_output, str) and stored_output:
            self._last_output_path = Path(stored_output)

        stored_page_order = self._config.get("session_page_order", [])
        stored_files = self._config.get("session_input_files", [])
        if isinstance(stored_files, list):
            restore_paths = [
                Path(p) for p in stored_files
                if isinstance(p, str) and Path(p).exists()
            ]
            if restore_paths:
                self._vm.add_files(restore_paths)

        if isinstance(stored_page_order, list):
            restored_pages: list[PdfPage] = []
            for entry in stored_page_order:
                if (
                    not isinstance(entry, dict)
                    or not isinstance(entry.get("path"), str)
                    or type(entry.get("page_index")) is not int
                ):
                    restored_pages = []
                    break
                restored_pages.append(
                    PdfPage(
                        path=Path(entry["path"]).resolve(),
                        page_index=entry["page_index"],
                    )
                )
            if (
                len(restored_pages) == len(self._vm.pages)
                and set(restored_pages) == set(self._vm.pages)
            ):
                self._vm.set_page_order(restored_pages)

    def _persist_session_state(self) -> None:
        """Persist current input list and output path so project can resume."""
        self._config["session_input_files"] = [str(doc.path) for doc in self._vm.documents]
        self._config["session_page_order"] = [
            {"path": str(page.path), "page_index": page.page_index}
            for page in self._vm.pages
        ]
        self._config["session_last_output"] = (
            str(self._last_output_path) if self._last_output_path else None
        )
        self._save_config(self._config)

    # ------------------------------------------------------------------
    # Toolbar actions
    # ------------------------------------------------------------------

    def _on_add(self) -> None:
        """Open file dialog and add selected PDFs."""
        initial = self._config.get("last_folder", str(Path.home()))
        paths = filedialog.askopenfilenames(
            title="Select PDF files",
            initialdir=initial,
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if not paths:
            return
        path_objs = [Path(p) for p in paths]
        # Update last_folder to directory of first selected file
        self._config["last_folder"] = str(path_objs[0].parent)
        self._save_config(self._config)

        errors = self._vm.add_files(path_objs)
        if errors:
            messagebox.showwarning("Some files could not be loaded",
                                   "\n".join(errors))

    def _on_remove_selected_pdf(self) -> None:
        """Remove the source PDF for the currently selected page or pages."""
        if not self._selected_pages:
            messagebox.showinfo("No page selected", "Select a page from the PDF to remove.")
            return

        selected_paths = {page.path.resolve() for page in self._selected_pages}
        if len(selected_paths) != 1:
            messagebox.showinfo(
                "Select pages from one PDF",
                "Select pages from a single PDF to remove that source file.",
            )
            return

        path = next(iter(selected_paths))
        document_index = next(
            (i for i, doc in enumerate(self._vm.documents)
             if doc.path.resolve() == path),
            None,
        )
        if document_index is not None:
            self._vm.remove(document_index)

    def _on_clear(self) -> None:
        """Clear all documents after confirmation."""
        if self._vm.is_empty:
            return
        if messagebox.askyesno("Clear all", "Remove all loaded PDF files?"):
            self._active_page = None
            self._selected_pages.clear()
            self._vm.clear()

    def _on_save(self) -> None:
        """Prompt for save location and merge PDFs."""
        if self._vm.is_empty:
            messagebox.showinfo("No files", "Add at least one PDF file first.")
            return

        initial_dir = str(self._vm.last_folder or
                          self._config.get("last_folder", Path.home()))
        output = filedialog.asksaveasfilename(
            title="Save merged PDF as…",
            initialdir=initial_dir,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not output:
            return

        output_path = Path(output)
        try:
            self._vm.merge(output_path)
            self._last_output_path = output_path
            self._config["last_folder"] = str(output_path.parent)
            self._persist_session_state()
            messagebox.showinfo("Done", f"Saved to:\n{output_path}")
            self._open_output_preview(output_path)
        except Exception as e:
            messagebox.showerror("Merge failed", str(e))

    def _on_output_preview(self) -> None:
        """Open output PDF preview popup for the most recent merged file."""
        if self._last_output_path is None or not self._last_output_path.exists():
            messagebox.showinfo(
                "No output available",
                "Save a merged PDF first, then use Output Preview.",
            )
            return
        self._open_output_preview(self._last_output_path)

    def _open_output_preview(self, output_path: Path) -> None:
        """Create or refresh an in-app popup window to preview output PDF."""
        if self._output_preview_window is not None and self._output_preview_window.winfo_exists():
            self._output_preview_window.destroy()

        self._output_preview_window = OutputPreviewWindow(self, self._vm, output_path)
        if self._output_preview_window.winfo_exists():
            self._output_preview_window.transient(self.winfo_toplevel())
            self._output_preview_window.lift()
            self._output_preview_window.focus_force()

    # ------------------------------------------------------------------
    # Page tiles: build, select, and drag-to-reorder
    # ------------------------------------------------------------------

    def _rebuild_page_tiles(self) -> None:
        """Destroy and recreate page tiles to match the viewmodel order."""
        for tile in self._page_tiles:
            tile.destroy()
        self._page_tiles = []

        for position, page in enumerate(self._vm.pages):
            photo = self._get_thumbnail(page)
            tile = PageTile(self._tile_frame, page=page, position=position, photo=photo)
            tile.pack(fill=tk.X, padx=10, pady=6)
            self._attach_tile_events(tile)
            self._page_tiles.append(tile)

        self._refresh_tile_styles()

    def _get_thumbnail(self, page: PdfPage) -> ImageTk.PhotoImage | None:
        """Return a cached thumbnail for a page, rendering it if needed."""
        key = (page.path.resolve(), page.page_index)
        cached = self._thumbnail_cache.get(key)
        if cached is not None:
            return cached
        try:
            image = self._vm.render_preview_for_file(
                page.path,
                page_index=page.page_index,
                max_width=TILE_THUMB_W,
                max_height=TILE_THUMB_H,
            )
        except Exception:
            return None
        photo = ImageTk.PhotoImage(image)
        self._thumbnail_cache[key] = photo
        return photo

    def _attach_tile_events(self, tile: PageTile) -> None:
        """Bind selection, drag, and context-menu events to a tile and its children."""
        for widget in [tile] + tile.winfo_children():
            widget.bind("<Button-1>", self._on_tile_press)
            widget.bind("<Shift-Button-1>", self._on_tile_shift_press)
            widget.bind("<Control-Button-1>", self._on_tile_toggle_press)
            widget.bind("<Command-Button-1>", self._on_tile_toggle_press)
            widget.bind("<B1-Motion>", self._on_tile_motion)
            widget.bind("<ButtonRelease-1>", self._on_tile_release)
            # Right-click: Button-3 on Windows/Linux, Button-2 on macOS Tk.
            widget.bind("<Button-2>", self._on_tile_right_click)
            widget.bind("<Button-3>", self._on_tile_right_click)

    def _find_tile(self, widget: tk.Widget) -> PageTile | None:
        """Walk up the widget hierarchy to find the enclosing PageTile."""
        w = widget
        while w is not None:
            if isinstance(w, PageTile):
                return w
            try:
                w = w.master
            except AttributeError:
                break
        return None

    def _on_tile_press(self, event: tk.Event) -> None:
        """Plain click: select only this tile unless it's already selected."""
        tile = self._find_tile(event.widget)
        if tile is None:
            return
        self._press_mode = "plain"
        if tile.page not in self._selected_pages:
            self._selected_pages = {tile.page}
            self._refresh_tile_styles()
        self._active_page = tile.page
        self._shift_anchor_page = tile.page
        self._begin_potential_drag(tile, event)
        self._schedule_preview_render()

    def _on_tile_shift_press(self, event: tk.Event) -> None:
        """Shift-click: select the range from the last anchor to this tile."""
        tile = self._find_tile(event.widget)
        if tile is None:
            return
        self._press_mode = "shift"
        pages = self._vm.pages
        anchor = self._shift_anchor_page if self._shift_anchor_page in pages else tile.page
        try:
            lo, hi = sorted((pages.index(anchor), pages.index(tile.page)))
            self._selected_pages = set(pages[lo:hi + 1])
        except ValueError:
            self._selected_pages = {tile.page}
        self._active_page = tile.page
        self._refresh_tile_styles()
        self._begin_potential_drag(tile, event)
        self._schedule_preview_render()

    def _on_tile_toggle_press(self, event: tk.Event) -> None:
        """Command/Ctrl-click: toggle this tile's selection."""
        tile = self._find_tile(event.widget)
        if tile is None:
            return
        self._press_mode = "toggle"
        if tile.page in self._selected_pages:
            self._selected_pages.discard(tile.page)
        else:
            self._selected_pages.add(tile.page)
        self._active_page = tile.page
        self._shift_anchor_page = tile.page
        self._refresh_tile_styles()
        self._begin_potential_drag(tile, event)
        self._schedule_preview_render()

    def _on_tile_right_click(self, event: tk.Event) -> None:
        """Right-click: select this tile (if not already part of the
        selection) and show a context menu to delete the selected page(s)."""
        tile = self._find_tile(event.widget)
        if tile is None:
            return
        if tile.page not in self._selected_pages:
            self._selected_pages = {tile.page}
            self._active_page = tile.page
            self._shift_anchor_page = tile.page
            self._refresh_tile_styles()
            self._schedule_preview_render()
        self._show_page_context_menu(event)

    def _show_page_context_menu(self, event: tk.Event) -> None:
        """Pop up a context menu offering to delete the selected page(s)."""
        count = len(self._selected_pages)
        label = f"Delete {count} Page{'s' if count != 1 else ''}"
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label=label, command=self._on_delete_selected_pages)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _on_delete_selected_pages(self) -> None:
        """Remove the currently selected page(s) from the merge order."""
        if not self._selected_pages:
            return
        pages_to_delete = list(self._selected_pages)
        self._selected_pages.clear()
        if self._active_page in pages_to_delete:
            self._active_page = None
        self._vm.delete_pages(pages_to_delete)

    def _begin_potential_drag(self, tile: PageTile, event: tk.Event) -> None:
        """Record press state so motion past a small threshold starts a drag."""
        self._press_page = tile.page
        self._press_root = (event.x_root, event.y_root)
        self._dragging = False
        self._drag_pages = None
        self._drag_target_index = None
        self._drop_before_tile = None

    def _on_tile_motion(self, event: tk.Event) -> str:
        """Start a drag once the cursor moves past a small threshold, then track it."""
        if self._press_page is None or self._press_root is None:
            return "break"

        if not self._dragging:
            dx = event.x_root - self._press_root[0]
            dy = event.y_root - self._press_root[1]
            if dx * dx + dy * dy < 16:
                return "break"
            self._dragging = True
            if self._press_page in self._selected_pages and len(self._selected_pages) > 1:
                self._drag_pages = [
                    page for page in self._vm.pages if page in self._selected_pages
                ]
            else:
                self._drag_pages = [self._press_page]
                self._selected_pages = {self._press_page}
            self._create_drag_ghost()

        self._move_drag_ghost(event.x_root, event.y_root)
        self._autoscroll_for_drag(event.y_root)
        self._drag_target_index, self._drag_insert_after, self._drop_before_tile = (
            self._compute_drop_target(event.y_root)
        )
        self._refresh_tile_styles()
        return "break"

    def _autoscroll_for_drag(self, y_root: int) -> None:
        """Scroll the page canvas while dragging near its top/bottom edge."""
        top = self._canvas.winfo_rooty()
        bottom = top + self._canvas.winfo_height()
        if y_root - top < 24:
            self._canvas.yview_scroll(-1, "units")
        elif bottom - y_root < 24:
            self._canvas.yview_scroll(1, "units")

    def _compute_drop_target(
        self, y_root: int
    ) -> tuple[int, bool, PageTile | None]:
        """
        Determine where a dragged group would land if dropped at y_root.

        Returns (target_index, insert_after, drop_before_tile). drop_before_tile
        is the tile the group will be inserted before, or None when the drop
        would append the group at the end of the list.
        """
        dragged_pages = set(self._drag_pages or [])
        remaining_tiles = [
            tile for tile in self._page_tiles if tile.page not in dragged_pages
        ]
        for tile in remaining_tiles:
            midpoint = tile.winfo_rooty() + tile.winfo_height() // 2
            if y_root < midpoint:
                return tile.position, False, tile
        if remaining_tiles:
            return remaining_tiles[-1].position, True, None
        return 0, False, None

    def _create_drag_ghost(self) -> None:
        """Create a small floating preview of the dragged page(s) near the cursor."""
        if not self._drag_pages:
            return
        first_page = self._drag_pages[0]
        photo = self._thumbnail_cache.get(
            (first_page.path.resolve(), first_page.page_index)
        )

        ghost = tk.Toplevel(self)
        ghost.overrideredirect(True)
        ghost.attributes("-topmost", True)
        try:
            ghost.attributes("-alpha", 0.85)
        except tk.TclError:
            pass

        frame = tk.Frame(ghost, bd=2, relief=tk.SOLID, bg="#4a90d9")
        frame.pack()
        if photo is not None:
            tk.Label(frame, image=photo, bg="#ffffff").pack(padx=2, pady=2)
        else:
            tk.Label(frame, text=first_page.path.name, bg="#ffffff",
                     width=12, height=4, wraplength=100).pack(padx=2, pady=2)
        if len(self._drag_pages) > 1:
            tk.Label(
                frame,
                text=f"{len(self._drag_pages)} pages",
                bg="#4a90d9",
                fg="white",
                font=("Helvetica", 8, "bold"),
            ).pack(fill=tk.X)

        ghost._ghost_photo = photo  # keep a reference alive for the window's lifetime
        ghost.update_idletasks()
        self._drag_ghost = ghost

    def _move_drag_ghost(self, x_root: int, y_root: int) -> None:
        """Reposition the floating drag preview near the cursor."""
        if self._drag_ghost is not None:
            self._drag_ghost.geometry(f"+{x_root + 16}+{y_root + 16}")

    def _destroy_drag_ghost(self) -> None:
        """Remove the floating drag preview, if one is showing."""
        if self._drag_ghost is not None:
            self._drag_ghost.destroy()
            self._drag_ghost = None

    def _on_tile_release(self, event: tk.Event) -> str:
        """Finish a drag by reordering pages, or finalize a plain-click selection."""
        if self._press_page is None:
            return "break"

        self._destroy_drag_ghost()

        if self._dragging and self._drag_pages and self._drag_target_index is not None:
            reordered = self._vm.reorder_page_group(
                self._vm.pages,
                self._drag_pages,
                self._drag_target_index,
                self._drag_insert_after,
            )
            if reordered != self._vm.pages:
                self._vm.set_page_order(reordered)
            else:
                self._refresh_tile_styles()
        elif self._press_mode == "plain" and len(self._selected_pages) > 1:
            self._selected_pages = {self._press_page}
            self._refresh_tile_styles()

        self._press_page = None
        self._press_mode = None
        self._press_root = None
        self._dragging = False
        self._drag_pages = None
        self._drag_target_index = None
        self._drop_before_tile = None
        return "break"

    def _refresh_tile_styles(self) -> None:
        """Update tile highlighting for selection and drag feedback."""
        dragging_pages = set(self._drag_pages) if self._dragging and self._drag_pages else set()
        for tile in self._page_tiles:
            if tile.page in dragging_pages:
                tile.set_style(bg="#dce8f8", relief=tk.SUNKEN)
            elif self._dragging and self._drop_before_tile is tile:
                tile.set_style(bg="#ffe08a", relief=tk.SOLID)
            elif tile.page in self._selected_pages:
                tile.set_style(bg="#eef5ff", relief=tk.SOLID)
            else:
                tile.set_style(bg="#f5f5f5", relief=tk.RAISED)


    # ------------------------------------------------------------------
    # Canvas scroll helpers
    # ------------------------------------------------------------------

    def _on_frame_configure(self, event: tk.Event) -> None:
        """Update canvas scroll region when the tile frame resizes."""
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        """Expand tile frame to fill canvas width."""
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        """Handle mouse-wheel and trackpad scrolling cross-platform."""
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")
        elif event.delta:
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ------------------------------------------------------------------
    # Preview helpers
    # ------------------------------------------------------------------

    def _on_preview_configure(self, event: tk.Event) -> None:
        """Redraw preview image when the preview panel size changes."""
        if event.width > 1 and event.height > 1:
            self._schedule_preview_render()

    def _on_preview_mousewheel(self, event: tk.Event) -> None:
        """Move preview by exactly one page per wheel tick."""
        if event.num == 4:
            self._change_preview_page(-1)
        elif event.num == 5:
            self._change_preview_page(1)
        elif event.delta > 0:
            self._change_preview_page(-1)
        elif event.delta < 0:
            self._change_preview_page(1)

    def _on_preview_scrollbar(self, *args: str) -> None:
        """Handle scrollbar actions as discrete page navigation."""
        page_count = len(self._vm.pages)
        if not page_count or not args:
            return
        current_index = self._active_page_index()
        if current_index is None:
            return

        if args[0] == "scroll":
            self._change_preview_page(int(args[1]))
        elif args[0] == "moveto":
            fraction = float(args[1])
            target = min(max(int(fraction * page_count), 0), page_count - 1)
            self._select_page_index(target)

    def _change_preview_page(self, step: int) -> None:
        """Move the preview to another page in the merged output order."""
        current_index = self._active_page_index()
        if current_index is None:
            return
        target = min(max(current_index + step, 0), len(self._vm.pages) - 1)
        self._select_page_index(target)

    def _sync_preview_scrollbar(self, page_count: int) -> None:
        """Position preview scrollbar thumb based on the active page."""
        if page_count <= 0:
            self._preview_scrollbar.set(0.0, 1.0)
            return
        page_index = self._active_page_index()
        if page_index is None:
            self._preview_scrollbar.set(0.0, 1.0)
            return
        first = page_index / page_count
        last = (page_index + 1) / page_count
        self._preview_scrollbar.set(first, last)

    def _active_page_index(self) -> int | None:
        if self._active_page is None:
            return None
        try:
            return self._vm.pages.index(self._active_page)
        except ValueError:
            return None

    def _select_page_index(self, index: int) -> None:
        if not 0 <= index < len(self._vm.pages):
            return
        self._active_page = self._vm.pages[index]
        self._selected_pages = {self._active_page}
        self._shift_anchor_page = self._active_page
        self._refresh_tile_styles()
        self._ensure_tile_visible(self._active_page)
        self._schedule_preview_render()

    def _ensure_tile_visible(self, page: PdfPage) -> None:
        """Scroll the page canvas so the given page's tile is visible."""
        tile = next((t for t in self._page_tiles if t.page == page), None)
        if tile is None:
            return
        self._canvas.update_idletasks()
        bbox = self._canvas.bbox("all")
        if not bbox:
            return
        total_height = bbox[3] - bbox[1]
        if total_height <= 0:
            return
        tile_top = tile.winfo_y()
        tile_bottom = tile_top + tile.winfo_height()
        view_top = self._canvas.canvasy(0)
        view_height = self._canvas.winfo_height()
        if tile_top < view_top:
            self._canvas.yview_moveto(tile_top / total_height)
        elif tile_bottom > view_top + view_height:
            self._canvas.yview_moveto((tile_bottom - view_height) / total_height)

    def _schedule_preview_render(self) -> None:
        """Debounce expensive preview rendering during rapid resize events."""
        if self._preview_after_id is not None:
            self.after_cancel(self._preview_after_id)
        self._preview_after_id = self.after(100, self._render_preview)

    def _render_preview(self) -> None:
        """Render the active page from the current merged output order."""
        self._preview_after_id = None
        self._preview_canvas.delete("all")

        page_count = len(self._vm.pages)
        page_index = self._active_page_index()
        if not page_count or page_index is None:
            self._preview_label.configure(text="Select a page to preview")
            self._sync_preview_scrollbar(0)
            self._preview_render_info = None
            self._preview_rendered_page = None
            self._preview_canvas.create_text(
                self._preview_canvas.winfo_width() // 2,
                self._preview_canvas.winfo_height() // 2,
                text="No pages loaded",
                fill="#bbbbbb",
                font=("Helvetica", 14),
            )
            return

        self._sync_preview_scrollbar(page_count)
        page = self._vm.pages[page_index]

        # Reset zoom/pan when the displayed page changes.
        if page != self._preview_rendered_page:
            self._preview_zoom = PREVIEW_MIN_ZOOM
            self._preview_pan = (0.5, 0.5)

        zoom_suffix = (
            f"  ·  {round(self._preview_zoom * 100)}% zoom"
            if self._preview_zoom > PREVIEW_MIN_ZOOM else ""
        )
        self._preview_label.configure(
            text=(
                f"Page {page_index + 1} of {page_count}  ·  "
                f"{page.path.name} — source page {page.page_index + 1}"
                f"{zoom_suffix}"
            )
        )

        fit_width = max(self._preview_canvas.winfo_width() - 30, 200)
        fit_height = max(self._preview_canvas.winfo_height() - 30, 200)
        desired_width = min(int(fit_width * self._preview_zoom), PREVIEW_MAX_RENDER_DIM)
        desired_height = min(int(fit_height * self._preview_zoom), PREVIEW_MAX_RENDER_DIM)

        try:
            full_image = self._vm.render_preview_for_file(
                page.path,
                page_index=page.page_index,
                max_width=desired_width,
                max_height=desired_height,
            )
        except Exception as e:
            self._preview_render_info = None
            self._preview_rendered_page = None
            self._preview_canvas.create_text(
                self._preview_canvas.winfo_width() // 2,
                self._preview_canvas.winfo_height() // 2,
                text=f"Preview failed:\n{e}",
                fill="#ff9f9f",
                font=("Helvetica", 12),
                justify=tk.CENTER,
            )
            return

        if full_image is None:
            return

        self._preview_rendered_page = page
        img_w, img_h = full_image.size
        crop_w = min(fit_width, img_w)
        crop_h = min(fit_height, img_h)

        pan_x, pan_y = self._preview_pan
        center_x = pan_x * img_w
        center_y = pan_y * img_h
        left = int(min(max(center_x - crop_w / 2, 0), max(img_w - crop_w, 0)))
        top = int(min(max(center_y - crop_h / 2, 0), max(img_h - crop_h, 0)))

        if crop_w < img_w or crop_h < img_h:
            visible_image = full_image.crop((left, top, left + crop_w, top + crop_h))
        else:
            visible_image = full_image

        self._preview_photo = ImageTk.PhotoImage(visible_image)
        canvas_w = self._preview_canvas.winfo_width()
        canvas_h = self._preview_canvas.winfo_height()
        draw_x = canvas_w // 2 - crop_w // 2
        draw_y = canvas_h // 2 - crop_h // 2
        self._preview_canvas.create_image(canvas_w // 2, canvas_h // 2,
                                          image=self._preview_photo,
                                          anchor="center")

        self._preview_render_info = {
            "img_w": img_w,
            "img_h": img_h,
            "crop_left": left,
            "crop_top": top,
            "crop_w": crop_w,
            "crop_h": crop_h,
            "draw_x": draw_x,
            "draw_y": draw_y,
        }

    # ------------------------------------------------------------------
    # Preview zoom and pan (view-only; never affects the merged PDF)
    # ------------------------------------------------------------------

    def _on_preview_press(self, event: tk.Event) -> None:
        """Record the press position so a later release can zoom or pan."""
        self._preview_press_pos = (event.x, event.y)
        self._preview_press_pan = self._preview_pan
        self._preview_dragging = False

    def _on_preview_drag(self, event: tk.Event) -> None:
        """Pan the zoomed view by dragging, once past a small threshold."""
        if self._preview_press_pos is None or self._preview_press_pan is None:
            return
        if self._preview_zoom <= PREVIEW_MIN_ZOOM:
            return

        dx = event.x - self._preview_press_pos[0]
        dy = event.y - self._preview_press_pos[1]
        if not self._preview_dragging:
            if dx * dx + dy * dy < 16:
                return
            self._preview_dragging = True

        info = self._preview_render_info
        if not info or not info["img_w"] or not info["img_h"]:
            return

        start_x, start_y = self._preview_press_pan
        new_x = min(max(start_x - dx / info["img_w"], 0.0), 1.0)
        new_y = min(max(start_y - dy / info["img_h"], 0.0), 1.0)
        self._preview_pan = (new_x, new_y)
        self._schedule_preview_render()

    def _on_preview_release(self, event: tk.Event) -> None:
        """Finish a pan drag, or treat a plain click as zoom-in on the cursor."""
        was_dragging = self._preview_dragging
        self._preview_press_pos = None
        self._preview_press_pan = None
        self._preview_dragging = False
        if not was_dragging:
            self._zoom_preview(event.x, event.y, zoom_in=True)

    def _on_preview_zoom_out_click(self, event: tk.Event) -> None:
        """Right-click: zoom back out, centered on the cursor."""
        self._zoom_preview(event.x, event.y, zoom_in=False)

    def _zoom_preview(self, canvas_x: int, canvas_y: int, zoom_in: bool) -> None:
        """Change the preview zoom level, centering the view on the cursor."""
        info = self._preview_render_info
        if info is None or not info["img_w"] or not info["img_h"]:
            return

        local_x = min(max(canvas_x - info["draw_x"], 0), info["crop_w"])
        local_y = min(max(canvas_y - info["draw_y"], 0), info["crop_h"])
        page_x = info["crop_left"] + local_x
        page_y = info["crop_top"] + local_y

        if zoom_in:
            new_zoom = min(self._preview_zoom * PREVIEW_ZOOM_STEP, PREVIEW_MAX_ZOOM)
        else:
            new_zoom = max(self._preview_zoom / PREVIEW_ZOOM_STEP, PREVIEW_MIN_ZOOM)

        if new_zoom <= PREVIEW_MIN_ZOOM:
            self._preview_zoom = PREVIEW_MIN_ZOOM
            self._preview_pan = (0.5, 0.5)
        else:
            self._preview_zoom = new_zoom
            self._preview_pan = (page_x / info["img_w"], page_y / info["img_h"])
        self._schedule_preview_render()
