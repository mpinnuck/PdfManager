"""
main.py
-------
Entry point for PDF Manager.

Usage:
    python main.py


"""

import sys
import os

# Ensure project root is on sys.path when run directly
sys.path.insert(0, os.path.dirname(__file__))

from views.main_window import MainWindow


def main() -> None:
    """Instantiate and run the application."""
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
