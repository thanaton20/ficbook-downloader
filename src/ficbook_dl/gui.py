"""Desktop window for macOS and Windows."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ficbook_dl.client import Client
from ficbook_dl.download import FORMATS, download_story, save_story
from ficbook_dl.errors import Cancelled, FicbookError


def main() -> None:
    root = build_window()
    root.mainloop()


def build_window() -> tk.Tk:
    root = tk.Tk()
    root.title("Ficbook Downloader")
    root.minsize(560, 460)
    root.geometry("680x540")

    output = tk.StringVar(value=str(Path.home() / "Stories"))
    delay = tk.StringVar(value="1.5")
    format_vars = {fmt: tk.BooleanVar(value=True) for fmt in FORMATS}
    status = tk.StringVar(value="Paste one or more story links.")

    frame = ttk.Frame(root, padding=16)
    frame.pack(fill="both", expand=True)
    links = tk.Text(frame, height=7, wrap="word", undo=True)
    log = tk.Text(frame, height=12, wrap="word", state="disabled")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(1, weight=1)
    frame.rowconfigure(6, weight=1)

    ttk.Label(frame, text="Story links").grid(row=0, column=0, sticky="w")
    links.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(4, 10))

    ttk.Label(frame, text="Save to").grid(row=2, column=0, sticky="w")
    ttk.Entry(frame, textvariable=output).grid(row=3, column=0, sticky="ew", pady=(4, 10))
    ttk.Button(frame, text="Browse", command=lambda: _choose_folder(root, output)).grid(
        row=3, column=1, sticky="ew", padx=(8, 0), pady=(4, 10)
    )

    options = ttk.Frame(frame)
    options.grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 10))
    ttk.Label(options, text="Formats").pack(side="left")
    for fmt in FORMATS:
        ttk.Checkbutton(options, text=fmt.upper(), variable=format_vars[fmt]).pack(side="left", padx=(10, 0))
    ttk.Label(options, text="Pause (seconds)").pack(side="left", padx=(18, 6))
    ttk.Spinbox(options, from_=0, to=30, increment=0.5, textvariable=delay, width=6).pack(side="left")

    download = ttk.Button(frame, text="Download")
    download.grid(row=5, column=0, sticky="w", pady=(0, 10))
    ttk.Label(frame, textvariable=status).grid(row=5, column=1, sticky="w", padx=(12, 0), pady=(0, 10))
    log.grid(row=6, column=0, columnspan=2, sticky="nsew")

    def start() -> None:
        chosen = [fmt for fmt in FORMATS if format_vars[fmt].get()]
        urls = [line.strip() for line in links.get("1.0", "end").splitlines() if line.strip()]
        if not urls:
            messagebox.showinfo("Ficbook Downloader", "Paste at least one story link.", parent=root)
            return
        if not chosen:
            messagebox.showinfo("Ficbook Downloader", "Choose at least one format.", parent=root)
            return
        try:
            pause = float(delay.get().replace(",", "."))
        except ValueError:
            messagebox.showinfo("Ficbook Downloader", "Pause must be a number.", parent=root)
            return
        if pause < 0:
            messagebox.showinfo("Ficbook Downloader", "Pause cannot be negative.", parent=root)
            return
        stop = threading.Event()
        download.configure(text="Stop", command=stop.set)
        status.set("Downloading…")
        _log(log, f"Saving {', '.join(fmt.upper() for fmt in chosen)} to {output.get()}")
        thread = threading.Thread(
            target=_run,
            args=(root, urls, Path(output.get()), chosen, pause, stop, log, status, download, start),
            daemon=True,
        )
        thread.start()

    download.configure(command=start)
    return root


def _choose_folder(root: tk.Tk, output: tk.StringVar) -> None:
    chosen = filedialog.askdirectory(parent=root, initialdir=output.get() or str(Path.home()))
    if chosen:
        output.set(chosen)


def _run(root, urls, folder, formats, pause, stop, log, status, button, start) -> None:
    client = Client(delay=pause)
    saved = 0
    failed = 0
    for url in urls:
        if stop.is_set():
            root.after(0, _log, log, "Stopped.")
            break
        root.after(0, _log, log, url)
        try:
            story = download_story(
                client,
                url,
                on_chapter=lambda index, total, title: root.after(
                    0, _log, log, f"  {index}/{total} {title}"
                ),
                stop=stop.is_set,
            )
            paths = save_story(story, folder, formats)
        except Cancelled as exc:
            root.after(0, _log, log, str(exc))
            break
        except FicbookError as exc:
            failed += 1
            root.after(0, _log, log, f"error: {exc}")
            if stop.is_set():
                break
            continue
        except Exception as exc:
            failed += 1
            root.after(0, _log, log, f"error: {url}: {exc}")
            continue
        saved += 1
        for path in paths:
            root.after(0, _log, log, f"saved {path}")
    summary = f"Saved {saved} story." if saved == 1 else f"Saved {saved} stories."
    if failed:
        summary += f" {failed} failed."
    root.after(0, status.set, summary)
    root.after(0, lambda: button.configure(text="Download", command=start))


def _log(widget: tk.Text, message: str) -> None:
    widget.configure(state="normal")
    widget.insert("end", message + "\n")
    widget.see("end")
    widget.configure(state="disabled")


if __name__ == "__main__":
    main()
