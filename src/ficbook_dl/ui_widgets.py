"""Flat controls and the colour palette for the desktop window."""

from __future__ import annotations

import sys
import tkinter as tk
import tkinter.font as tkfont

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
    """A vertically scrolling page. With fill=True the content stretches to a tall window."""

    def __init__(self, parent, bg: str = BG, fill: bool = False) -> None:
        super().__init__(parent, bg=bg)
        self.fill = fill
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
        # Text boxes keep their own scrolling.
        if isinstance(widget, tk.Text):
            return
        self._bind_wheel(widget)
        for child in widget.winfo_children():
            self._bind_tree(child)

    def _bind_wheel(self, widget) -> None:
        # sync() runs again after every change; bind each widget only once.
        if getattr(widget, "_page_scroll", False):
            return
        widget._page_scroll = True
        widget.bind("<MouseWheel>", self._wheel, add="+")
        widget.bind("<TouchpadScroll>", self._touchpad, add="+")
        widget.bind("<Button-4>", self._wheel_linux, add="+")
        widget.bind("<Button-5>", self._wheel_linux, add="+")

    def _reflow(self, _event=None) -> None:
        self.inner.update_idletasks()
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.inner.winfo_reqheight(), 1)
        if self.fill:
            height = max(height, self.canvas.winfo_height())
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


# Covers without a picture get the title on one of these. The phone app uses the same tones,
# picked by the same hash, so a story looks the same everywhere.
COVER_TONES = ("#3f6b60", "#4a6378", "#7d6250", "#6b5870", "#5d6e4c", "#4f6d6d")


def cover_tone(seed: str) -> str:
    value = 0
    for char in seed:
        value = (value * 31 + ord(char)) & 0xFFFFFFFF
    return COVER_TONES[value % len(COVER_TONES)]


def clamp_lines(text: str, font: tuple, width: int, lines: int) -> str:
    """Wrap text to `width` pixels and keep at most `lines` lines, ending in an ellipsis."""
    measure = tkfont.Font(font=font).measure
    rows: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if measure(candidate) <= width or not current:
            current = candidate
            continue
        rows.append(current)
        current = word
    if current:
        rows.append(current)
    if len(rows) > lines:
        rows = rows[:lines]
        last = rows[-1]
        while last and measure(last + "…") > width:
            last = last[:-1]
        rows[-1] = last.rstrip() + "…"
    return "\n".join(rows)


class BookCard(tk.Frame):
    """A cover with the title and author under it, like a shelf in a bookshop."""

    def __init__(self, parent, width: int = 120, bg: str = CARD, on_open=None, author_line: bool = True) -> None:
        super().__init__(parent, bg=bg)
        self.cover_width = width
        self.cover_height = round(width * 1.5)
        self.author_line = author_line
        self.canvas = tk.Canvas(
            self,
            width=self.cover_width,
            height=self.cover_height,
            highlightthickness=0,
            bd=0,
            bg=bg,
            cursor="hand2" if on_open else "arrow",
        )
        self.canvas.pack(anchor="w")
        if on_open:
            self.canvas.bind("<Button-1>", lambda _event: on_open())
        self.title = tk.Label(self, bg=bg, fg=INK, font=ui_font(13, "bold"), justify="left", anchor="w")
        self.title.pack(anchor="w", pady=(6, 0))
        self.author = tk.Label(self, bg=bg, fg=MUTED, font=ui_font(12), justify="left", anchor="w")
        if author_line:
            self.author.pack(anchor="w")
        self._state: dict = {}
        self._photo = None

    def show(self, *, title: str, author: str = "", seed: str = "", image=None, state: str = "done", number=None, saved=False) -> None:
        self._state = dict(title=title, author=author, seed=seed, image=image, state=state, number=number, saved=saved)
        # Two title lines always, so buttons and rows line up.
        text = clamp_lines(title, ui_font(13, "bold"), self.cover_width, 2)
        self.title.configure(text=text if "\n" in text else text + "\n")
        self.author.configure(
            text=clamp_lines(author, ui_font(12), self.cover_width, 2 if state == "failed" else 1),
            fg=DANGER if state == "failed" else MUTED,
        )
        self._draw()

    def set_image(self, image) -> None:
        if self._state:
            self._state["image"] = image
            self._draw()

    def _draw(self) -> None:
        state = self._state
        canvas = self.canvas
        canvas.delete("all")
        w, h = self.cover_width, self.cover_height
        waiting = state["state"] in ("waiting", "loading")
        if state["image"] is not None:
            from PIL import ImageOps, ImageTk

            fitted = ImageOps.fit(state["image"].convert("RGB"), (w, h))
            self._photo = ImageTk.PhotoImage(fitted)
            canvas.create_image(0, 0, image=self._photo, anchor="nw")
        elif waiting or state["state"] == "failed":
            canvas.create_rectangle(0, 0, w - 1, h - 1, fill=SOFT, outline=LINE)
            mark = "…" if waiting else "!"
            canvas.create_text(w / 2, h / 2, text=mark, fill=DANGER if mark == "!" else MUTED, font=ui_font(22, "bold"))
        else:
            canvas.create_rectangle(0, 0, w, h, fill=cover_tone(state["seed"]), outline="")
            title = clamp_lines(state["title"], display_font(13), w - 20, 6)
            canvas.create_text(w / 2, h / 2, text=title, fill="#ffffff", font=display_font(13), justify="center")
        canvas.create_rectangle(0, 0, w - 1, h - 1, outline="#c9d2ce")
        if state["number"]:
            label = f"✓ {state['number']}" if state["saved"] else str(state["number"])
            width = max(26, tkfont.Font(font=ui_font(12, "bold")).measure(label) + 12)
            canvas.create_rectangle(6, 6, 6 + width, 32, fill=DONE if state["saved"] else CARD, outline="#c9d2ce")
            canvas.create_text(6 + width / 2, 19, text=label, fill=DONE_INK if state["saved"] else INK, font=ui_font(12, "bold"))


class Shelf(tk.Frame):
    """A row of cards that scrolls sideways with the wheel or a trackpad swipe."""

    def __init__(self, parent, bg: str = CARD, height: int = 260) -> None:
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0, height=height)
        self.bar = tk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(xscrollcommand=self.bar.set)
        self.canvas.pack(fill="x")
        self.bar.pack(fill="x")
        self.inner.bind("<Configure>", lambda _event: self._reflow())

    def sync(self) -> None:
        """Call after adding cards so a swipe over any card scrolls the row."""
        self._bind_tree(self.inner)
        self._bind_scroll(self.canvas)
        self._reflow()

    def _reflow(self) -> None:
        self.inner.update_idletasks()
        self.canvas.configure(scrollregion=(0, 0, self.inner.winfo_reqwidth(), self.inner.winfo_reqheight()))

    def _bind_tree(self, widget) -> None:
        self._bind_scroll(widget)
        for child in widget.winfo_children():
            self._bind_tree(child)

    def _bind_scroll(self, widget) -> None:
        if getattr(widget, "_shelf_scroll", False):
            return
        widget._shelf_scroll = True
        widget.bind("<Shift-MouseWheel>", self._wheel, add="+")
        widget.bind("<TouchpadScroll>", self._touchpad, add="+")

    def _wheel(self, event) -> str:
        delta = int(getattr(event, "delta", 0) or 0)
        if delta:
            factor = -2.0 if sys.platform == "darwin" else -40.0
            self.canvas.xview_scroll(int(delta / factor) or (-1 if delta > 0 else 1), "units")
        return "break"

    def _touchpad(self, event):
        try:
            delta_x, delta_y = self.canvas.tk.call("tk::PreciseScrollDeltas", int(event.delta))
        except tk.TclError:
            return None
        if abs(int(delta_x)) <= abs(int(delta_y)):
            return None  # a vertical swipe: let the page scroll
        self.canvas.xview_scroll(-int(delta_x), "units")
        return "break"


def circle_photo(image, size: int, ring: str = BG):
    """A round avatar as a PhotoImage, with the corners painted in `ring`."""
    from PIL import Image, ImageDraw, ImageOps, ImageTk

    scale = 3
    fitted = ImageOps.fit(image.convert("RGBA"), (size * scale, size * scale))
    background = Image.new("RGBA", fitted.size, CARD)
    background.alpha_composite(fitted)
    mask = Image.new("L", fitted.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, fitted.width - 1, fitted.height - 1), fill=255)
    result = Image.new("RGBA", fitted.size, ring)
    result.paste(background, (0, 0), mask)
    return ImageTk.PhotoImage(result.resize((size, size), Image.Resampling.LANCZOS))
