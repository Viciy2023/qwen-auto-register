"""Log panel for displaying step progress."""

import customtkinter as ctk


class LogPanel(ctk.CTkTextbox):
    """Text box for clean formatted log output."""

    def append(self, msg: str) -> None:
        """Append a log message."""
        self.insert("end", f"{msg}\n")
        self.see("end")

    def clear(self) -> None:
        """Clear log content."""
        self.delete("1.0", "end")
