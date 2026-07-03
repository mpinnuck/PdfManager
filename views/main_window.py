"""
main_window.py
--------------
Root Tkinter window for PDF Manager.

Creates the application window, menu bar, and hosts the MergeView.
Restores and saves window geometry via config.
"""

import tkinter as tk
from tkinter import Menu

from config import load_config, save_config
from viewmodels.merge_viewmodel import MergeViewModel
from views.merge_view import MergeView


class MainWindow(tk.Tk):
    """
    Application root window.

    Responsibilities:
        - Window title, geometry, and close handling.
        - Menu bar with File and Help menus.
        - Instantiating MergeViewModel and MergeView.
        - Persisting window geometry on exit.
    """

    def __init__(self) -> None:
        super().__init__()
        self._config = load_config()
        self.title("PDF Manager")
        self.geometry(self._config.get("window_geometry", "860x700"))
        self.minsize(600, 480)
        self._center_on_screen()

        self._viewmodel = MergeViewModel()
        self._build_menu()
        self._build_content()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center_on_screen(self) -> None:
        """Center the window on the current screen using its existing size."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        self.geometry(f"{width}x{height}+{x}+{y}")

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        """Construct the application menu bar."""
        menubar = Menu(self)

        # File menu
        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label="Add PDFs…",
                              command=self._merge_view_add,
                              accelerator="Cmd+O")
        file_menu.add_command(label="Save Merged PDF As…",
                              command=self._merge_view_save,
                              accelerator="Cmd+S")
        file_menu.add_separator()
        file_menu.add_command(label="Clear All",
                              command=self._viewmodel.clear)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self._on_close,
                              accelerator="Cmd+Q")
        menubar.add_cascade(label="File", menu=file_menu)

        # Keyboard shortcuts
        self.bind_all("<Command-o>", lambda e: self._merge_view_add())
        self.bind_all("<Command-s>", lambda e: self._merge_view_save())
        self.bind_all("<Command-q>", lambda e: self._on_close())

        self.config(menu=menubar)

    def _build_content(self) -> None:
        """Instantiate and pack the MergeView."""
        self._merge_view = MergeView(
            self,
            viewmodel=self._viewmodel,
            config=self._config,
            save_config_fn=save_config,
        )
        self._merge_view.pack(fill=tk.BOTH, expand=True)
        self._merge_view.refresh()

    # ------------------------------------------------------------------
    # Menu command proxies
    # ------------------------------------------------------------------

    def _merge_view_add(self) -> None:
        """Delegate Add action to MergeView."""
        self._merge_view._on_add()

    def _merge_view_save(self) -> None:
        """Delegate Save action to MergeView."""
        self._merge_view._on_save()

    # ------------------------------------------------------------------
    # Close
    # ------------------------------------------------------------------

    def _on_close(self) -> None:
        """Persist geometry and destroy window."""
        self._config["window_geometry"] = self.geometry()
        save_config(self._config)
        self.destroy()
