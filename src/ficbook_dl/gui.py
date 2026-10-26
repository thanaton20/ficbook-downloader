"""Desktop window for macOS and Windows."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ficbook_dl.client import Client
from ficbook_dl.download import FORMATS, download_story, save_story
from ficbook_dl.errors import Cancelled, FicbookError, message
from ficbook_dl.i18n import CHOICES, choice_label, code_for_label, preferred_language, save_language, saved_status, t


def main() -> None:
    root = build_window()
    root.mainloop()


def build_window() -> tk.Tk:
    root = tk.Tk()
    root.minsize(560, 520)
    root.geometry("760x640")

    output = tk.StringVar(value=str(Path.home() / "Stories"))
    delay = tk.StringVar(value="1.5")
    format_vars = {fmt: tk.BooleanVar(value=True) for fmt in FORMATS}
    status = tk.StringVar()
    state = {"busy": False, "language": preferred_language()}

    frame = ttk.Frame(root, padding=16)
    frame.pack(fill="both", expand=True)
    links = tk.Text(frame, height=12, wrap="word", undo=True)
    log = tk.Text(frame, height=8, wrap="word", state="disabled")
    log.configure(
        font=("TkDefaultFont", 12),
        bg="#f3f4f6",
        fg="#374151",
        relief="flat",
        highlightthickness=1,
        highlightbackground="#d1d5db",
        highlightcolor="#d1d5db",
        padx=8,
        pady=6,
    )
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(1, weight=3)
    frame.rowconfigure(6, weight=1)

    heading = ttk.Frame(frame)
    heading.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
    title = ttk.Label(heading, font=("TkDefaultFont", 16, "bold"))
    title.pack(side="left")
    subtitle = ttk.Label(heading)
    subtitle.pack(side="left", padx=(8, 0))
    language_box = ttk.Combobox(
        heading,
        state="readonly",
        width=16,
        values=[label for _, label in CHOICES],
    )
    language_box.pack(side="right")
    language_label = ttk.Label(heading)
    language_label.pack(side="right", padx=(0, 8))

    _style_link_box(links)
    links.ui_language = state["language"]
    links.bind("<FocusIn>", lambda _event: _clear_link_hint(links))
    links.bind("<FocusOut>", lambda _event: _show_link_hint(links))
    links.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 14))

    save_label = ttk.Label(frame)
    save_label.grid(row=2, column=0, sticky="w")
    ttk.Entry(frame, textvariable=output).grid(row=3, column=0, sticky="ew", pady=(4, 10))
    browse = ttk.Button(frame, command=lambda: _choose_folder(root, output))
    browse.grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=(4, 10))

    options = ttk.Frame(frame)
    options.grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 10))
    formats_label = ttk.Label(options)
    formats_label.pack(side="left")
    for fmt in FORMATS:
        ttk.Checkbutton(options, text=fmt.upper(), variable=format_vars[fmt]).pack(side="left", padx=(10, 0))
    pause_label = ttk.Label(options)
    pause_label.pack(side="left", padx=(18, 6))
    ttk.Spinbox(options, from_=0, to=30, increment=0.5, textvariable=delay, width=6).pack(side="left")

    download = ttk.Button(frame)
    download.grid(row=5, column=0, sticky="w", pady=(0, 10))
    ttk.Label(frame, textvariable=status).grid(row=5, column=1, sticky="w", padx=(12, 0), pady=(0, 10))
    log.grid(row=6, column=0, columnspan=2, sticky="nsew")

    def apply(code: str, persist: bool) -> None:
        state["language"] = code
        if persist:
            save_language(code)
        root.title(t(code, "window_title"))
        title.configure(text=t(code, "story_links"))
        subtitle.configure(text=t(code, "one_per_line"))
        language_label.configure(text=t(code, "language"))
        save_label.configure(text=t(code, "save_to"))
        browse.configure(text=t(code, "browse"))
        formats_label.configure(text=t(code, "formats"))
        pause_label.configure(text=t(code, "pause"))
        download.configure(text=t(code, "stop" if state["busy"] else "download"))
        if not state["busy"]:
            status.set(t(code, "status_idle"))
        links.ui_language = code
        if links.hint_on:
            links.delete("1.0", "end")
            links.hint_on = False
        _show_link_hint(links)
        language_box.set(choice_label(code))

    def on_language(_event=None) -> None:
        apply(code_for_label(language_box.get()), persist=True)

    language_box.bind("<<ComboboxSelected>>", on_language)

    def start() -> None:
        code = state["language"]
        chosen = [fmt for fmt in FORMATS if format_vars[fmt].get()]
        urls = _link_lines(links)
        if not urls:
            messagebox.showinfo(t(code, "window_title"), t(code, "need_link"), parent=root)
            return
        if not chosen:
            messagebox.showinfo(t(code, "window_title"), t(code, "need_format"), parent=root)
            return
        try:
            pause = float(delay.get().replace(",", "."))
        except ValueError:
            messagebox.showinfo(t(code, "window_title"), t(code, "pause_number"), parent=root)
            return
        if pause < 0:
            messagebox.showinfo(t(code, "window_title"), t(code, "pause_negative"), parent=root)
            return
        stop = threading.Event()
        state["busy"] = True
        download.configure(text=t(code, "stop"), command=stop.set)
        status.set(t(code, "downloading"))
        _log(log, t(code, "saving_to", formats=", ".join(fmt.upper() for fmt in chosen), folder=output.get()))
        thread = threading.Thread(
            target=_run,
            args=(root, urls, Path(output.get()), chosen, pause, stop, log, status, download, start, code, state),
            daemon=True,
        )
        thread.start()

    download.configure(command=start)
    apply(state["language"], persist=False)
    return root


_LINK_FG = "#111827"
_HINT_FG = "#6b7280"


def _style_link_box(widget: tk.Text) -> None:
    widget.configure(
        height=12,
        font=("TkDefaultFont", 15),
        bg="#f5f3ff",
        fg=_LINK_FG,
        insertbackground=_LINK_FG,
        insertwidth=2,
        relief="solid",
        borderwidth=0,
        highlightthickness=3,
        highlightbackground="#6d28d9",
        highlightcolor="#4c1d95",
        padx=12,
        pady=10,
    )
    widget.hint_on = False
    widget.ui_language = "en"


def _show_link_hint(widget: tk.Text) -> None:
    if widget.get("1.0", "end").strip():
        return
    widget.insert("1.0", t(widget.ui_language, "hint"))
    widget.configure(fg=_HINT_FG)
    widget.hint_on = True


def _clear_link_hint(widget: tk.Text) -> None:
    if not widget.hint_on:
        return
    widget.delete("1.0", "end")
    widget.configure(fg=_LINK_FG)
    widget.hint_on = False


def _link_lines(widget: tk.Text) -> list[str]:
    if widget.hint_on:
        return []
    return [line.strip() for line in widget.get("1.0", "end").splitlines() if line.strip()]


def _choose_folder(root: tk.Tk, output: tk.StringVar) -> None:
    chosen = filedialog.askdirectory(parent=root, initialdir=output.get() or str(Path.home()))
    if chosen:
        output.set(chosen)


def _run(root, urls, folder, formats, pause, stop, log, status, button, start, language, state) -> None:
    client = Client(delay=pause)
    saved = 0
    failed = 0
    for url in urls:
        if stop.is_set():
            root.after(0, _log, log, t(language, "stopped"))
            break
        root.after(0, _log, log, url)
        try:
            story = download_story(
                client,
                url,
                on_chapter=lambda index, total, title: root.after(0, _log, log, f"  {index}/{total} {title}"),
                stop=stop.is_set,
                language=language,
            )
            paths = save_story(story, folder, formats, language)
        except Cancelled:
            root.after(0, _log, log, t(language, "stopped"))
            break
        except FicbookError as exc:
            failed += 1
            root.after(0, _log, log, t(language, "error_line", message=message(exc, language)))
            if stop.is_set():
                break
            continue
        except Exception as exc:
            failed += 1
            root.after(0, _log, log, t(language, "error_line", message=f"{url}: {exc}"))
            continue
        saved += 1
        for path in paths:
            root.after(0, _log, log, t(language, "saved_path", path=path))
    summary = saved_status(language, saved, failed)

    def finish() -> None:
        state["busy"] = False
        status.set(summary)
        button.configure(text=t(state["language"], "download"), command=start)

    root.after(0, finish)


def _log(widget: tk.Text, message_text: str) -> None:
    widget.configure(state="normal")
    widget.insert("end", message_text + "\n")
    widget.see("end")
    widget.configure(state="disabled")


if __name__ == "__main__":
    main()
