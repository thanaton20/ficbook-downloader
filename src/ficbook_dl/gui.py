"""Desktop window for macOS and Windows."""

from __future__ import annotations

import io
import os
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

from PIL import Image, ImageTk

from ficbook_dl.client import Client
from ficbook_dl.download import FORMATS, download_story, save_story
from ficbook_dl.errors import Cancelled, FicbookError, message
from ficbook_dl.formats.cover import to_jpeg
from ficbook_dl.i18n import preferred_language, save_language, saved_status, t, tn
from ficbook_dl.mac_window import blend_title_bar
from ficbook_dl.parse import canonical_author_works_url, canonical_story_url, parse_author_works, parse_story
from ficbook_dl.ui_widgets import (
    ACCENT,
    BG,
    CARD,
    INK,
    LINE,
    MUTED,
    PANEL,
    SIDEBAR,
    SOFT,
    ProgressLine,
    ScrolledBody,
    SoftButton,
    display_font,
    ui_font,
)

CREATOR_URL = "https://github.com/thanaton20"

# Tk binds Command-V and friends to Latin letters, so on a Russian or Ukrainian
# layout the same physical keys arrive as Cyrillic and do nothing.
CYRILLIC_SHORTCUTS = {
    "cyrillic_ef": "<<SelectAll>>",
    "cyrillic_es": "<<Copy>>",
    "cyrillic_che": "<<Cut>>",
    "cyrillic_em": "<<Paste>>",
    "cyrillic_ya": "<<Undo>>",
}
START_KEYS = "<Command-Return>" if sys.platform == "darwin" else "<Control-Return>"
START_LABEL = "⌘↩" if sys.platform == "darwin" else "Ctrl+Enter"


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.language = preferred_language()
        self.page = "download"
        self.busy = False
        self.output = tk.StringVar(value=_load_save_folder())
        self.delay = tk.StringVar(value="1.5")
        self.format_chips: dict[str, SoftButton] = {}
        self.row_buttons: list[tuple[SoftButton, str]] = []
        self.book_buttons: dict[str, SoftButton] = {}
        self.downloaded_urls: set[str] = set()
        self.library_author_url = ""
        self.nav: dict[str, SoftButton] = {}
        self.lang_chips: dict[str, SoftButton] = {}
        self.labels: list[tuple[tk.Label, str, int, str, bool]] = []
        self.library_idle = True
        self.buttons: list[tuple[SoftButton, str]] = []
        self._build()
        self.apply_language()
        self.show_page("download")
        blend_title_bar(self.root, BG)

    def _build(self) -> None:
        self.root.minsize(880, 640)
        self.root.geometry("1020x720")
        self.root.configure(bg=BG)
        self._build_edit_menu()

        sidebar = tk.Frame(self.root, bg=SIDEBAR, width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        brand = tk.Label(sidebar, text="Ficbook", bg=SIDEBAR, fg=INK, font=display_font(21), anchor="w")
        brand.pack(fill="x", padx=22, pady=(28, 22))

        for key in ("download", "library", "about"):
            button = SoftButton(
                sidebar,
                "",
                command=lambda page=key: self.show_page(page),
                kind="nav",
                width=188,
                height=38,
                canvas_bg=SIDEBAR,
            )
            button.pack(padx=16, pady=4)
            self.nav[key] = button

        tk.Frame(sidebar, bg=SIDEBAR).pack(fill="both", expand=True)
        lang_row = tk.Frame(sidebar, bg=SIDEBAR)
        lang_row.pack(fill="x", padx=16, pady=(0, 22))
        for code in ("en", "ru", "uk"):
            chip = SoftButton(
                lang_row,
                code.upper(),
                command=lambda value=code: self.set_language(value),
                kind="chip",
                width=52,
                height=30,
                canvas_bg=SIDEBAR,
                selected=code == self.language,
            )
            chip.pack(side="left", padx=3)
            self.lang_chips[code] = chip

        self.content = tk.Frame(self.root, bg=BG)
        self.content.pack(side="left", fill="both", expand=True)
        self.pages = {
            "download": self._build_download(self.content),
            "library": self._build_library(self.content),
            "about": self._build_about(self.content),
        }

    def _build_edit_menu(self) -> None:
        # macOS only delivers Command-V when the app has a real Edit menu.
        self.menubar = tk.Menu(self.root)
        self.root.configure(menu=self.menubar)
        apple = tk.Menu(self.menubar, name="apple")
        self.menubar.add_cascade(menu=apple, label="Ficbook")
        self.edit_menu = tk.Menu(self.menubar, name="edit", tearoff=0)
        self.menubar.add_cascade(menu=self.edit_menu, label="Edit")
        for key, virtual in (
            ("menu_undo", "<<Undo>>"),
            ("menu_cut", "<<Cut>>"),
            ("menu_copy", "<<Copy>>"),
            ("menu_paste", "<<Paste>>"),
            ("menu_select_all", "<<SelectAll>>"),
        ):
            self.edit_menu.add_command(label=key, command=lambda name=virtual: self._edit_event(name))
        self.edit_menu.insert_separator(1)
        shortcut = "<Command-KeyPress>" if sys.platform == "darwin" else "<Control-KeyPress>"
        self.root.bind_all(shortcut, self._layout_shortcut)
        self.root.bind_all(START_KEYS, self._start_shortcut)

    def _start_shortcut(self, _event=None) -> str:
        if self.page == "download":
            self._download_links()
        return "break"

    def _layout_shortcut(self, event) -> str | None:
        virtual = CYRILLIC_SHORTCUTS.get(event.keysym.lower())
        if virtual is None:
            return None
        if virtual == "<<Undo>>" and event.state & 0x1:
            virtual = "<<Redo>>"
        try:
            event.widget.event_generate(virtual)
        except (tk.TclError, AttributeError):
            return None
        return "break"

    def _edit_event(self, virtual: str) -> None:
        widget = self.root.focus_get() or self.links
        try:
            widget.event_generate(virtual)
        except tk.TclError:
            return

    def _card(self, parent) -> tk.Frame:
        card = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        return card

    def _label(
        self,
        parent,
        key: str,
        size: int = 13,
        weight: str = "normal",
        fg: str = INK,
        bg: str = CARD,
        serif: bool = False,
    ) -> tk.Label:
        label = tk.Label(parent, bg=bg, fg=fg, anchor="w", justify="left")
        self.labels.append((label, key, size, weight, serif))
        return label

    def _button(
        self,
        parent,
        key: str,
        command,
        kind: str = "primary",
        width: int = 140,
        canvas_bg: str = CARD,
        height: int = 34,
    ) -> SoftButton:
        button = SoftButton(parent, "", command=command, kind=kind, width=width, height=height, canvas_bg=canvas_bg)
        self.buttons.append((button, key))
        return button

    def _rule(self, parent) -> None:
        tk.Frame(parent, bg=LINE, height=1).pack(fill="x", padx=22, pady=(4, 14))

    def _build_download(self, parent) -> tk.Frame:
        page = tk.Frame(parent, bg=BG)
        self.download_title = self._label(page, "nav_download", 26, bg=BG, serif=True)
        self.download_title.pack(anchor="w", padx=28, pady=(26, 14))
        card = self._card(page)
        card.pack(fill="both", expand=True, padx=28, pady=(0, 28))

        head = tk.Frame(card, bg=CARD)
        head.pack(fill="x", padx=22, pady=(18, 8))
        self._label(head, "story_links", 16, "bold").pack(side="left")
        self._label(head, "one_per_line", 13, fg=MUTED).pack(side="left", padx=(10, 0))
        self._button(head, "clear", self._clear_links, "ghost", 100, height=30).pack(side="right")
        self._button(head, "paste", self._paste_button, "secondary", 112, height=30).pack(side="right", padx=(0, 6))

        self.links = tk.Text(
            card,
            height=8,
            wrap="word",
            undo=True,
            font=ui_font(15),
            bg=SOFT,
            fg=INK,
            insertbackground=INK,
            relief="flat",
            highlightthickness=2,
            highlightbackground=LINE,
            highlightcolor=ACCENT,
            padx=12,
            pady=10,
            bd=0,
            spacing1=2,
            spacing3=2,
        )
        self.links.hint_on = False
        self.links.pack(fill="both", expand=True, padx=22, pady=(0, 6))
        self.links.bind("<FocusIn>", lambda _event: self._clear_hint())
        self.links.bind("<FocusOut>", lambda _event: self.root.after(50, self._show_hint))
        self.links.bind("<<Paste>>", self._paste_links)
        self.links.bind("<<Modified>>", self._links_changed)
        self.links.bind(START_KEYS, self._start_shortcut)
        self.link_count = tk.Label(card, bg=CARD, fg=MUTED, font=ui_font(12), anchor="w")
        self.link_count.pack(fill="x", padx=22, pady=(0, 10))
        self._rule(card)

        folder = tk.Frame(card, bg=CARD)
        folder.pack(fill="x", padx=22, pady=(0, 12))
        self._label(folder, "save_to", 13, "bold").pack(anchor="w")
        row = tk.Frame(folder, bg=CARD)
        row.pack(fill="x", pady=(6, 0))
        self.folder_entry = tk.Entry(
            row,
            textvariable=self.output,
            font=ui_font(13),
            bg=SOFT,
            fg=INK,
            insertbackground=INK,
            relief="flat",
            highlightthickness=1,
            highlightbackground=LINE,
            highlightcolor=ACCENT,
        )
        self.folder_entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 10))
        self.browse_button = self._button(row, "browse", self._choose_folder, "secondary", 112)
        self.browse_button.pack(side="left")
        self._button(row, "open_folder", self._open_folder, "ghost", 136).pack(side="left", padx=(6, 0))

        options = tk.Frame(card, bg=CARD)
        options.pack(fill="x", padx=22, pady=(4, 8))
        self._label(options, "formats", 13, "bold").pack(side="left", padx=(0, 10))
        for fmt in FORMATS:
            chip = SoftButton(
                options,
                fmt.upper(),
                command=lambda: None,
                kind="chip",
                width=84,
                height=30,
                selected=True,
                check=True,
            )
            chip.pack(side="left", padx=4)
            self.format_chips[fmt] = chip
        tk.Spinbox(
            options,
            from_=0,
            to=30,
            increment=0.5,
            textvariable=self.delay,
            width=5,
            font=ui_font(13),
            fg=INK,
            bg=SOFT,
            buttonbackground=CARD,
            relief="flat",
            highlightthickness=1,
            highlightbackground=LINE,
            highlightcolor=ACCENT,
        ).pack(side="right")
        self._label(options, "pause", 13, fg=MUTED).pack(side="right", padx=(16, 6))
        self._rule(card)

        actions = tk.Frame(card, bg=CARD)
        actions.pack(fill="x", padx=22, pady=(0, 10))
        self.download_button = self._button(actions, "download", self._download_links, "primary", 180, height=40)
        self.download_button.pack(side="left")
        self.status = tk.Label(actions, bg=CARD, fg=MUTED, font=ui_font(13), anchor="w")
        self.status.pack(side="left", padx=14)
        self.shortcut_hint = tk.Label(actions, bg=CARD, fg=MUTED, font=ui_font(12))
        self.shortcut_hint.pack(side="right")
        self.progress = ProgressLine(card)
        self.progress.pack(fill="x", padx=22, pady=(0, 10))

        self.log = tk.Text(
            card,
            height=6,
            wrap="word",
            state="disabled",
            font=ui_font(12),
            bg=PANEL,
            fg=MUTED,
            relief="flat",
            highlightthickness=0,
            padx=10,
            pady=8,
            bd=0,
        )
        self.log.pack(fill="x", padx=22, pady=(0, 18))
        return page

    def _build_library(self, parent) -> tk.Frame:
        page = tk.Frame(parent, bg=BG)
        self._label(page, "nav_library", 26, bg=BG, serif=True).pack(anchor="w", padx=28, pady=(26, 6))
        self._label(page, "library_hint", 14, fg=MUTED, bg=BG).pack(anchor="w", padx=28, pady=(0, 12))

        bar = self._card(page)
        bar.pack(fill="x", padx=28)
        inner = tk.Frame(bar, bg=CARD)
        inner.pack(fill="x", padx=16, pady=14)
        self.author_entry = tk.Entry(
            inner,
            font=ui_font(15),
            bg=SOFT,
            fg=INK,
            insertbackground=INK,
            relief="flat",
            highlightthickness=2,
            highlightbackground=LINE,
            highlightcolor=ACCENT,
        )
        self.author_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 12))
        self.author_entry.bind("<Return>", lambda _event: self._load_author())
        self.show_books_button = self._button(inner, "show_books", self._load_author, "primary", 170)
        self.show_books_button.pack(side="left")
        formats = tk.Frame(bar, bg=CARD)
        formats.pack(fill="x", padx=16, pady=(0, 14))
        self._label(formats, "formats", 13, "bold").pack(side="left", padx=(0, 10))
        self.library_format_chips: dict[str, SoftButton] = {}
        for fmt in FORMATS:
            chip = SoftButton(formats, fmt.upper(), command=lambda: None, kind="chip", width=84, height=30, selected=True, check=True)
            chip.pack(side="left", padx=4)
            self.library_format_chips[fmt] = chip

        self.library_status = tk.Label(page, bg=BG, fg=MUTED, font=ui_font(13), anchor="w")
        self.library_status.pack(anchor="w", padx=28, pady=(10, 6))
        self.library_scroll = ScrolledBody(page, BG)
        self.library_scroll.pack(fill="both", expand=True, padx=28, pady=(0, 24))
        return page

    def _build_about(self, parent) -> tk.Frame:
        page = tk.Frame(parent, bg=BG)
        self._label(page, "nav_about", 26, bg=BG, serif=True).pack(anchor="w", padx=28, pady=(26, 14))
        card = self._card(page)
        card.pack(fill="x", padx=28)
        body = tk.Frame(card, bg=CARD)
        body.pack(fill="x", padx=28, pady=28)
        mark = tk.Canvas(body, width=72, height=72, bg=CARD, highlightthickness=0, bd=0)
        mark.pack(anchor="w")
        mark.create_oval(0, 0, 72, 72, fill=ACCENT, outline=ACCENT)
        mark.create_text(36, 36, text="YH", fill="#ffffff", font=ui_font(22, "bold"))
        self._label(body, "creator_name", 22, serif=True).pack(anchor="w", pady=(16, 2))
        self._label(body, "about_role", 14, fg=MUTED).pack(anchor="w")
        self._label(body, "about_body", 14).pack(anchor="w", pady=(14, 16))
        self._button(body, "open_github", lambda: webbrowser.open(CREATOR_URL), "primary", 160).pack(anchor="w")
        link = tk.Label(body, text=CREATOR_URL, bg=CARD, fg=ACCENT, font=ui_font(13), cursor="hand2")
        link.pack(anchor="w", pady=(10, 0))
        link.bind("<Button-1>", lambda _event: webbrowser.open(CREATOR_URL))
        return page

    def show_page(self, name: str) -> None:
        self.page = name
        for page in self.pages.values():
            page.pack_forget()
        self.pages[name].pack(fill="both", expand=True)
        for key, button in self.nav.items():
            button.set_selected(key == name)
        if name == "download":
            self._show_hint()

    def set_language(self, code: str) -> None:
        self.language = code
        save_language(code)
        for lang, chip in self.lang_chips.items():
            chip.set_selected(lang == code)
        self.apply_language()

    def apply_language(self) -> None:
        self.root.title(t(self.language, "window_title"))
        self.edit_menu.entryconfigure(0, label=t(self.language, "menu_undo"))
        self.edit_menu.entryconfigure(2, label=t(self.language, "menu_cut"))
        self.edit_menu.entryconfigure(3, label=t(self.language, "menu_copy"))
        self.edit_menu.entryconfigure(4, label=t(self.language, "menu_paste"))
        self.edit_menu.entryconfigure(5, label=t(self.language, "menu_select_all"))
        self.menubar.entryconfigure(1, label=t(self.language, "menu_edit"))
        for label, key, size, weight, serif in self.labels:
            label.configure(text=t(self.language, key), font=display_font(size) if serif else ui_font(size, weight))
        for button, key in [*self.buttons, *self.row_buttons]:
            state = getattr(button, "book_state", None)
            if state == "downloaded":
                button.kind = "done"
            elif state == "saving":
                button.kind = "primary"
                button.set_enabled(False)
            button.set_text(t(self.language, state or key))
        for key, button in self.nav.items():
            button.set_text(t(self.language, f"nav_{key}"))
        if not self.busy:
            self.status.configure(text=t(self.language, "status_idle"))
            self.download_button.set_text(t(self.language, "download"))
        else:
            self.download_button.set_text(t(self.language, "stop"))
        self.shortcut_hint.configure(text=t(self.language, "shortcut_hint", keys=START_LABEL))
        if self.library_idle:
            self.library_status.configure(text=t(self.language, "library_empty"))
        self.links.ui_language = self.language
        if self.links.hint_on:
            self.links.delete("1.0", "end")
            self.links.hint_on = False
        self._show_hint()
        self._update_link_count()
        if not self.author_entry.get().strip():
            self.author_entry.delete(0, "end")
        self.author_entry.configure(bg=SOFT)

    def _show_hint(self) -> None:
        if self.links.focus_get() == self.links:
            return
        if self.links.get("1.0", "end").strip():
            return
        self.links.hint_on = True
        self.links.insert("1.0", t(self.language, "hint"))
        self.links.configure(fg=MUTED)

    def _clear_hint(self) -> None:
        if not self.links.hint_on:
            return
        self.links.delete("1.0", "end")
        self.links.configure(fg=INK)
        self.links.hint_on = False

    def _paste_links(self, _event=None) -> str:
        self._clear_hint()
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            return "break"
        try:
            self.links.delete("sel.first", "sel.last")
        except tk.TclError:
            pass
        self.links.insert("insert", text)
        self.links.configure(fg=INK)
        self.links.hint_on = False
        return "break"

    def _paste_button(self) -> None:
        # Each press adds the clipboard on its own line, so links can be collected one by one.
        self.links.focus_set()
        self._clear_hint()
        self.links.mark_set("insert", "end-1c")
        current = self.links.get("1.0", "end-1c")
        if current and not current.endswith("\n"):
            self.links.insert("insert", "\n")
        self._paste_links()
        self.links.see("insert")

    def _clear_links(self) -> None:
        self.links.delete("1.0", "end")
        self.links.configure(fg=INK)
        self.links.hint_on = False
        self.links.focus_set()

    def _links_changed(self, _event=None) -> None:
        self.links.edit_modified(False)
        self._update_link_count()

    def _update_link_count(self) -> None:
        count = len(self._link_lines())
        self.link_count.configure(text=tn(self.language, "links_count", count) if count else "")

    def _open_folder(self) -> None:
        folder = Path(self.output.get()).expanduser()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showinfo(t(self.language, "window_title"), str(exc), parent=self.root)
            return
        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(folder)])
        else:
            subprocess.Popen(["xdg-open", str(folder)])

    def _link_lines(self) -> list[str]:
        if self.links.hint_on:
            return []
        return [line.strip() for line in self.links.get("1.0", "end").splitlines() if line.strip()]

    def _choose_folder(self) -> None:
        chosen = filedialog.askdirectory(parent=self.root, initialdir=self.output.get() or str(Path.home()))
        if chosen:
            self.output.set(chosen)
            _save_save_folder(chosen)

    def _selected_formats(self) -> list[str]:
        return [fmt for fmt, chip in self.format_chips.items() if chip.selected]

    def _library_formats(self) -> list[str]:
        return [fmt for fmt, chip in self.library_format_chips.items() if chip.selected]

    def _pause(self) -> float:
        return float(self.delay.get().replace(",", "."))

    def _download_links(self) -> None:
        if self.busy:
            return
        urls = self._link_lines()
        if not urls:
            messagebox.showinfo(t(self.language, "window_title"), t(self.language, "need_link"), parent=self.root)
            return
        self._start_download(urls)

    def _start_download(self, urls: list[str], formats: list[str] | None = None) -> None:
        if self.busy:
            return
        if formats is None:
            formats = self._selected_formats()
        if not formats:
            messagebox.showinfo(t(self.language, "window_title"), t(self.language, "need_format"), parent=self.root)
            return
        try:
            pause = self._pause()
        except ValueError:
            messagebox.showinfo(t(self.language, "window_title"), t(self.language, "pause_number"), parent=self.root)
            return
        if pause < 0:
            messagebox.showinfo(t(self.language, "window_title"), t(self.language, "pause_negative"), parent=self.root)
            return
        self.busy = True
        self.stop_flag = threading.Event()
        self.download_button.kind = "danger"
        self.download_button.set_text(t(self.language, "stop"))
        self.download_button.command = self.stop_flag.set
        self.status.configure(text=t(self.language, "downloading"))
        self.progress.set(0.0)
        self._log(t(self.language, "saving_to", formats=", ".join(item.upper() for item in formats), folder=self.output.get()))
        threading.Thread(
            target=self._download_worker,
            args=(urls, formats, pause, self.language),
            daemon=True,
        ).start()

    def _download_worker(self, urls, formats, pause, language) -> None:
        client = Client(delay=pause)
        saved = 0
        failed = 0
        for index, url in enumerate(urls, 1):
            self.root.after(0, self._show_progress, index, len(urls), language)
            if self.stop_flag.is_set():
                self.root.after(0, self._log, t(language, "stopped"))
                break
            try:
                story_url = canonical_story_url(url)
            except FicbookError as exc:
                failed += 1
                self.root.after(0, self._log, t(language, "error_line", message=message(exc, language)))
                continue
            self.root.after(0, lambda current=story_url: self._set_book_state(current, "saving"))
            self.root.after(0, self._log, url)
            try:
                story = download_story(
                    client,
                    url,
                    on_chapter=lambda index, total, title: self.root.after(
                        0, self._log, f"  {index}/{total} {title}"
                    ),
                    stop=self.stop_flag.is_set,
                    language=language,
                )
                paths = save_story(story, Path(self.output.get()), formats, language)
            except Cancelled:
                self.root.after(0, lambda current=story_url: self._set_book_state(current, "download"))
                self.root.after(0, self._log, t(language, "stopped"))
                break
            except FicbookError as exc:
                failed += 1
                self.root.after(0, lambda current=story_url: self._set_book_state(current, "download"))
                self.root.after(0, self._log, t(language, "error_line", message=message(exc, language)))
                continue
            except Exception as exc:
                failed += 1
                self.root.after(0, lambda current=story_url: self._set_book_state(current, "download"))
                self.root.after(0, self._log, t(language, "error_line", message=str(exc)))
                continue
            saved += 1
            self.root.after(0, lambda current=story_url: self._remember_download(current))
            for path in paths:
                self.root.after(0, self._log, t(language, "saved_path", path=path))
        summary = saved_status(language, saved, failed)

        def finish() -> None:
            self.busy = False
            self.progress.set(None)
            self.download_button.kind = "primary"
            self.download_button.command = self._download_links
            self.download_button.set_text(t(self.language, "download"))
            self.status.configure(text=summary)

        self.root.after(0, finish)

    def _show_progress(self, index: int, total: int, language: str) -> None:
        if not self.busy:
            return
        self.status.configure(text=t(language, "downloading_n", i=index, n=total))
        self.progress.set((index - 1) / total)

    def _load_author(self) -> None:
        if self.busy:
            return
        raw = self.author_entry.get().strip()
        if not raw or raw == t(self.language, "library_hint"):
            messagebox.showinfo(t(self.language, "window_title"), t(self.language, "need_author"), parent=self.root)
            return
        try:
            url = canonical_author_works_url(raw)
            pause = self._pause()
        except FicbookError as exc:
            messagebox.showinfo(t(self.language, "window_title"), message(exc, self.language), parent=self.root)
            return
        except ValueError:
            messagebox.showinfo(t(self.language, "window_title"), t(self.language, "pause_number"), parent=self.root)
            return
        self.library_idle = False
        self.library_status.configure(text=t(self.language, "loading"))
        self.show_books_button.set_enabled(False)
        threading.Thread(target=self._author_worker, args=(url, pause, self.language), daemon=True).start()

    def _author_worker(self, url: str, pause: float, language: str) -> None:
        try:
            client = Client(delay=pause)
            name = ""
            works = []
            seen: set[str] = set()
            page = url
            for _ in range(40):
                author_name, found, nxt = parse_author_works(client.get(page), page)
                name = name or author_name
                for work in found:
                    if work.story_id not in seen:
                        seen.add(work.story_id)
                        works.append(work)
                if not nxt:
                    break
                page = nxt
        except Exception as exc:
            text = message(exc, language) if isinstance(exc, FicbookError) else str(exc)
            self.root.after(0, lambda: self._author_failed(text))
            return
        self.root.after(0, lambda: self._show_works(name, works, url))

    def _author_failed(self, text: str) -> None:
        self.show_books_button.set_enabled(True)
        self.library_status.configure(text=text)

    def _show_works(self, name: str, works, author_url: str) -> None:
        if author_url != self.library_author_url:
            self.downloaded_urls.clear()
            self.library_author_url = author_url
        self.show_books_button.set_enabled(True)
        self.library_status.configure(text=f"{name} · {t(self.language, 'books_count', n=len(works))}" if name else t(self.language, "books_count", n=len(works)))
        self.row_buttons.clear()
        self.book_buttons.clear()
        for child in self.library_scroll.inner.winfo_children():
            child.destroy()
        for work in works:
            row = tk.Frame(self.library_scroll.inner, bg=CARD, highlightthickness=1, highlightbackground=LINE)
            row.pack(fill="x", pady=6)
            title = tk.Label(row, text=work.title, bg=CARD, fg=INK, font=ui_font(15, "bold"), anchor="w", wraplength=520, justify="left")
            title.pack(side="left", fill="x", expand=True, padx=16, pady=14)
            preview = SoftButton(row, t(self.language, "preview"), command=lambda item=work: self._preview(item), kind="secondary", width=150, height=34)
            already = work.url in self.downloaded_urls
            download = SoftButton(
                row,
                t(self.language, "downloaded" if already else "download"),
                command=None if already else (lambda item=work: self._start_download([item.url], self._library_formats())),
                kind="done" if already else "primary",
                width=168,
                height=34,
            )
            download.book_state = "downloaded" if already else "download"
            download.pack(side="right", padx=(0, 14), pady=12)
            preview.pack(side="right", padx=(0, 8), pady=12)
            self.book_buttons[work.url] = download
            self.row_buttons.append((preview, "preview"))
            self.row_buttons.append((download, "download"))
        self.library_scroll.sync()

    def _set_book_state(self, url: str, state: str) -> None:
        button = self.book_buttons.get(url)
        if button is None or button.book_state == "downloaded" and state != "downloaded":
            return
        button.book_state = state
        if state == "downloaded":
            button.kind = "done"
            button.command = None
            button.set_enabled(True)
            button.set_text(t(self.language, "downloaded"))
        elif state == "saving":
            button.kind = "primary"
            button.command = None
            button.set_enabled(False)
            button.set_text(t(self.language, "saving"))
        else:
            button.kind = "primary"
            button.command = lambda current=url: self._start_download([current], self._library_formats())
            button.set_enabled(True)
            button.set_text(t(self.language, "download"))

    def _remember_download(self, url: str) -> None:
        self.downloaded_urls.add(url)
        self._set_book_state(url, "downloaded")

    def _preview(self, work) -> None:
        self.library_status.configure(text=t(self.language, "loading"))

        def job() -> None:
            try:
                client = Client(delay=0)
                story = parse_story(client.get(work.url), work.url, self.language)
                cover = to_jpeg(client.get_bytes(story.cover_url)) if story.cover_url else None
            except Exception as exc:
                text = message(exc, self.language) if isinstance(exc, FicbookError) else str(exc)
                self.root.after(0, lambda: self.library_status.configure(text=text))
                return
            self.root.after(0, lambda: self._open_preview(story, cover))

        threading.Thread(target=job, daemon=True).start()

    def _open_preview(self, story, cover: bytes | None) -> None:
        self.library_status.configure(text="")
        window = tk.Toplevel(self.root)
        window.title(t(self.language, "preview"))
        window.configure(bg=CARD)
        window.transient(self.root)
        window.resizable(False, False)
        body = tk.Frame(window, bg=CARD)
        body.pack(padx=28, pady=24)
        if cover:
            image = Image.open(io.BytesIO(cover))
            image.thumbnail((240, 340))
            photo = ImageTk.PhotoImage(image)
            picture = tk.Label(body, image=photo, bg=CARD)
            picture.image = photo
            picture.pack()
        else:
            blank = tk.Label(body, text=t(self.language, "no_cover"), bg=SOFT, fg=MUTED, font=ui_font(13), width=24, height=10)
            blank.pack()
        tk.Label(body, text=story.title, bg=CARD, fg=INK, font=ui_font(20, "bold"), wraplength=360, justify="center").pack(pady=(16, 6))
        tk.Label(body, text=f"{t(self.language, 'author')}: {story.author}", bg=CARD, fg=INK, font=ui_font(14)).pack()
        series = story.series_name or t(self.language, "no_series")
        if story.series_index and story.series_name:
            series = f"{story.series_name} ({story.series_index})"
        tk.Label(body, text=f"{t(self.language, 'series')}: {series}", bg=CARD, fg=MUTED, font=ui_font(14), wraplength=360).pack(pady=(4, 16))
        SoftButton(body, t(self.language, "close"), command=window.destroy, kind="secondary", width=140).pack()
        window.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - window.winfo_width()) // 2
        y = self.root.winfo_rooty() + 40
        window.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        blend_title_bar(window, CARD)

    def _log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")


def _config_dir() -> Path:
    return Path.home() / ".config" / "ficbook-downloader"


def _load_save_folder() -> str:
    fallback = Path.home() / "Stories"
    try:
        saved = (_config_dir() / "save-folder").read_text(encoding="utf-8").strip()
    except OSError:
        saved = ""
    if saved and Path(saved).is_dir():
        return saved
    return str(fallback)


def _save_save_folder(folder: str) -> None:
    try:
        directory = _config_dir()
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "save-folder").write_text(folder, encoding="utf-8")
    except OSError:
        return


if __name__ == "__main__":
    main()
