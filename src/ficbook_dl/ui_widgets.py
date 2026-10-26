"""Rounded controls that follow a macOS-style layout."""

from __future__ import annotations

import sys
import tkinter as tk

BG = "#f5f5f7"
SIDEBAR = "#ececef"
CARD = "#ffffff"
INK = "#1d1d1f"
MUTED = "#6e6e73"
LINE = "#d2d2d7"
ACCENT = "#6d28d9"
ACCENT_DARK = "#5b21b6"
SOFT = "#f5f3ff"


def ui_font(size: int = 13, weight: str = "normal") -> tuple:
    family = "Segoe UI" if sys.platform == "win32" else "Helvetica Neue"
    if weight == "bold":
        return (family, size, "bold")
    return (family, size)


def round_rect(canvas: tk.Canvas, box: tuple, radius: int, **kwargs) -> int:
    x1, y1, x2, y2 = box
    radius = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class SoftButton(tk.Canvas):
    """A rounded button. primary is filled; secondary and chips are outlined."""

    def __init__(
        self,
        parent,
        text: str,
        command=None,
        kind: str = "primary",
        width: int = 132,
        height: int = 34,
        canvas_bg: str = CARD,
        selected: bool = False,
    ) -> None:
        super().__init__(
            parent,
            width=width,
            height=height,
            highlightthickness=0,
            bd=0,
            bg=canvas_bg,
            cursor="hand2",
        )
        self.kind = kind
        self.command = command
        self.enabled = True
        self.selected = selected
        self.label = text
        self._hover = False
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self._draw()

    def set_text(self, text: str) -> None:
        self.label = text
        self._draw()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw()

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self._draw()

    def _enter(self, _event) -> None:
        self._hover = True
        self._draw()

    def _leave(self, _event) -> None:
        self._hover = False
        self._draw()

    def _click(self, _event) -> None:
        if not self.enabled:
            return
        if self.kind == "chip":
            self.selected = not self.selected
            self._draw()
        if self.command:
            self.command()

    def _draw(self) -> None:
        self.delete("all")
        width = int(self.cget("width"))
        height = int(self.cget("height"))
        fill, ink, outline = self._palette()
        if outline:
            round_rect(self, (1, 1, width - 1, height - 1), 12, fill=fill, outline=outline, width=1)
        else:
            round_rect(self, (1, 1, width - 1, height - 1), 12, fill=fill, outline=fill)
        if self.kind == "nav":
            self.create_text(16, height / 2, text=self.label, fill=ink, font=ui_font(14, "bold"), anchor="w")
        else:
            self.create_text(width / 2, height / 2, text=self.label, fill=ink, font=ui_font(13, "bold"))

    def _palette(self) -> tuple[str, str, str]:
        if not self.enabled:
            return "#e5e5ea", "#8e8e93", ""
        if self.kind == "primary" or (self.kind == "chip" and self.selected):
            return (ACCENT_DARK if self._hover else ACCENT), "#ffffff", ""
        if self.kind == "nav":
            if self.selected:
                return "#ffffff", ACCENT, ""
            return ("#e4e4e8" if self._hover else SIDEBAR), INK, ""
        return ("#f5f5f7" if self._hover else "#ffffff"), INK, LINE


class ScrolledBody(tk.Frame):
    def __init__(self, parent, bg: str = BG) -> None:
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.bar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.inner.bind("<Configure>", lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.bar.pack(side="right", fill="y")
        self.canvas.bind("<Configure>", self._stretch)
        # Trackpad events land on the row under the fingers, not on this canvas.
        # Listen globally and scroll only while the pointer is over the list.
        self.bind_all("<MouseWheel>", self._wheel)
        self.bind_all("<Button-4>", self._wheel_linux)
        self.bind_all("<Button-5>", self._wheel_linux)

    def _stretch(self, event) -> None:
        self.canvas.itemconfigure(self.window, width=max(event.width, 1))

    def _pointer_is_inside(self) -> bool:
        widget = self.winfo_containing(self.winfo_pointerx(), self.winfo_pointery())
        while widget is not None:
            if widget == self:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _wheel(self, event) -> str | None:
        if not self._pointer_is_inside():
            return None
        delta = getattr(event, "delta", 0) or 0
        if delta == 0:
            return "break"
        if abs(delta) >= 120:
            step = int(-delta / 120)
        else:
            # macOS trackpad: small signed deltas, one gesture sends many of them.
            step = int(-delta) if abs(delta) > 1 else (-1 if delta > 0 else 1)
            step = max(-6, min(6, step))
        if step:
            self.canvas.yview_scroll(step, "units")
        return "break"

    def _wheel_linux(self, event) -> str | None:
        if not self._pointer_is_inside():
            return None
        self.canvas.yview_scroll(-1 if event.num == 4 else 1, "units")
        return "break"
