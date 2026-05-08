#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Huawei KoBackup Decryptor — GUI Application
A modern, dark-themed graphical interface for kobackupdec.py

Requires: tkinter (bundled with Python), pycryptodome
"""

import logging
import os
import pathlib
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import queue
import time
import json
import subprocess
from tkinterdnd2 import TkinterDnD, DND_FILES

# ---------------------------------------------------------------------------
#  Logging handler that forwards records into a thread-safe queue
# ---------------------------------------------------------------------------

class QueueHandler(logging.Handler):
    """Sends log records to a queue for consumption by the GUI thread."""

    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))


# ---------------------------------------------------------------------------
#  Main GUI Application
# ---------------------------------------------------------------------------

class KoBackupDecGUI(TkinterDnD.Tk):
    """Tkinter-based GUI for the Huawei KoBackup decryptor."""

    # -- Colour palette (dark mode) ----------------------------------------
    BG           = "#0f1117"
    BG_CARD      = "#181b24"
    BG_INPUT     = "#1e2230"
    BG_HOVER     = "#252a3a"
    FG           = "#e4e6ed"
    FG_DIM       = "#8b8fa3"
    ACCENT       = "#6c63ff"
    ACCENT_HOVER = "#8a82ff"
    ACCENT_DARK  = "#4e47b8"
    SUCCESS      = "#34d399"
    WARNING      = "#fbbf24"
    ERROR        = "#f87171"
    BORDER       = "#2a2e3d"
    LOG_BG       = "#12141c"

    FONT_FAMILY  = "Segoe UI"
    FONT_TITLE   = ("Segoe UI", 22, "bold")
    FONT_SUB     = ("Segoe UI", 11)
    FONT_LABEL   = ("Segoe UI", 10, "bold")
    FONT_INPUT   = ("Segoe UI", 10)
    FONT_BTN     = ("Segoe UI", 11, "bold")
    FONT_LOG     = ("Consolas", 9)
    FONT_STATUS  = ("Segoe UI", 10)

    def __init__(self):
        super().__init__()

        self.title("KoBackup Decryptor")
        self.configure(bg=self.BG)
        self.minsize(600, 500)
        self.geometry("900x820")

        # Center on screen
        self.update_idletasks()
        w, h = 900, 820
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        # Application icon — set title-bar colour on Windows
        try:
            self.iconbitmap(default="")
        except Exception:
            pass

        # State
        self._running = False
        self._log_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # not paused initially
        self._worker_thread = None
        self._folder_vars = {}   # {name: BooleanVar} for folder selection

        # ---------- configure ttk styles -----------
        self._setup_styles()

        # ---------- build widgets ------------------
        # Scrollable main container so content never gets clipped
        self._build_main_container()

        self._build_header()
        self._build_form()
        self._build_options()
        self._build_folder_selector()
        self._build_action()
        self._build_log()
        self._build_status_bar()

        # Bind resize to reflow folder checkboxes
        self.bind("<Configure>", self._on_resize)

        # Load saved settings
        self._load_config()

        # Save config on exit
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Start polling the log queue
        self._poll_log_queue()

    # -----------------------------------------------------------------
    #  Style helpers
    # -----------------------------------------------------------------

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("Card.TFrame", background=self.BG_CARD)
        style.configure("Dark.TFrame", background=self.BG)

        style.configure("TCheckbutton",
                        background=self.BG_CARD,
                        foreground=self.FG,
                        font=self.FONT_INPUT,
                        focuscolor=self.BG_CARD)
        style.map("TCheckbutton",
                  background=[("active", self.BG_CARD)],
                  foreground=[("active", self.ACCENT)])

        style.configure("Horizontal.TProgressbar",
                        troughcolor=self.BG_INPUT,
                        background=self.ACCENT,
                        thickness=6,
                        borderwidth=0)

    def _make_rounded_frame(self, parent, expandable=False, **kw):
        """Simulated rounded card using a Frame + padding.
        Set expandable=True for sections that should grow (like the log).
        """
        outer = tk.Frame(parent, bg=self.BG, padx=0, pady=6)
        inner = tk.Frame(outer, bg=self.BG_CARD, highlightbackground=self.BORDER,
                         highlightthickness=1, padx=20, pady=16, **kw)
        if expandable:
            inner.pack(fill="both", expand=True)
        else:
            inner.pack(fill="x")
        return outer, inner

    def _build_main_container(self):
        """Create a vertically-scrollable container for all widgets."""
        # Status bar is packed at bottom of self, everything else in _main
        self._main = tk.Frame(self, bg=self.BG)
        self._main.pack(fill="both", expand=True)

    # -----------------------------------------------------------------
    #  Build UI sections
    # -----------------------------------------------------------------

    def _build_header(self):
        hdr = tk.Frame(self._main, bg=self.BG, pady=10)
        hdr.pack(fill="x", padx=30)

        # Gradient-like effect: coloured accent bar
        accent_bar = tk.Frame(hdr, bg=self.ACCENT, height=4)
        accent_bar.pack(fill="x", pady=(0, 14))

        title = tk.Label(hdr, text="🔐  KoBackup Decryptor",
                         font=self.FONT_TITLE, bg=self.BG, fg=self.FG)
        title.pack(anchor="w")

        sub = tk.Label(hdr, text="Huawei HiSuite / KoBackup encrypted backup decryption tool  •  v20200705",
                       font=self.FONT_SUB, bg=self.BG, fg=self.FG_DIM)
        sub.pack(anchor="w", pady=(2, 0))

    # -- Form fields ---------------------------------------------------

    def _build_form(self):
        outer, card = self._make_rounded_frame(self._main)
        outer.pack(fill="x", padx=30)

        # Section title
        sec = tk.Label(card, text="CONFIGURATION", font=("Segoe UI", 9, "bold"),
                       bg=self.BG_CARD, fg=self.ACCENT)
        sec.pack(anchor="w", pady=(0, 10))

        # Password
        self._add_field_label(card, "Backup Password")
        pw_frame = tk.Frame(card, bg=self.BG_CARD)
        pw_frame.pack(fill="x", pady=(0, 12))

        self.password_var = tk.StringVar()
        self.show_pw = False
        self.pw_entry = tk.Entry(pw_frame, textvariable=self.password_var,
                                 show="•", font=self.FONT_INPUT,
                                 bg=self.BG_INPUT, fg=self.FG,
                                 insertbackground=self.ACCENT,
                                 relief="flat", bd=0,
                                 highlightbackground=self.BORDER,
                                 highlightthickness=1,
                                 highlightcolor=self.ACCENT)
        self.pw_entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 8))

        self.toggle_pw_btn = tk.Button(pw_frame, text="👁", font=("Segoe UI", 11),
                                       bg=self.BG_INPUT, fg=self.FG_DIM,
                                       activebackground=self.BG_HOVER,
                                       activeforeground=self.FG,
                                       relief="flat", bd=0, cursor="hand2",
                                       command=self._toggle_password)
        self.toggle_pw_btn.pack(side="right", ipadx=6, ipady=4)

        # Backup path
        self._add_field_label(card, "Backup Folder")
        self._build_path_row(card, "backup")

        # Destination path
        self._add_field_label(card, "Destination Folder")
        self._build_path_row(card, "dest")

    def _add_field_label(self, parent, text):
        lbl = tk.Label(parent, text=text, font=self.FONT_LABEL,
                       bg=self.BG_CARD, fg=self.FG_DIM)
        lbl.pack(anchor="w", pady=(0, 3))

    def _build_path_row(self, parent, tag):
        row = tk.Frame(parent, bg=self.BG_CARD)
        row.pack(fill="x", pady=(0, 12))

        var = tk.StringVar()
        setattr(self, f"{tag}_var", var)

        entry = tk.Entry(row, textvariable=var, font=self.FONT_INPUT,
                         bg=self.BG_INPUT, fg=self.FG,
                         insertbackground=self.ACCENT,
                         relief="flat", bd=0,
                         highlightbackground=self.BORDER,
                         highlightthickness=1,
                         highlightcolor=self.ACCENT)
        entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 8))

        # Enable Drag and Drop
        entry.drop_target_register(DND_FILES)
        entry.dnd_bind('<<Drop>>', lambda e, v=var, t=tag: self._on_drop(e, v, t))

        btn = tk.Button(row, text="Browse", font=("Segoe UI", 9, "bold"),
                        bg=self.ACCENT, fg="#ffffff",
                        activebackground=self.ACCENT_HOVER,
                        activeforeground="#ffffff",
                        relief="flat", bd=0, cursor="hand2",
                        padx=14, pady=4,
                        command=lambda t=tag: self._browse(t))
        btn.pack(side="right", ipady=2)

        # Hover effects
        btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=self.ACCENT_HOVER))
        btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=self.ACCENT))

    # -- Options section -----------------------------------------------

    def _build_options(self):
        outer, card = self._make_rounded_frame(self._main)
        outer.pack(fill="x", padx=30)

        sec = tk.Label(card, text="OPTIONS", font=("Segoe UI", 9, "bold"),
                       bg=self.BG_CARD, fg=self.ACCENT)
        sec.pack(anchor="w", pady=(0, 10))

        opts_row = tk.Frame(card, bg=self.BG_CARD)
        opts_row.pack(fill="x")

        self.expandtar_var = tk.BooleanVar(value=False)
        self.writable_var  = tk.BooleanVar(value=False)

        cb1 = ttk.Checkbutton(opts_row, text="  Expand TAR archives",
                               variable=self.expandtar_var)
        cb1.pack(side="left", padx=(0, 30))

        cb2 = ttk.Checkbutton(opts_row, text="  Keep files writable (skip read-only)",
                               variable=self.writable_var)
        cb2.pack(side="left")

        # Verbose level
        verb_row = tk.Frame(card, bg=self.BG_CARD)
        verb_row.pack(fill="x", pady=(12, 0))

        vlbl = tk.Label(verb_row, text="Log Verbosity", font=self.FONT_LABEL,
                        bg=self.BG_CARD, fg=self.FG_DIM)
        vlbl.pack(side="left", padx=(0, 12))

        self.verbose_var = tk.StringVar(value="INFO")
        for level in ("ERROR", "WARNING", "INFO", "DEBUG"):
            rb = tk.Radiobutton(verb_row, text=level, variable=self.verbose_var,
                                value=level,
                                font=("Segoe UI", 9),
                                bg=self.BG_CARD, fg=self.FG,
                                selectcolor=self.BG_INPUT,
                                activebackground=self.BG_CARD,
                                activeforeground=self.ACCENT,
                                highlightthickness=0,
                                cursor="hand2")
            rb.pack(side="left", padx=(0, 10))

    # -- Folder selection panel ----------------------------------------

    def _build_folder_selector(self):
        outer, card = self._make_rounded_frame(self._main)
        outer.pack(fill="x", padx=30)
        self._folder_card = card
        self._folder_outer = outer

        # Header row with title + buttons
        hdr = tk.Frame(card, bg=self.BG_CARD)
        hdr.pack(fill="x", pady=(0, 8))

        sec = tk.Label(hdr, text="FOLDER SELECTION",
                       font=("Segoe UI", 9, "bold"),
                       bg=self.BG_CARD, fg=self.ACCENT)
        sec.pack(side="left")

        desel_btn = tk.Button(hdr, text="Deselect All",
                              font=("Segoe UI", 8),
                              bg=self.BG_INPUT, fg=self.FG_DIM,
                              activebackground=self.BG_HOVER,
                              activeforeground=self.FG,
                              relief="flat", bd=0, cursor="hand2",
                              padx=8, pady=2,
                              command=lambda: self._set_all_folders(False))
        desel_btn.pack(side="right", padx=(4, 0))

        sel_btn = tk.Button(hdr, text="Select All",
                            font=("Segoe UI", 8),
                            bg=self.BG_INPUT, fg=self.FG_DIM,
                            activebackground=self.BG_HOVER,
                            activeforeground=self.FG,
                            relief="flat", bd=0, cursor="hand2",
                            padx=8, pady=2,
                            command=lambda: self._set_all_folders(True))
        sel_btn.pack(side="right", padx=(4, 0))

        scan_btn = tk.Button(hdr, text="🔍 Scan",
                             font=("Segoe UI", 8, "bold"),
                             bg=self.ACCENT, fg="#ffffff",
                             activebackground=self.ACCENT_HOVER,
                             activeforeground="#ffffff",
                             relief="flat", bd=0, cursor="hand2",
                             padx=8, pady=2,
                             command=self._scan_backup_folders)
        scan_btn.pack(side="right", padx=(4, 0))

        # Hint label
        self._folder_hint = tk.Label(
            card,
            text="Set a backup folder above, then click Scan to detect available folders.",
            font=("Segoe UI", 9),
            bg=self.BG_CARD, fg=self.FG_DIM, anchor="w")
        self._folder_hint.pack(fill="x")

        # Scrollable checkbox area
        self._folder_canvas = tk.Canvas(card, bg=self.BG_CARD,
                                        highlightthickness=0, height=0)
        self._folder_inner = tk.Frame(self._folder_canvas, bg=self.BG_CARD)
        self._folder_canvas.create_window((0, 0), window=self._folder_inner,
                                          anchor="nw")
        # Don't pack canvas yet — shown after scan

    def _scan_backup_folders(self):
        """Scan the backup path and populate folder checkboxes."""
        bkp = self.backup_var.get().strip()
        if not bkp or not pathlib.Path(bkp).is_dir():
            messagebox.showwarning("No Backup Folder",
                                   "Please select a valid backup folder first.")
            return

        bkp_path = pathlib.Path(bkp)

        # Find the files_folder
        files_folder = None
        if bkp_path.joinpath('info.xml').exists():
            files_folder = bkp_path
        else:
            bf1 = bkp_path.joinpath('backupFiles1')
            if bf1.is_dir():
                info_xml = next(bf1.glob('**/info.xml'), None)
                if info_xml:
                    files_folder = info_xml.parent

        # Collect folder names
        folder_names = []

        # Root files (apk, db, tar in the files_folder)
        if files_folder:
            has_root = any(
                f.is_file() and f.suffix.lower() != '.xml'
                for f in files_folder.glob('*'))
            if has_root:
                folder_names.append(('__root__', '📄  Root files (APK, DB, TAR)'))

            for entry in sorted(files_folder.glob('*')):
                if entry.is_dir():
                    folder_names.append(
                        (entry.name, f'📁  {entry.name}'))

        # Media folder
        if bkp_path.joinpath('media').is_dir():
            folder_names.append(('__media__', '🎬  Media'))

        # Clear old checkboxes
        for w in self._folder_inner.winfo_children():
            w.destroy()
        self._folder_vars.clear()

        if not folder_names:
            self._folder_hint.configure(
                text="No decryptable folders found in this backup.")
            self._folder_canvas.pack_forget()
            return

        self._folder_hint.pack_forget()

        # Build checkbox grid (3 columns)
        cols = 3
        for i, (key, label) in enumerate(folder_names):
            var = tk.BooleanVar(value=True)
            self._folder_vars[key] = var
            cb = tk.Checkbutton(
                self._folder_inner, text=label, variable=var,
                font=("Segoe UI", 9),
                bg=self.BG_CARD, fg=self.FG,
                selectcolor=self.BG_INPUT,
                activebackground=self.BG_CARD,
                activeforeground=self.ACCENT,
                highlightthickness=0, cursor="hand2",
                anchor="w")
            cb.grid(row=i // cols, column=i % cols,
                    sticky="w", padx=(0, 18), pady=2)

        self._folder_canvas.pack(fill="x", pady=(4, 0))
        self._folder_inner.update_idletasks()
        self._folder_canvas.configure(
            height=self._folder_inner.winfo_reqheight())

    def _set_all_folders(self, state: bool):
        for var in self._folder_vars.values():
            var.set(state)

    def _get_selected_folders(self):
        """Return set of selected folder keys."""
        return {k for k, v in self._folder_vars.items() if v.get()}

    # -- Action button & progress bar -----------------------------------

    def _build_action(self):
        action_frame = tk.Frame(self._main, bg=self.BG, pady=6)
        action_frame.pack(fill="x", padx=30)

        # Progress bar
        self.progress = ttk.Progressbar(action_frame, mode="indeterminate",
                                        style="Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(0, 10))

        btn_row = tk.Frame(action_frame, bg=self.BG)
        btn_row.pack(fill="x")

        self.decrypt_btn = tk.Button(
            btn_row,
            text="🔓  Start Decryption",
            font=self.FONT_BTN,
            bg=self.ACCENT,
            fg="#ffffff",
            activebackground=self.ACCENT_HOVER,
            activeforeground="#ffffff",
            relief="flat", bd=0,
            cursor="hand2",
            padx=28, pady=10,
            command=self._start_decrypt
        )
        self.decrypt_btn.pack(side="left")
        self.decrypt_btn.bind("<Enter>",
                              lambda e: self.decrypt_btn.configure(bg=self.ACCENT_HOVER))
        self.decrypt_btn.bind("<Leave>",
                              lambda e: self.decrypt_btn.configure(bg=self.ACCENT))

        # Pause button
        self.pause_btn = tk.Button(
            btn_row,
            text="⏸  Pause",
            font=("Segoe UI", 10, "bold"),
            bg=self.WARNING,
            fg="#1a1a2e",
            activebackground="#f59e0b",
            activeforeground="#1a1a2e",
            relief="flat", bd=0,
            cursor="hand2",
            padx=18, pady=10,
            state="disabled",
            command=self._toggle_pause
        )
        self.pause_btn.pack(side="left", padx=(10, 0))

        # Stop button
        self.stop_btn = tk.Button(
            btn_row,
            text="⏹  Stop",
            font=("Segoe UI", 10, "bold"),
            bg=self.ERROR,
            fg="#ffffff",
            activebackground="#ef4444",
            activeforeground="#ffffff",
            relief="flat", bd=0,
            cursor="hand2",
            padx=18, pady=10,
            state="disabled",
            command=self._stop_decrypt
        )
        self.stop_btn.pack(side="left", padx=(10, 0))

        self.open_output_btn = tk.Button(
            btn_row,
            text="📂 Open Output",
            font=("Segoe UI", 9),
            bg=self.SUCCESS,
            fg="#1a1a2e",
            activebackground="#10b981",
            activeforeground="#1a1a2e",
            relief="flat", bd=0,
            cursor="hand2",
            padx=14, pady=8,
            state="disabled",
            command=self._open_output_folder
        )
        self.open_output_btn.pack(side="right", padx=(10, 0))

        self.export_log_btn = tk.Button(
            btn_row,
            text="Export Log",
            font=("Segoe UI", 9),
            bg=self.BG_INPUT,
            fg=self.FG_DIM,
            activebackground=self.BG_HOVER,
            activeforeground=self.FG,
            relief="flat", bd=0,
            cursor="hand2",
            padx=14, pady=8,
            command=self._export_log
        )
        self.export_log_btn.pack(side="right", padx=(10, 0))

        self.clear_log_btn = tk.Button(
            btn_row,
            text="Clear Log",
            font=("Segoe UI", 9),
            bg=self.BG_INPUT,
            fg=self.FG_DIM,
            activebackground=self.BG_HOVER,
            activeforeground=self.FG,
            relief="flat", bd=0,
            cursor="hand2",
            padx=14, pady=8,
            command=self._clear_log
        )
        self.clear_log_btn.pack(side="right")

    # -- Log output area -----------------------------------------------

    def _build_log(self):
        outer, card = self._make_rounded_frame(self._main, expandable=True)
        outer.pack(fill="both", expand=True, padx=30)

        sec = tk.Label(card, text="LOG OUTPUT", font=("Segoe UI", 9, "bold"),
                       bg=self.BG_CARD, fg=self.ACCENT)
        sec.pack(anchor="w", pady=(0, 6))

        log_frame = tk.Frame(card, bg=self.LOG_BG, highlightbackground=self.BORDER,
                             highlightthickness=1)
        log_frame.pack(fill="both", expand=True)

        self.log_text = tk.Text(log_frame, font=self.FONT_LOG,
                                bg=self.LOG_BG, fg="#a0aec0",
                                insertbackground=self.ACCENT,
                                relief="flat", bd=8,
                                wrap="word",
                                state="disabled",
                                highlightthickness=0)
        scroll = tk.Scrollbar(log_frame, command=self.log_text.yview,
                              bg=self.BG_CARD, troughcolor=self.LOG_BG,
                              activebackground=self.ACCENT,
                              highlightthickness=0, bd=0)
        self.log_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True)

        # Tag colours for log levels
        self.log_text.tag_configure("ERROR",   foreground=self.ERROR)
        self.log_text.tag_configure("WARNING", foreground=self.WARNING)
        self.log_text.tag_configure("INFO",    foreground=self.SUCCESS)
        self.log_text.tag_configure("DEBUG",   foreground=self.FG_DIM)
        self.log_text.tag_configure("CRITICAL", foreground=self.ERROR,
                                    font=("Consolas", 9, "bold"))

    # -- Status bar ----------------------------------------------------

    def _build_status_bar(self):
        bar = tk.Frame(self, bg=self.BORDER, height=30)
        bar.pack(fill="x", side="bottom")

        self.status_var = tk.StringVar(value="Ready")
        self.status_lbl = tk.Label(bar, textvariable=self.status_var,
                                   font=self.FONT_STATUS,
                                   bg=self.BORDER, fg=self.FG_DIM,
                                   padx=14, pady=4)
        self.status_lbl.pack(side="left")

        ver = tk.Label(bar, text="kobackupdec v20200705",
                       font=("Segoe UI", 8), bg=self.BORDER, fg=self.FG_DIM,
                       padx=14)
        ver.pack(side="right")

    # -----------------------------------------------------------------
    #  Responsive helpers
    # -----------------------------------------------------------------

    _last_resize_width = 0

    def _on_resize(self, event):
        """Reflow folder checkboxes when the window width changes."""
        if event.widget is not self:
            return
        # Only reflow when width changes meaningfully (>30px)
        if abs(event.width - self._last_resize_width) > 30:
            self._last_resize_width = event.width
            self._reflow_folder_checkboxes()

    def _reflow_folder_checkboxes(self):
        """Re-grid folder checkboxes to fit the current width."""
        children = self._folder_inner.winfo_children()
        if not children:
            return
        # Estimate available width (window - padding)
        avail = self.winfo_width() - 120
        # Measure widest checkbox
        max_cb_w = max(c.winfo_reqwidth() for c in children) or 200
        cols = max(1, avail // (max_cb_w + 18))
        for i, cb in enumerate(children):
            cb.grid_configure(row=i // cols, column=i % cols)
        self._folder_inner.update_idletasks()
        self._folder_canvas.configure(
            height=self._folder_inner.winfo_reqheight())

    # -----------------------------------------------------------------
    #  Actions & helpers
    # -----------------------------------------------------------------

    def _toggle_password(self):
        self.show_pw = not self.show_pw
        self.pw_entry.configure(show="" if self.show_pw else "•")
        self.toggle_pw_btn.configure(text="🔒" if self.show_pw else "👁")

    def _browse(self, tag):
        if tag == "dest":
            # For destination: pick a parent dir, then ask for a new subfolder name
            parent = filedialog.askdirectory(title="Select parent folder for output")
            if parent:
                subfolder = simpledialog.askstring(
                    "Destination Folder Name",
                    "Enter a name for the new output folder:",
                    parent=self
                )
                if subfolder and subfolder.strip():
                    full = os.path.join(parent, subfolder.strip())
                    self.dest_var.set(full)
        else:
            path = filedialog.askdirectory(title="Select folder")
            if path:
                getattr(self, f"{tag}_var").set(path)
                if tag == "backup":
                    self._scan_backup_folders()

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _append_log(self, msg: str):
        self.log_text.configure(state="normal")
        tag = None
        for lvl in ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"):
            if msg.startswith(lvl):
                tag = lvl
                break
        if tag:
            self.log_text.insert("end", msg + "\n", tag)
        else:
            self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _poll_log_queue(self):
        """Drain queued log messages into the text widget."""
        while True:
            try:
                msg = self._log_queue.get_nowait()
                self._append_log(msg)
            except queue.Empty:
                break
        self.after(100, self._poll_log_queue)

    # -- Validation ---

    def _validate(self) -> bool:
        pw   = self.password_var.get().strip()
        bkp  = self.backup_var.get().strip()
        dest = self.dest_var.get().strip()

        if not pw:
            messagebox.showwarning("Missing Password",
                                   "Please enter the backup password.")
            return False
        if not bkp or not pathlib.Path(bkp).is_dir():
            messagebox.showwarning("Invalid Backup Folder",
                                   "The backup folder does not exist.\n"
                                   "Please select a valid directory.")
            return False
        if not dest:
            messagebox.showwarning("Missing Destination",
                                   "Please specify a destination folder.")
            return False
        if pathlib.Path(dest).is_dir():
            proceed = messagebox.askyesno(
                "Destination Exists",
                "The destination folder already exists.\n"
                "Decrypted files will be written into it and may overwrite "
                "existing content.\n\nContinue anyway?"
            )
            if not proceed:
                return False
        return True

    # -- Stop / Pause controls ---

    def _toggle_pause(self):
        if self._pause_event.is_set():
            self._pause_event.clear()
            self.pause_btn.configure(text="▶  Resume", bg=self.SUCCESS)
            self.status_var.set("⏸  Paused")
            self.progress.stop()
        else:
            self._pause_event.set()
            self.pause_btn.configure(text="⏸  Pause", bg=self.WARNING)
            self.status_var.set("▶  Resumed — decrypting…")
            self.progress.start(12)

    def _stop_decrypt(self):
        if self._running:
            self._stop_event.set()
            self._pause_event.set()  # unblock if paused
            self.status_var.set("⏹  Stopping…")

    def _check_stop_pause(self):
        """Returns True if thread should abort. Blocks while paused."""
        if self._stop_event.is_set():
            return True
        while not self._pause_event.is_set():
            if self._stop_event.is_set():
                return True
            time.sleep(0.1)
        return False

    def _set_controls_running(self, running):
        """Toggle button states for running / idle."""
        if running:
            self.decrypt_btn.configure(state="disabled", bg=self.ACCENT_DARK,
                                       text="⏳  Decrypting…")
            self.pause_btn.configure(state="normal")
            self.stop_btn.configure(state="normal")
        else:
            self.decrypt_btn.configure(state="normal", bg=self.ACCENT,
                                       text="🔓  Start Decryption")
            self.pause_btn.configure(state="disabled",
                                     text="⏸  Pause", bg=self.WARNING)
            self.stop_btn.configure(state="disabled")

    # -- Decryption thread ---

    def _start_decrypt(self):
        if self._running:
            return
        if not self._validate():
            return

        self._running = True
        self._stop_event.clear()
        self._pause_event.set()
        self._set_controls_running(True)
        self.progress.start(12)
        self.status_var.set("🔑  Verifying password…")

        self._worker_thread = threading.Thread(
            target=self._run_decrypt, daemon=True)
        self._worker_thread.start()

    def _setup_logging(self):
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        level_map = {
            "ERROR":   logging.ERROR,
            "WARNING": logging.WARNING,
            "INFO":    logging.INFO,
            "DEBUG":   logging.DEBUG,
        }
        root_logger.setLevel(
            level_map.get(self.verbose_var.get(), logging.INFO))
        qh = QueueHandler(self._log_queue)
        qh.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        root_logger.addHandler(qh)

    def _find_files_folder(self, bkp_path):
        """Locate the folder containing info.xml."""
        if bkp_path.joinpath('info.xml').exists():
            return bkp_path
        bf1 = bkp_path.joinpath('backupFiles1')
        if bf1.is_dir():
            info_xml = next(bf1.glob('**/info.xml'), None)
            if info_xml:
                return info_xml.parent
            raise FileNotFoundError('Unable to find info.xml in backupFiles1!')
        raise FileNotFoundError(
            'No backupFiles1 folder nor info.xml file found!')

    def _run_decrypt(self):
        """Background thread: verify password then decrypt with stop/pause."""
        import kobackupdec
        self._setup_logging()

        password  = self.password_var.get().strip().encode('utf-8')
        bkp_path  = pathlib.Path(self.backup_var.get().strip())
        dest_path = pathlib.Path(self.dest_var.get().strip())
        expand    = self.expandtar_var.get()
        writable  = self.writable_var.get()

        success = False
        stopped = False
        try:
            # ── Phase 1: locate backup & verify password ──────────
            files_folder = self._find_files_folder(bkp_path)

            decrypt_info = kobackupdec.parse_info_xml(
                files_folder.joinpath('info.xml'), password)
            if not decrypt_info:
                raise ValueError('Failed to parse info.xml')
            if not decrypt_info.decryptor.good:
                raise ValueError(
                    'Wrong password! Decryptor verification failed.')

            logging.info('Password verified successfully!')
            self.after(0, lambda: self.status_var.set(
                '✅  Password OK — decrypting…'))

            if self._check_stop_pause():
                raise InterruptedError('Stopped')

            # ── Phase 2: parse XML keys ───────────────────────────
            dest_path.mkdir(0o755, parents=True, exist_ok=True)

            for entry in files_folder.glob('*.xml'):
                if self._check_stop_pause():
                    raise InterruptedError('Stopped')
                if entry.name != 'info.xml' \
                        and not entry.name.startswith('._'):
                    kobackupdec.parse_generic_xml(entry, decrypt_info)

            logging.debug(decrypt_info.dump())

            # Determine which folders the user selected
            selected = self._get_selected_folders()
            # If no scan was done (no checkboxes), decrypt everything
            decrypt_all = len(self._folder_vars) == 0

            # ── Phase 3: decrypt root files ───────────────────────
            if decrypt_all or '__root__' in selected:
                if self._check_stop_pause():
                    raise InterruptedError('Stopped')
                self.after(0, lambda: self.status_var.set(
                    '📂  Decrypting root files…'))
                kobackupdec.decrypt_files_in_root(
                    decrypt_info, files_folder, dest_path, expand)
            else:
                logging.info('Skipping root files (not selected)')

            # ── Phase 4: decrypt sub-folders one by one ───────────
            all_folders = [e for e in files_folder.glob('*') if e.is_dir()]
            folders = [e for e in all_folders
                       if decrypt_all or e.name in selected]
            skipped = len(all_folders) - len(folders)
            if skipped:
                logging.info('Skipping %d unselected folder(s)', skipped)

            for idx, entry in enumerate(folders, 1):
                if self._check_stop_pause():
                    raise InterruptedError('Stopped')
                self.after(0, lambda n=entry.name, i=idx, t=len(folders):
                    self.status_var.set(
                        f'📂  Folder {i}/{t}: {n}'))
                kobackupdec.decrypt_files_in_folder(
                    decrypt_info, entry, dest_path, expand)

            # ── Phase 5: media ────────────────────────────────────
            if bkp_path.joinpath('media').is_dir() and \
                    (decrypt_all or '__media__' in selected):
                if self._check_stop_pause():
                    raise InterruptedError('Stopped')
                self.after(0, lambda: self.status_var.set(
                    '🎬  Decrypting media…'))
                kobackupdec.decrypt_media(
                    password, bkp_path.joinpath('media'),
                    dest_path, expand)
            elif bkp_path.joinpath('media').is_dir():
                logging.info('Skipping media folder (not selected)')

            # ── Phase 6: permissions ──────────────────────────────
            if self._check_stop_pause():
                raise InterruptedError('Stopped')
            if writable:
                logging.info('Not setting read-only on decrypted files')
            else:
                self.after(0, lambda: self.status_var.set(
                    '🔒  Setting permissions…'))
                for fentry in dest_path.glob('**/*'):
                    if self._stop_event.is_set():
                        raise InterruptedError('Stopped')
                    if os.path.isfile(fentry):
                        os.chmod(fentry, 0o444)
                    elif os.path.isdir(fentry):
                        os.chmod(fentry, 0o555)

            success = True

        except InterruptedError:
            stopped = True
            logging.warning('Decryption stopped by user.')
        except Exception as exc:
            logging.critical('Decryption failed: %s', exc)
            self._log_queue.put(f'CRITICAL: {exc}')

        self.after(0, lambda: self._decrypt_done(success, stopped))

    def _decrypt_done(self, success: bool, stopped: bool = False):
        self._running = False
        self.progress.stop()
        self._set_controls_running(False)
        self.open_output_btn.configure(state="disabled")

        if stopped:
            self.status_var.set('⏹  Decryption stopped by user')
            self._append_log('')
            self._append_log('WARNING: ⏹  Decryption was stopped by the user.')
        elif success:
            self.open_output_btn.configure(state="normal")
            self.status_var.set('✅  Decryption completed successfully!')
            self._append_log('')
            self._append_log('=' * 50)
            self._append_log('INFO: ✅  Decryption completed successfully!')
            self._append_log('=' * 50)
            messagebox.showinfo('Success',
                                'Backup has been decrypted successfully!\n\n'
                                f'Output: {self.dest_var.get()}')
        else:
            self.status_var.set('❌  Decryption failed — see log for details')
            messagebox.showerror('Error',
                                 'Decryption failed.\n'
                                 'Check the log output for details.')

    # -----------------------------------------------------------------
    #  New Utilities
    # -----------------------------------------------------------------

    def _on_drop(self, event, var, tag):
        path = event.data
        if path.startswith('{') and path.endswith('}'):
            path = path[1:-1]
        var.set(path)
        if tag == "backup":
            self._scan_backup_folders()

    def _export_log(self):
        log_content = self.log_text.get("1.0", "end-1c")
        if not log_content.strip():
            messagebox.showinfo("Export Log", "The log is empty.")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Log Output"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(log_content)
                messagebox.showinfo("Success", "Log exported successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save log:\n{e}")

    def _open_output_folder(self):
        path = self.dest_var.get().strip()
        if os.path.isdir(path):
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])

    def _get_config_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

    def _load_config(self):
        config_path = self._get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "backup_path" in data:
                        self.backup_var.set(data["backup_path"])
                        self._scan_backup_folders()
                    if "dest_path" in data:
                        self.dest_var.set(data["dest_path"])
                    if "expandtar" in data:
                        self.expandtar_var.set(data["expandtar"])
                    if "writable" in data:
                        self.writable_var.set(data["writable"])
                    if "verbose" in data:
                        self.verbose_var.set(data["verbose"])
            except Exception as e:
                logging.error(f"Failed to load config: {e}")

    def _save_config(self):
        config_path = self._get_config_path()
        data = {
            "backup_path": self.backup_var.get(),
            "dest_path": self.dest_var.get(),
            "expandtar": self.expandtar_var.get(),
            "writable": self.writable_var.get(),
            "verbose": self.verbose_var.get()
        }
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save config: {e}")

    def _on_closing(self):
        self._save_config()
        self.destroy()

# ---------------------------------------------------------------------------
#  Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Ensure the script's own directory is on the path so we can import kobackupdec
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    app = KoBackupDecGUI()
    app.mainloop()
