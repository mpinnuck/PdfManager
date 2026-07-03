"""
merge_view.py
-------------
View for the PDF merge operation.

Displays a two-panel layout:
- Left: vertically scrollable list of PDF thumbnail cards (reorderable).
- Right: first-page PDF preview for the selected document.

The panel split is resizable and the preview expands to fill available space.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from PIL import ImageTk

from viewmodels.merge_viewmodel import MergeViewModel


# Card dimensions
CARD_WIDTH = 130
CARD_THUMB_W = 80
CARD_THUMB_H = 105
CARD_PAD = 8
CARD_TOTAL_H = CARD_THUMB_H + 50  # thumbnail + label area
APP_VERSION = "v1.0.0"


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


class ThumbnailCard(tk.Frame):
    """
    A single card in the merge list displaying one PDF document.

    Attributes:
        index:     Current position in the list (updated on refresh).
        _photo:    Keeps a reference to the PhotoImage to prevent GC.
    """

    def __init__(self, parent: tk.Widget, index: int, doc, on_remove, **kwargs):
        """
        Args:
            parent:    Parent widget.
            index:     Zero-based position of this card.
            doc:       PdfDocument instance.
            on_remove: Callback(index) called when the × button is clicked.
        """
        super().__init__(parent, bd=1, relief=tk.RAISED,
                         bg="#f5f5f5", width=CARD_WIDTH, **kwargs)
        self.index = index
        self._photo: ImageTk.PhotoImage | None = None
        self._build(doc, on_remove)

    def _build(self, doc, on_remove) -> None:
        """Construct internal widgets."""
        self.pack_propagate(False)
        self.configure(height=CARD_TOTAL_H + CARD_PAD * 2)

        # ── Thumbnail image ──────────────────────────────────────────
        if doc.thumbnail:
            img = doc.thumbnail.copy()
            img.thumbnail((CARD_THUMB_W, CARD_THUMB_H))
            self._photo = ImageTk.PhotoImage(img)
            thumb_label = tk.Label(self, image=self._photo, bg="#f5f5f5")
        else:
            thumb_label = tk.Label(self, text="[No preview]",
                                   width=CARD_THUMB_W, height=CARD_THUMB_H,
                                   bg="#cccccc")
        thumb_label.pack(pady=(CARD_PAD, 2))

        # ── Filename ─────────────────────────────────────────────────
        name = doc.name if len(doc.name) <= 26 else doc.name[:23] + "…"
        tk.Label(self, text=name, bg="#f5f5f5",
                 font=("Helvetica", 10), wraplength=CARD_WIDTH - 10).pack()

        # ── Page count ───────────────────────────────────────────────
        tk.Label(self, text=f"{doc.page_count} page{'s' if doc.page_count != 1 else ''}",
                 bg="#f5f5f5", fg="#666666", font=("Helvetica", 9)).pack()

        # ── Remove button ────────────────────────────────────────────
        tk.Button(self, text="✕ Remove", font=("Helvetica", 9),
                  command=lambda: on_remove(self.index),
                  relief=tk.FLAT, bg="#e0e0e0", cursor="hand2").pack(pady=(4, CARD_PAD))

        # ── Drag handle label ─────────────────────────────────────────
        tk.Label(self, text="⠿ drag to reorder", fg="#aaaaaa",
                 bg="#f5f5f5", font=("Helvetica", 8)).pack()


class MergeView(tk.Frame):
    """
    Full merge view: toolbar + scrollable card list.

    Wires drag-reorder behaviour onto the card list and delegates all
    data operations to MergeViewModel.
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
        self._cards: list[ThumbnailCard] = []
        self._selected_index: int | None = None
        self._preview_page_index: int = 0
        self._preview_photo: ImageTk.PhotoImage | None = None
        self._preview_after_id: str | None = None
        self._last_output_path: Path | None = None
        self._output_preview_window: OutputPreviewWindow | None = None

        # Drag state
        self._drag_card: ThumbnailCard | None = None

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
        """Scrollable canvas that holds the card list."""
        container = tk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(container, bg="#ffffff", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL,
                                  command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._card_frame = tk.Frame(self._canvas, bg="#ffffff")
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._card_frame, anchor="nw")

        self._card_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        # Mouse-wheel scrolling
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind("<Button-4>", self._on_mousewheel)
        self._canvas.bind("<Button-5>", self._on_mousewheel)

    def _build_preview_area(self, parent: tk.Widget) -> None:
        """Right-side preview canvas that grows with the window."""
        preview_container = tk.Frame(parent, bg="#222222")
        preview_container.pack(fill=tk.BOTH, expand=True)

        self._preview_canvas = tk.Canvas(preview_container, bg="#262626", highlightthickness=0)
        self._preview_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._preview_canvas.bind("<MouseWheel>", self._on_preview_mousewheel)
        self._preview_canvas.bind("<Button-4>", self._on_preview_mousewheel)
        self._preview_canvas.bind("<Button-5>", self._on_preview_mousewheel)

        self._preview_scrollbar = ttk.Scrollbar(
            preview_container,
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
        """Rebuild the card list from the current viewmodel document list."""
        # Destroy existing cards
        for card in self._cards:
            card.destroy()
        self._cards.clear()

        docs = self._vm.documents
        for i, doc in enumerate(docs):
            card = ThumbnailCard(self._card_frame, index=i,
                                 doc=doc, on_remove=self._on_remove)
            card.pack(fill=tk.X, padx=10, pady=6)
            self._attach_drag(card)
            self._cards.append(card)

        # Empty state label
        if not docs:
            tk.Label(self._card_frame, text="Add PDF files to get started.",
                     fg="#aaaaaa", bg="#ffffff",
                     font=("Helvetica", 13)).pack(pady=40)

        # Status bar
        if docs:
            total = sum(d.page_count for d in docs)
            self._status_var.set(
                f"{len(docs)} file{'s' if len(docs) != 1 else ''} · {total} pages total")
        else:
            self._status_var.set("No files loaded.")

        if self._selected_index is None and docs:
            self._selected_index = 0
            self._preview_page_index = 0
        if self._selected_index is not None and self._selected_index >= len(docs):
            self._selected_index = len(docs) - 1 if docs else None
            self._preview_page_index = 0

        self._refresh_card_styles()
        self._schedule_preview_render()
        self._persist_session_state()

    def _restore_session_state(self) -> None:
        """Restore input files and last output path from saved config."""
        stored_output = self._config.get("session_last_output")
        if isinstance(stored_output, str) and stored_output:
            self._last_output_path = Path(stored_output)

        stored_files = self._config.get("session_input_files", [])
        if isinstance(stored_files, list):
            restore_paths = [
                Path(p) for p in stored_files
                if isinstance(p, str) and Path(p).exists()
            ]
            if restore_paths:
                self._vm.add_files(restore_paths)

    def _persist_session_state(self) -> None:
        """Persist current input list and output path so project can resume."""
        self._config["session_input_files"] = [str(doc.path) for doc in self._vm.documents]
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

    def _on_remove(self, index: int) -> None:
        """Remove a document by index."""
        if self._selected_index is not None:
            if index == self._selected_index:
                self._selected_index = None
                self._preview_page_index = 0
            elif index < self._selected_index:
                self._selected_index -= 1
        self._vm.remove(index)

    def _on_clear(self) -> None:
        """Clear all documents after confirmation."""
        if self._vm.is_empty:
            return
        if messagebox.askyesno("Clear all", "Remove all loaded PDF files?"):
            self._selected_index = None
            self._preview_page_index = 0
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
    # Drag-to-reorder
    # ------------------------------------------------------------------

    def _attach_drag(self, card: ThumbnailCard) -> None:
        """Bind drag events to a card and all its child widgets."""
        for widget in [card] + card.winfo_children():
            widget.bind("<ButtonPress-1>", self._drag_start)
            widget.bind("<B1-Motion>", self._drag_motion)
            widget.bind("<ButtonRelease-1>", self._drag_end)

    def _drag_start(self, event: tk.Event) -> None:
        """Record the card being dragged and select it for preview."""
        widget = event.widget
        # Walk up to find the ThumbnailCard
        card = self._find_card(widget)
        if card is None:
            return
        self._drag_card = card
        if self._selected_index != card.index:
            self._preview_page_index = 0
        self._selected_index = card.index
        self._refresh_card_styles(dragging_index=card.index)
        self._schedule_preview_render()

    def _drag_motion(self, event: tk.Event) -> None:
        """Highlight the insertion target as the card is dragged."""
        if self._drag_card is None:
            return
        y_root = event.y_root
        target = self._get_target_index(y_root)
        self._refresh_card_styles(target_index=target,
                                  dragging_index=self._drag_card.index)

    def _drag_end(self, event: tk.Event) -> None:
        """Complete the drag: move the document to the new position."""
        if self._drag_card is None:
            return
        target = self._get_target_index(event.y_root)
        from_idx = self._drag_card.index
        self._drag_card = None

        if target != from_idx:
            if self._selected_index is not None:
                if self._selected_index == from_idx:
                    self._selected_index = target
                elif from_idx < self._selected_index <= target:
                    self._selected_index -= 1
                elif target <= self._selected_index < from_idx:
                    self._selected_index += 1
            self._vm.move(from_idx, target)  # triggers refresh via callback
            return

        self._refresh_card_styles()
        self._schedule_preview_render()

    def _find_card(self, widget: tk.Widget) -> ThumbnailCard | None:
        """Walk up the widget hierarchy to find the enclosing ThumbnailCard."""
        w = widget
        while w is not None:
            if isinstance(w, ThumbnailCard):
                return w
            try:
                w = w.master
            except AttributeError:
                break
        return None

    def _get_target_index(self, y_root: int) -> int:
        """
        Determine which card index the cursor is hovering over.

        Args:
            y_root: Absolute screen Y coordinate.

        Returns:
            Target zero-based index, clamped to valid range.
        """
        if not self._cards:
            return 0
        for i, card in enumerate(self._cards):
            card_y = card.winfo_rooty()
            card_h = card.winfo_height()
            if y_root < card_y + card_h // 2:
                return i
        return len(self._cards) - 1

    # ------------------------------------------------------------------
    # Canvas scroll helpers
    # ------------------------------------------------------------------

    def _on_frame_configure(self, event: tk.Event) -> None:
        """Update canvas scroll region when card frame resizes."""
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        """Expand card frame to fill canvas width."""
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        """Handle mouse-wheel and trackpad scrolling cross-platform."""
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")
        else:
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ------------------------------------------------------------------
    # Preview helpers
    # ------------------------------------------------------------------

    def _on_preview_configure(self, event: tk.Event) -> None:
        """Redraw preview image when the preview panel size changes."""
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
        if self._selected_index is None:
            return
        page_count = self._vm.documents[self._selected_index].page_count
        if page_count <= 0:
            return

        if args[0] == "scroll":
            self._change_preview_page(int(args[1]))
        elif args[0] == "moveto":
            fraction = float(args[1])
            target = min(max(int(fraction * page_count), 0), page_count - 1)
            if target != self._preview_page_index:
                self._preview_page_index = target
                self._schedule_preview_render()

    def _change_preview_page(self, step: int) -> None:
        """Increment/decrement the selected preview page index by one step."""
        if self._selected_index is None:
            return
        page_count = self._vm.documents[self._selected_index].page_count
        if page_count <= 0:
            return

        new_index = min(max(self._preview_page_index + step, 0), page_count - 1)
        if new_index != self._preview_page_index:
            self._preview_page_index = new_index
            self._schedule_preview_render()

    def _sync_preview_scrollbar(self, page_count: int) -> None:
        """Position preview scrollbar thumb based on current page index."""
        if page_count <= 0:
            self._preview_scrollbar.set(0.0, 1.0)
            return
        first = self._preview_page_index / page_count
        last = (self._preview_page_index + 1) / page_count
        self._preview_scrollbar.set(first, last)

    def _schedule_preview_render(self) -> None:
        """Debounce expensive preview rendering during rapid resize events."""
        if self._preview_after_id is not None:
            self.after_cancel(self._preview_after_id)
        self._preview_after_id = self.after(100, self._render_preview)

    def _render_preview(self) -> None:
        """Render selected document preview to fit the right-side panel."""
        self._preview_after_id = None
        self._preview_canvas.delete("all")

        docs = self._vm.documents
        if not docs or self._selected_index is None:
            self._sync_preview_scrollbar(0)
            self._preview_canvas.create_text(
                self._preview_canvas.winfo_width() // 2,
                self._preview_canvas.winfo_height() // 2,
                text="Select a PDF to preview",
                fill="#bbbbbb",
                font=("Helvetica", 14),
            )
            return

        page_count = docs[self._selected_index].page_count
        if page_count <= 0:
            self._sync_preview_scrollbar(0)
            self._preview_canvas.create_text(
                self._preview_canvas.winfo_width() // 2,
                self._preview_canvas.winfo_height() // 2,
                text="PDF has no pages",
                fill="#bbbbbb",
                font=("Helvetica", 14),
            )
            return

        self._preview_page_index = min(max(self._preview_page_index, 0), page_count - 1)
        self._sync_preview_scrollbar(page_count)

        max_width = max(self._preview_canvas.winfo_width() - 30, 200)
        max_height = max(self._preview_canvas.winfo_height() - 30, 200)

        try:
            image = self._vm.render_preview(
                self._selected_index,
                max_width,
                max_height,
                page_index=self._preview_page_index,
            )
        except Exception as e:
            self._preview_canvas.create_text(
                self._preview_canvas.winfo_width() // 2,
                self._preview_canvas.winfo_height() // 2,
                text=f"Preview failed:\n{e}",
                fill="#ff9f9f",
                font=("Helvetica", 12),
                justify=tk.CENTER,
            )
            return

        if image is None:
            return

        self._preview_photo = ImageTk.PhotoImage(image)
        canvas_w = self._preview_canvas.winfo_width()
        canvas_h = self._preview_canvas.winfo_height()
        self._preview_canvas.create_image(canvas_w // 2, canvas_h // 2,
                                          image=self._preview_photo,
                                          anchor="center")

    def _refresh_card_styles(
        self,
        target_index: int | None = None,
        dragging_index: int | None = None,
    ) -> None:
        """Update card highlight states for selection and drag feedback."""
        for i, card in enumerate(self._cards):
            if i == dragging_index:
                card.configure(bg="#dce8f8", relief=tk.SUNKEN)
            elif target_index is not None and i == target_index:
                card.configure(bg="#e8f4e8", relief=tk.RAISED)
            elif i == self._selected_index:
                card.configure(bg="#eef5ff", relief=tk.SOLID)
            else:
                card.configure(bg="#f5f5f5", relief=tk.RAISED)
