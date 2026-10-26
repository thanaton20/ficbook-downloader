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
        if self.kind == "done":
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
            self.create_rectangle(1, 1, width - 1, height - 1, fill=fill, outline=outline, width=1)
        else:
            self.create_rectangle(0, 0, width, height, fill=fill, outline=fill)
        if self.kind == "nav":
            self.create_text(16, height / 2, text=self.label, fill=ink, font=ui_font(14, "bold"), anchor="w")
        else:
            self.create_text(width / 2, height / 2, text=self.label, fill=ink, font=ui_font(13, "bold"))

    def _palette(self) -> tuple[str, str, str]:
        if not self.enabled:
            return "#e5e5ea", "#8e8e93", ""
        if self.kind == "done":
            return "#248a3d", "#ffffff", ""
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
        self.inner.bind("<Configure>", self._reflow)
        self.window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.bar.pack(side="right", fill="y")
        self.canvas.bind("<Configure>", self._reflow)
        self._bind_wheel(self.canvas)
        self._bind_wheel(self.inner)

    def sync(self) -> None:
        """Call after adding rows so a trackpad swipe on a row scrolls the list."""
        self._bind_tree(self.inner)
        self._reflow()

    def _bind_tree(self, widget) -> None:
        self._bind_wheel(widget)
        for child in widget.winfo_children():
            self._bind_tree(child)

    def _bind_wheel(self, widget) -> None:
        widget.bind("<MouseWheel>", self._wheel, add="+")
        widget.bind("<TouchpadScroll>", self._touchpad, add="+")
        widget.bind("<Button-4>", self._wheel_linux, add="+")
        widget.bind("<Button-5>", self._wheel_linux, add="+")

    def _reflow(self, _event=None) -> None:
        self.inner.update_idletasks()
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.inner.winfo_reqheight(), 1)
        self.canvas.itemconfigure(self.window, width=width, height=height)
        self.canvas.configure(scrollregion=(0, 0, width, height))

    def _wheel(self, event) -> str:
        delta = int(getattr(event, "delta", 0) or 0)
        if delta:
            factor = -40.0 if sys.platform == "darwin" else -120.0
            step = int(delta / factor) or (-1 if delta > 0 else 1)
            self.canvas.yview_scroll(step, "units")
        return "break"

    def _touchpad(self, event) -> str:
        # macOS sends a two-finger swipe as TouchpadScroll, not MouseWheel.
        try:
            _delta_x, delta_y = self.canvas.tk.call("tk::PreciseScrollDeltas", int(event.delta))
        except tk.TclError:
            return "break"
        delta_y = int(delta_y)
        if delta_y:
            self._scroll_pixels(-delta_y)
        return "break"

    def _scroll_pixels(self, pixels: float) -> None:
        region = self.canvas.cget("scrollregion")
        if not region:
            return
        parts = [float(part) for part in str(region).split()]
        if len(parts) != 4:
            return
        total = parts[3] - parts[1]
        visible = float(self.canvas.winfo_height())
        if total <= visible + 1:
            return
        first = float(self.canvas.yview()[0])
        top = max(0.0, min(total - visible, first * total + pixels))
        self.canvas.yview_moveto(top / total)

    def _wheel_linux(self, event) -> str:
        self.canvas.yview_scroll(-1 if event.num == 4 else 1, "units")
        return "break"
