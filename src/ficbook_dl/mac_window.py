"""Make the macOS title bar part of the window instead of a separate system strip."""

from __future__ import annotations

import ctypes
import ctypes.util
import sys
import tkinter as tk

_TITLE_HIDDEN = 1
_SEPARATOR_NONE = 1


def blend_title_bar(root: tk.Tk, color: str) -> None:
    """Keep the window light, hide the title text, and paint the title bar in `color`."""
    if sys.platform != "darwin":
        return
    try:
        root.wm_attributes("-appearance", "aqua")
    except tk.TclError:
        pass
    root.update_idletasks()
    try:
        _paint(root.title(), color)
    except (OSError, AttributeError, TypeError, ValueError):
        return


def _paint(title: str, color: str) -> None:
    objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.objc_getClass.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]

    def send(receiver, selector: str, *args, restype=ctypes.c_void_p, argtypes=()):
        call = ctypes.CFUNCTYPE(restype, ctypes.c_void_p, ctypes.c_void_p, *argtypes)(("objc_msgSend", objc))
        return call(receiver, objc.sel_registerName(selector.encode()), *args)

    red, green, blue = (int(color[index : index + 2], 16) / 255 for index in (1, 3, 5))
    paint = send(
        objc.objc_getClass(b"NSColor"),
        "colorWithSRGBRed:green:blue:alpha:",
        red,
        green,
        blue,
        1.0,
        argtypes=(ctypes.c_double,) * 4,
    )
    app = send(objc.objc_getClass(b"NSApplication"), "sharedApplication")
    # Light dialogs too, so alerts and folder pickers match the window in Dark Mode.
    aqua = send(objc.objc_getClass(b"NSString"), "stringWithUTF8String:", b"NSAppearanceNameAqua", argtypes=(ctypes.c_char_p,))
    light = send(objc.objc_getClass(b"NSAppearance"), "appearanceNamed:", aqua, argtypes=(ctypes.c_void_p,))
    send(app, "setAppearance:", light, restype=None, argtypes=(ctypes.c_void_p,))
    windows = send(app, "windows")
    for index in range(send(windows, "count", restype=ctypes.c_ulong)):
        window = send(windows, "objectAtIndex:", index, argtypes=(ctypes.c_ulong,))
        name = send(send(window, "title"), "UTF8String", restype=ctypes.c_char_p)
        if (name or b"").decode() != title:
            continue
        send(window, "setTitlebarAppearsTransparent:", True, restype=None, argtypes=(ctypes.c_bool,))
        send(window, "setTitleVisibility:", _TITLE_HIDDEN, restype=None, argtypes=(ctypes.c_long,))
        send(window, "setBackgroundColor:", paint, restype=None, argtypes=(ctypes.c_void_p,))
        separator = objc.sel_registerName(b"setTitlebarSeparatorStyle:")
        if send(window, "respondsToSelector:", separator, restype=ctypes.c_bool, argtypes=(ctypes.c_void_p,)):
            send(window, "setTitlebarSeparatorStyle:", _SEPARATOR_NONE, restype=None, argtypes=(ctypes.c_long,))
