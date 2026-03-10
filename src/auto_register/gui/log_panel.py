"""Log panel for displaying step progress."""

from typing import Callable, Optional

import customtkinter as ctk


class LogPanel(ctk.CTkTextbox):
    """Text box for clean formatted log output."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._theme = "dark"

    def append(self, msg: str, level: str = "info") -> None:
        """Append a log message."""
        self.insert("end", f"{msg}\n")
        self.see("end")

    def clear(self) -> None:
        """Clear log content."""
        self.delete("1.0", "end")
