#!/usr/bin/env python3
"""X11 text history. All entries live in memory; no Windows input events."""
import argparse, ctypes as C, ctypes.util, os, pathlib, signal, subprocess, sys, time

MAX_ITEMS = 50


class History:
    def __init__(self):
        self.items = []

    def add(self, text):
        if not text or len(text) > 4 * 1024 * 1024:
            return
        if text in self.items:
            self.items.remove(text)
        self.items.insert(0, text)
        del self.items[MAX_ITEMS:]


class XKeyEvent(C.Structure):
    _fields_ = [
        ("type", C.c_int),
        ("serial", C.c_ulong),
        ("send_event", C.c_int),
        ("display", C.c_void_p),
        ("window", C.c_ulong),
        ("root", C.c_ulong),
        ("subwindow", C.c_ulong),
        ("time", C.c_ulong),
        ("x", C.c_int),
        ("y", C.c_int),
        ("x_root", C.c_int),
        ("y_root", C.c_int),
        ("state", C.c_uint),
        ("keycode", C.c_uint),
        ("same_screen", C.c_int),
    ]


class XEvent(C.Union):
    _fields_ = [("type", C.c_int), ("key", XKeyEvent), ("pad", C.c_long * 24)]


class X11:
    def __init__(self):
        self.lib = C.CDLL(ctypes.util.find_library("X11") or "libX11.so.6")
        declarations = {
            "XOpenDisplay": ([C.c_char_p], C.c_void_p),
            "XDefaultRootWindow": ([C.c_void_p], C.c_ulong),
            "XCreateSimpleWindow": (
                [
                    C.c_void_p,
                    C.c_ulong,
                    C.c_int,
                    C.c_int,
                    C.c_uint,
                    C.c_uint,
                    C.c_uint,
                    C.c_ulong,
                    C.c_ulong,
                ],
                C.c_ulong,
            ),
            "XInternAtom": ([C.c_void_p, C.c_char_p, C.c_int], C.c_ulong),
            "XGetSelectionOwner": ([C.c_void_p, C.c_ulong], C.c_ulong),
            "XSetSelectionOwner": (
                [C.c_void_p, C.c_ulong, C.c_ulong, C.c_ulong],
                C.c_int,
            ),
            "XGrabServer": ([C.c_void_p], C.c_int),
            "XUngrabServer": ([C.c_void_p], C.c_int),
            "XSync": ([C.c_void_p, C.c_int], C.c_int),
            "XFlush": ([C.c_void_p], C.c_int),
            "XKeysymToKeycode": ([C.c_void_p, C.c_ulong], C.c_uint),
            "XGrabKey": (
                [C.c_void_p, C.c_int, C.c_uint, C.c_ulong, C.c_int, C.c_int, C.c_int],
                C.c_int,
            ),
            "XPending": ([C.c_void_p], C.c_int),
            "XNextEvent": ([C.c_void_p, C.POINTER(XEvent)], C.c_int),
            "XGetInputFocus": (
                [C.c_void_p, C.POINTER(C.c_ulong), C.POINTER(C.c_int)],
                C.c_int,
            ),
            "XSetInputFocus": ([C.c_void_p, C.c_ulong, C.c_int, C.c_ulong], C.c_int),
            "XCloseDisplay": ([C.c_void_p], C.c_int),
        }
        for name, (args, result) in declarations.items():
            fn = getattr(self.lib, name)
            fn.argtypes = args
            fn.restype = result
        self.display = self.lib.XOpenDisplay(None)
        if not self.display:
            raise RuntimeError("An X11 display is required")
        self.root = self.lib.XDefaultRootWindow(self.display)
        self.window = self.lib.XCreateSimpleWindow(
            self.display, self.root, 0, 0, 1, 1, 0, 0, 0
        )
        self.atom = self.lib.XInternAtom(
            self.display, b"_ZHOURONGYI_CLIPBOARD_HISTORY_V1", 0
        )

    def owner(self):
        return self.lib.XGetSelectionOwner(self.display, self.atom)

    def claim(self):
        self.lib.XGrabServer(self.display)
        try:
            if self.owner():
                return False
            self.lib.XSetSelectionOwner(self.display, self.atom, self.window, 0)
            self.lib.XSync(self.display, 0)
            return self.owner() == self.window
        finally:
            self.lib.XUngrabServer(self.display)
            self.lib.XFlush(self.display)

    def hotkeys(self):
        # Ctrl+Shift+J, Ctrl+Alt+H and Ctrl+Alt+V, with Caps/NumLock variants.
        for symbol, mods in [(ord("j"), 4 | 1), (ord("h"), 4 | 8), (ord("v"), 4 | 8)]:
            code = self.lib.XKeysymToKeycode(self.display, symbol)
            for locks in (0, 2, 16, 18):
                self.lib.XGrabKey(
                    self.display, code, mods | locks, self.root, False, 1, 1
                )
        self.lib.XSync(self.display, 0)

    def focus(self):
        window = C.c_ulong()
        revert = C.c_int()
        self.lib.XGetInputFocus(self.display, C.byref(window), C.byref(revert))
        return window.value

    def restore(self, window):
        self.lib.XSetInputFocus(self.display, window, 2, 0)
        self.lib.XFlush(self.display)

    def paste(self):
        lib = C.CDLL(ctypes.util.find_library("Xtst") or "libXtst.so.6")
        lib.XTestFakeKeyEvent.argtypes = [C.c_void_p, C.c_uint, C.c_int, C.c_ulong]
        shift = self.lib.XKeysymToKeycode(self.display, 0xFFE1)
        insert = self.lib.XKeysymToKeycode(self.display, 0xFF63)
        for key, down in [(shift, 1), (insert, 1), (insert, 0), (shift, 0)]:
            lib.XTestFakeKeyEvent(self.display, key, down, 0)
        self.lib.XFlush(self.display)


class App:
    def __init__(self, x):
        import tkinter as tk

        self.tk = tk
        self.x = x
        self.root = tk.Tk(className="ClipboardHistory")
        self.root.withdraw()
        self.history = History()
        self.popup = None
        self.previous_owner = 0
        self.last_text = None
        self.own_text = None
        self.x.hotkeys()
        self.root.after(30, self.events)
        self.root.after(250, self.poll)

    def poll(self):
        try:
            atom = self.x.lib.XInternAtom(self.x.display, b"CLIPBOARD", 0)
            owner = self.x.lib.XGetSelectionOwner(self.x.display, atom)
            if owner and owner != self.x.window:
                text = self.root.selection_get(
                    selection="CLIPBOARD", type="UTF8_STRING"
                )
                if text != self.last_text:
                    self.history.add(text)
                    self.last_text = text
            self.previous_owner = owner
        except self.tk.TclError:
            pass
        self.root.after(250, self.poll)

    def events(self):
        while self.x.lib.XPending(self.x.display):
            event = XEvent()
            self.x.lib.XNextEvent(self.x.display, C.byref(event))
            if event.type == 2:
                self.toggle()
            if event.type == 29:
                self.root.destroy()
                return
        self.root.after(30, self.events)

    def toggle(self):
        if self.popup:
            self.cancel()
            return
        if not self.history.items:
            return
        self.original_focus = self.x.focus()
        top = self.tk.Toplevel(self.root)
        self.popup = top
        top.title("Clipboard History")
        top.geometry("720x420")
        top.attributes("-topmost", True)
        self.tk.Label(
            top,
            text="Ctrl+Shift+J · Ctrl+Alt+H · Ctrl+Alt+V     j/k  Enter  Esc",
            anchor="w",
        ).pack(fill="x")
        self.listbox = self.tk.Listbox(
            top,
            font=("Noto Sans CJK SC", 12),
            activestyle="dotbox",
            exportselection=False,
        )
        self.listbox.pack(fill="both", expand=True)
        for text in self.history.items:
            self.listbox.insert(
                "end", text.replace("\n", " ⏎ ").replace("\r", "")[:160]
            )
        self.listbox.selection_set(0)
        self.listbox.focus_force()
        for key in [
            "<Escape>",
            "<Control-c>",
            "<Control-Shift-J>",
            "<Control-Alt-h>",
            "<Control-Alt-v>",
        ]:
            top.bind(key, lambda event: self.cancel() or "break")
        top.bind("<Return>", lambda event: self.choose() or "break")
        self.listbox.bind("<ButtonRelease-1>", lambda event: self.choose())
        for key, delta in [("j", 1), ("k", -1)]:
            top.bind(key, lambda event, d=delta: self.move(d) or "break")
        top.bind("<FocusOut>", lambda event: top.after(40, self.check_focus))
        top.protocol("WM_DELETE_WINDOW", self.cancel)

    def move(self, delta):
        current = self.listbox.curselection()
        index = max(
            0, min(len(self.history.items) - 1, (current[0] if current else 0) + delta)
        )
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(index)
        self.listbox.activate(index)
        self.listbox.see(index)

    def check_focus(self):
        if self.popup and self.popup.focus_displayof() is None:
            self.cancel(restore=False)

    def cancel(self, restore=True):
        if not self.popup:
            return
        self.popup.destroy()
        self.popup = None
        if restore:
            self.x.restore(self.original_focus)

    def choose(self):
        selected = self.listbox.curselection()
        if not selected:
            return
        text = self.history.items[selected[0]]
        self.own_text = text
        self.last_text = text
        # Tk owns both selections and serves exact UTF-8 text on demand.
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.selection_handle(
            lambda offset, length: self.own_text[
                int(offset) : int(offset) + int(length)
            ],
            selection="PRIMARY",
            type="UTF8_STRING",
        )
        self.root.selection_own(selection="PRIMARY")
        self.cancel()
        self.root.after(80, self.paste_if_focused)

    def paste_if_focused(self):
        if self.x.focus() == self.original_focus:
            self.x.paste()

    def run(self):
        self.root.mainloop()


def ensure_running():
    x = X11()
    if x.owner():
        return
    x.lib.XCloseDisplay(x.display)
    state = (
        pathlib.Path(
            os.environ.get("XDG_STATE_HOME", str(pathlib.Path.home() / ".local/state"))
        )
        / "clipboard-history"
    )
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    state.chmod(0o700)
    log = state / "service.log"
    fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    subprocess.Popen(
        [sys.executable, str(pathlib.Path(__file__).resolve())],
        stdin=subprocess.DEVNULL,
        stdout=fd,
        stderr=fd,
        start_new_session=True,
        close_fds=True,
    )
    os.close(fd)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ensure-running", action="store_true")
    p.add_argument("--check", action="store_true")
    a = p.parse_args()
    if a.ensure_running:
        ensure_running()
        return
    x = X11()
    if a.check:
        print("running" if x.owner() else "stopped")
        return
    if not x.claim():
        return
    App(x).run()


if __name__ == "__main__":
    main()
