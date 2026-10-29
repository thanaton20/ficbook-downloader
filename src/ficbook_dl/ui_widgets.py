"""Flat controls and the colour palette for the desktop window."""

from __future__ import annotations

import sys
import tkinter as tk

# A quiet sage palette: muted ink on pale grey-green, one bookbinding green for actions.
BG = "#eef1ef"
SIDEBAR = "#e4e9e6"
CARD = "#fbfcfb"
INK = "#26332f"
MUTED = "#69756f"
LINE = "#d4dcd8"
ACCENT = "#3f6b60"
ACCENT_DARK = "#33574e"
SOFT = "#f4f7f5"
PANEL = "#f0f3f1"
TINT = "#dfe9e5"
HOVER = "#e7ece9"
DONE = "#e1ece4"
DONE_INK = "#2f5d43"
DANGER = "#a3554a"


def ui_font(size: int = 13, weight: str = "normal") -> tuple:
    family = "Segoe UI" if sys.platform == "win32" else "PT Sans"
    if weight == "bold":
        return (family, size, "bold")
    return (family, size)


def display_font(size: int) -> tuple:
    """Page titles: a book face, since the app is for saving stories."""
    family = "Georgia" if sys.platform == "win32" else "PT Serif"
    return (family, size, "bold")


class SoftButton(tk.Canvas):
    """A flat button. primary is filled, secondary and chips are outlined, ghost is text only."""

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
        check: bool = False,
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
        self.check = check
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
        self.configure(cursor="hand2" if self.enabled and self.kind != "done" else "arrow")
        width = int(self.cget("width"))
        height = int(self.cget("height"))
        fill, ink, outline = self._palette()
        if outline:
            self.create_rectangle(1, 1, width - 1, height - 1, fill=fill, outline=outline, width=1)
        else:
            self.create_rectangle(0, 0, width, height, fill=fill, outline=fill)
        text = self.label
        if self.kind == "done" or (self.check and self.kind == "chip" and self.selected):
            text = f"✓ {text}"
        if self.kind == "nav":
            if self.selected:
                self.create_rectangle(0, 0, 3, height, fill=ACCENT, outline=ACCENT)
            self.create_text(16, height / 2, text=text, fill=ink, font=ui_font(14, "bold"), anchor="w")
        else:
            self.create_text(width / 2, height / 2, text=text, fill=ink, font=ui_font(13, "bold"))

    def _palette(self) -> tuple[str, str, str]:
        if not self.enabled:
            return "#e6eae8", "#8a948f", ""
        if self.kind == "done":
            return DONE, DONE_INK, ""
        if self.kind == "primary":
            return (ACCENT_DARK if self._hover else ACCENT), "#ffffff", ""
        if self.kind == "danger":
            return ("#f6ebe9" if self._hover else CARD), DANGER, "#dcb6b0"
        if self.kind == "ghost":
            return (HOVER if self._hover else self.cget("bg")), ACCENT, ""
        if self.kind == "chip" and self.selected:
            return TINT, ACCENT_DARK, "#b9cec7"
        if self.kind == "nav":
            if self.selected:
                return CARD, INK, ""
            return ("#dae1dd" if self._hover else SIDEBAR), MUTED, ""
        return (HOVER if self._hover else CARD), INK, LINE


class ProgressLine(tk.Canvas):
    """A thin bar that fills as stories finish; blank while idle."""

    def __init__(self, parent, bg: str = CARD) -> None:
        super().__init__(parent, height=4, highlightthickness=0, bd=0, bg=bg)
        self.fraction: float | None = None
        self.bind("<Configure>", lambda _event: self._draw())

    def set(self, fraction: float | None) -> None:
        self.fraction = fraction
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        if self.fraction is None:
            return
        width = self.winfo_width()
        self.create_rectangle(0, 0, width, 4, fill=LINE, outline="")
        self.create_rectangle(0, 0, int(width * self.fraction), 4, fill=ACCENT, outline="")


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
