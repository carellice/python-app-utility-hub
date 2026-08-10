"""Tkinter user interface for Video Track & Subtitle Editor."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import uuid

from media_engine import (
    ExportProcess,
    FFmpegTools,
    MediaError,
    MediaInfo,
    Track,
    build_ffmpeg_command,
    probe_media,
    remove_original,
    video_summary,
)


APP_NAME = "Video Track & Subtitle Editor"
VIDEO_TYPES = [
    ("Filmati", "*.mkv *.mp4 *.mov *.m4v *.avi *.webm *.ts *.m2ts"),
    ("Tutti i file", "*.*"),
]
AUDIO_TYPES = [
    ("File audio", "*.mka *.mp3 *.m4a *.aac *.flac *.wav *.ogg *.opus *.ac3 *.eac3 *.dts"),
    ("Contenitori multimediali", "*.mkv *.mp4 *.mov *.webm"),
    ("Tutti i file", "*.*"),
]
SUBTITLE_TYPES = [
    ("Sottotitoli", "*.srt *.ass *.ssa *.vtt *.sub *.sup"),
    ("Contenitori multimediali", "*.mks *.mkv *.mp4"),
    ("Tutti i file", "*.*"),
]


@dataclass(frozen=True)
class ExportOutcome:
    output: Path
    cleanup_mode: str | None = None
    cleanup_succeeded: bool = False
    cleanup_error: str = ""


class TrackDialog(tk.Toplevel):
    """Modal editor for track metadata and dispositions."""

    def __init__(self, parent: tk.Misc, track: Track) -> None:
        super().__init__(parent)
        self.track = track
        self.result: dict[str, object] | None = None
        self.title("Dettagli traccia")
        self.resizable(False, False)
        self.transient(parent)
        self.configure(background="#ffffff")

        frame = ttk.Frame(self, style="Card.TFrame", padding=20)
        frame.grid(sticky="nsew")
        ttk.Label(frame, text="Lingua", style="Field.TLabel").grid(row=0, column=0, sticky="w")
        self.language = tk.StringVar(value=track.language)
        language_entry = ttk.Entry(frame, textvariable=self.language, width=34)
        language_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 12))
        ttk.Label(
            frame,
            text="Codice ISO 639, ad esempio ita, eng, fra o und",
            style="Hint.TLabel",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 14))

        ttk.Label(frame, text="Titolo", style="Field.TLabel").grid(row=3, column=0, sticky="w")
        self.track_title = tk.StringVar(value=track.title)
        ttk.Entry(frame, textvariable=self.track_title, width=44).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(4, 14)
        )

        self.is_default = tk.BooleanVar(value=track.default)
        self.is_forced = tk.BooleanVar(value=track.forced)
        ttk.Checkbutton(frame, text="Traccia predefinita", variable=self.is_default).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=2
        )
        ttk.Checkbutton(frame, text="Traccia forzata", variable=self.is_forced).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=2
        )

        buttons = ttk.Frame(frame, style="Card.TFrame")
        buttons.grid(row=7, column=0, columnspan=2, sticky="e", pady=(22, 0))
        ttk.Button(buttons, text="Annulla", command=self.destroy).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Salva", style="Accent.TButton", command=self._save).pack(side="left")

        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Return>", lambda _event: self._save())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.grab_set()
        language_entry.focus_set()
        self.update_idletasks()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - self.winfo_width()) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - self.winfo_height()) // 2)
        self.geometry(f"+{x}+{y}")

    def _save(self) -> None:
        language = self.language.get().strip() or "und"
        if any(character.isspace() for character in language) or len(language) > 12:
            messagebox.showwarning(
                "Lingua non valida",
                "Inserisci un codice lingua breve, per esempio ita, eng o und.",
                parent=self,
            )
            return
        self.result = {
            "language": language,
            "title": self.track_title.get().strip(),
            "default": self.is_default.get(),
            "forced": self.is_forced.get(),
        }
        self.destroy()


class TrackEditorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1120x720")
        self.minsize(900, 620)
        self.option_add("*tearOff", False)

        self.tools: FFmpegTools | None = None
        self.media: MediaInfo | None = None
        self.tracks: list[Track] = []
        self.export_process: ExportProcess | None = None
        self.export_thread: threading.Thread | None = None
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.last_output: Path | None = None
        self.busy = False
        self.progress_has_value = False
        self.export_can_cancel = False

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.file_heading = tk.StringVar(value="Nessun filmato selezionato")
        self.file_details = tk.StringVar(value="Apri un filmato per visualizzare le tracce disponibili.")
        self.selection_summary = tk.StringVar(value="0 tracce audio · 0 sottotitoli")
        self.status_text = tk.StringVar(value="Ricerca di FFmpeg…")
        self.progress_value = tk.DoubleVar(value=0)
        self.progress_text = tk.StringVar(value="Pronto")
        self.delete_original = tk.BooleanVar(value=False)
        self.cleanup_mode = tk.StringVar(value="Cestino — consigliato")
        self.cleanup_hint = tk.StringVar(
            value="L'originale verrà conservato. Questa scelta non modifica mai il file durante l'esportazione."
        )

        self._configure_style()
        self._build_ui()
        self.after(50, self._discover_tools)
        self.after(100, self._poll_events)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        available = style.theme_names()
        # Aqua follows macOS dark mode and can combine dark native controls with
        # our light cards.  Clam is fully colourable and therefore gives the same
        # legible light appearance in both system modes.
        if "clam" in available:
            style.theme_use("clam")

        background = "#f4f6f8"
        card = "#ffffff"
        text = "#17212b"
        muted = "#637083"
        accent = "#1677ff"
        disabled_text = "#9aa4b2"
        button = "#e8edf3"
        button_active = "#dbe4ee"
        self.configure(background=background)
        style.configure(".", background=background, foreground=text)
        style.configure("TFrame", background=background)
        style.configure("TLabel", background=background, foreground=text)
        style.configure(
            "TButton",
            background=button,
            foreground=text,
            bordercolor="#c8d0da",
            lightcolor=button,
            darkcolor=button,
            padding=(11, 6),
            relief="flat",
        )
        style.map(
            "TButton",
            background=[("disabled", "#f0f2f5"), ("pressed", "#ced9e5"), ("active", button_active)],
            foreground=[("disabled", disabled_text), ("!disabled", text)],
            bordercolor=[("disabled", "#e4e7eb"), ("!disabled", "#c8d0da")],
        )
        style.configure(
            "TEntry",
            fieldbackground="#ffffff",
            foreground=text,
            insertcolor=text,
            bordercolor="#c8d0da",
            lightcolor="#c8d0da",
            darkcolor="#c8d0da",
            padding=7,
        )
        style.map(
            "TEntry",
            fieldbackground=[("disabled", "#f1f3f5"), ("!disabled", "#ffffff")],
            foreground=[("disabled", disabled_text), ("!disabled", text)],
        )
        style.configure("TCheckbutton", background=card, foreground=text)
        style.map(
            "TCheckbutton",
            background=[("active", card), ("!active", card)],
            foreground=[("disabled", disabled_text), ("!disabled", text)],
        )
        style.configure("App.TFrame", background=background)
        style.configure("Card.TFrame", background=card)
        style.configure("Header.TLabel", background=background, foreground=text, font=("TkDefaultFont", 22, "bold"))
        style.configure("Subheader.TLabel", background=background, foreground=muted, font=("TkDefaultFont", 11))
        style.configure("CardTitle.TLabel", background=card, foreground=text, font=("TkDefaultFont", 13, "bold"))
        style.configure("CardText.TLabel", background=card, foreground=text, font=("TkDefaultFont", 11))
        style.configure("Hint.TLabel", background=card, foreground=muted, font=("TkDefaultFont", 10))
        style.configure("Field.TLabel", background=card, foreground=text, font=("TkDefaultFont", 10, "bold"))
        style.configure("Pill.TLabel", background="#e9f2ff", foreground="#0b63ce", padding=(8, 4))
        style.configure("BusyPill.TLabel", background="#fff0d6", foreground="#9a5b00", padding=(8, 4))
        style.configure("BusyText.TLabel", background=card, foreground="#9a5b00", font=("TkDefaultFont", 10, "bold"))
        style.configure("Danger.TLabel", background=card, foreground="#b42318", font=("TkDefaultFont", 10, "bold"))
        style.configure("Progress.TLabel", background=card, foreground=text, font=("TkDefaultFont", 10, "bold"))
        style.configure(
            "Accent.TButton",
            background=accent,
            foreground="#ffffff",
            bordercolor=accent,
            lightcolor=accent,
            darkcolor=accent,
            font=("TkDefaultFont", 11, "bold"),
            padding=(16, 8),
        )
        style.map(
            "Accent.TButton",
            background=[("disabled", "#cbd4df"), ("pressed", "#075fc7"), ("active", "#0f6fdf")],
            foreground=[("disabled", "#f6f7f9"), ("!disabled", "#ffffff")],
            bordercolor=[("disabled", "#cbd4df"), ("!disabled", accent)],
        )
        style.configure("Toolbar.TButton", padding=(10, 5))
        style.configure(
            "TCombobox",
            fieldbackground="#ffffff",
            background=button,
            foreground=text,
            arrowcolor=text,
            bordercolor="#c8d0da",
            lightcolor="#c8d0da",
            darkcolor="#c8d0da",
            padding=6,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("disabled", "#f1f3f5"), ("readonly", "#ffffff")],
            foreground=[("disabled", disabled_text), ("readonly", text)],
            arrowcolor=[("disabled", disabled_text), ("!disabled", text)],
        )
        style.configure(
            "Track.Treeview",
            background=card,
            fieldbackground=card,
            foreground=text,
            rowheight=34,
            borderwidth=0,
            font=("TkDefaultFont", 10),
        )
        style.configure(
            "Track.Treeview.Heading",
            background="#e9edf2",
            foreground=text,
            font=("TkDefaultFont", 10, "bold"),
            padding=(6, 8),
        )
        style.map(
            "Track.Treeview",
            background=[("disabled", "#f1f3f5"), ("selected", "#dcecff")],
            foreground=[("disabled", disabled_text), ("selected", text)],
        )
        style.map(
            "Track.Treeview.Heading",
            background=[("active", "#dfe5ec"), ("!active", "#e9edf2")],
            foreground=[("!disabled", text)],
        )
        style.configure(
            "Card.Horizontal.TProgressbar",
            troughcolor="#e4e9ef",
            background=accent,
            bordercolor="#e4e9ef",
            lightcolor=accent,
            darkcolor=accent,
            thickness=13,
        )

    def _build_ui(self) -> None:
        root = ttk.Frame(self, style="App.TFrame", padding=(28, 22, 28, 22))
        root.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        header = ttk.Frame(root, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=APP_NAME, style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Aggiungi o rimuovi audio e sottotitoli senza ricodificare il video.",
            style="Subheader.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))
        self.status_badge = ttk.Label(header, textvariable=self.status_text, style="Pill.TLabel")
        self.status_badge.grid(row=0, column=1, rowspan=2, sticky="e")

        source_card = ttk.Frame(root, style="Card.TFrame", padding=18)
        source_card.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        source_card.columnconfigure(0, weight=1)
        ttk.Label(source_card, textvariable=self.file_heading, style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(source_card, textvariable=self.file_details, style="Hint.TLabel").grid(
            row=1, column=0, sticky="w", pady=(5, 0)
        )
        self.open_button = ttk.Button(
            source_card, text="Apri filmato…", style="Accent.TButton", command=self._choose_input
        )
        self.open_button.grid(row=0, column=1, rowspan=2, sticky="e", padx=(18, 0))

        tracks_card = ttk.Frame(root, style="Card.TFrame", padding=18)
        tracks_card.grid(row=2, column=0, sticky="nsew", pady=(0, 14))
        tracks_card.columnconfigure(0, weight=1)
        tracks_card.rowconfigure(2, weight=1)

        track_header = ttk.Frame(tracks_card, style="Card.TFrame")
        track_header.grid(row=0, column=0, sticky="ew")
        track_header.columnconfigure(0, weight=1)
        ttk.Label(track_header, text="Tracce audio e sottotitoli", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(track_header, textvariable=self.selection_summary, style="Hint.TLabel").grid(
            row=0, column=1, sticky="e"
        )

        toolbar = ttk.Frame(tracks_card, style="Card.TFrame")
        toolbar.grid(row=1, column=0, sticky="ew", pady=(12, 10))
        self.add_audio_button = ttk.Button(
            toolbar, text="＋ Audio", style="Toolbar.TButton", command=lambda: self._add_tracks("audio")
        )
        self.add_audio_button.pack(side="left", padx=(0, 7))
        self.add_subtitle_button = ttk.Button(
            toolbar, text="＋ Sottotitoli", style="Toolbar.TButton", command=lambda: self._add_tracks("subtitle")
        )
        self.add_subtitle_button.pack(side="left", padx=(0, 7))
        self.toggle_button = ttk.Button(
            toolbar, text="Includi / escludi", style="Toolbar.TButton", command=self._toggle_selected
        )
        self.toggle_button.pack(side="left", padx=(0, 7))
        self.edit_button = ttk.Button(
            toolbar, text="Modifica dettagli…", style="Toolbar.TButton", command=self._edit_selected
        )
        self.edit_button.pack(side="left", padx=(0, 7))
        self.remove_button = ttk.Button(
            toolbar, text="Rimuovi", style="Toolbar.TButton", command=self._remove_selected
        )
        self.remove_button.pack(side="left")
        self.down_button = ttk.Button(toolbar, text="↓", width=3, command=lambda: self._move_selected(1))
        self.down_button.pack(side="right", padx=(5, 0))
        self.up_button = ttk.Button(toolbar, text="↑", width=3, command=lambda: self._move_selected(-1))
        self.up_button.pack(side="right")

        table_frame = ttk.Frame(tracks_card, style="Card.TFrame")
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        columns = ("keep", "type", "language", "title", "details", "flags", "source")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="Track.Treeview",
            selectmode="browse",
        )
        headings = {
            "keep": "Usa",
            "type": "Tipo",
            "language": "Lingua",
            "title": "Titolo",
            "details": "Codec / dettagli",
            "flags": "Flag",
            "source": "Origine",
        }
        widths = {"keep": 54, "type": 105, "language": 72, "title": 190, "details": 180, "flags": 115, "source": 160}
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], minwidth=50, stretch=column in {"title", "details", "source"})
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.tag_configure("excluded", foreground="#929ba8")
        self.tree.tag_configure("external", foreground="#0b63ce")
        self.tree.bind("<Double-1>", lambda _event: self._toggle_selected())
        self.tree.bind("<space>", lambda _event: self._toggle_selected())
        self.tree.bind("<Return>", lambda _event: self._edit_selected())

        output_card = ttk.Frame(root, style="Card.TFrame", padding=18)
        output_card.grid(row=3, column=0, sticky="ew")
        output_card.columnconfigure(0, weight=1)
        ttk.Label(output_card, text="File di destinazione", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w"
        )
        self.output_entry = ttk.Entry(output_card, textvariable=self.output_path)
        self.output_entry.grid(row=1, column=0, sticky="ew", pady=(9, 0))
        self.output_browse = ttk.Button(output_card, text="Scegli…", command=self._choose_output)
        self.output_browse.grid(row=1, column=1, padx=(8, 12), pady=(9, 0))
        self.export_button = ttk.Button(
            output_card, text="Esporta senza ricodifica", style="Accent.TButton", command=self._start_export
        )
        self.export_button.grid(row=1, column=2, pady=(9, 0))

        progress_frame = ttk.Frame(output_card, style="Card.TFrame")
        progress_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(13, 0))
        progress_frame.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(
            progress_frame,
            variable=self.progress_value,
            maximum=100,
            mode="determinate",
            style="Card.Horizontal.TProgressbar",
        )
        self.progress.grid(row=0, column=0, sticky="ew")
        ttk.Label(progress_frame, textvariable=self.progress_text, style="Progress.TLabel", width=14, anchor="e").grid(
            row=0, column=1, sticky="e", padx=(12, 0)
        )
        self.output_hint = tk.StringVar(value="Il video verrà copiato bit per bit, senza perdita di qualità.")
        self.output_hint_label = ttk.Label(output_card, textvariable=self.output_hint, style="Hint.TLabel")
        self.output_hint_label.grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(5, 0)
        )
        self.cancel_button = ttk.Button(output_card, text="Annulla", command=self._cancel_export)
        self.cancel_button.grid(row=2, column=2, rowspan=2, sticky="e", pady=(10, 0))

        cleanup_separator = ttk.Separator(output_card, orient="horizontal")
        cleanup_separator.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(14, 11))
        cleanup_frame = ttk.Frame(output_card, style="Card.TFrame")
        cleanup_frame.grid(row=5, column=0, columnspan=3, sticky="ew")
        cleanup_frame.columnconfigure(2, weight=1)
        self.cleanup_check = ttk.Checkbutton(
            cleanup_frame,
            text="Rimuovi il file originale dopo un'esportazione riuscita",
            variable=self.delete_original,
            command=self._sync_cleanup_controls,
        )
        self.cleanup_check.grid(row=0, column=0, sticky="w")
        ttk.Label(cleanup_frame, text="Modalità:", style="CardText.TLabel").grid(
            row=0, column=1, sticky="e", padx=(24, 7)
        )
        self.cleanup_mode_combo = ttk.Combobox(
            cleanup_frame,
            textvariable=self.cleanup_mode,
            values=("Cestino — consigliato", "Elimina definitivamente"),
            state="readonly",
            width=25,
        )
        self.cleanup_mode_combo.grid(row=0, column=2, sticky="e")
        self.cleanup_mode_combo.bind("<<ComboboxSelected>>", lambda _event: self._sync_cleanup_controls())
        self.cleanup_mode_combo.current(0)
        self.cleanup_hint_label = ttk.Label(cleanup_frame, textvariable=self.cleanup_hint, style="Hint.TLabel")
        self.cleanup_hint_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(5, 0))

        self._set_media_controls(False)
        self.cancel_button.state(["disabled"])

    def _discover_tools(self) -> None:
        try:
            self.tools = FFmpegTools.discover()
        except MediaError as exc:
            self.status_text.set("FFmpeg mancante")
            self.open_button.state(["disabled"])
            messagebox.showerror("FFmpeg necessario", str(exc), parent=self)
        else:
            self.status_text.set("FFmpeg pronto · copia diretta")

    def _set_media_controls(self, enabled: bool) -> None:
        state = ["!disabled"] if enabled else ["disabled"]
        for widget in (
            self.add_audio_button,
            self.add_subtitle_button,
            self.toggle_button,
            self.edit_button,
            self.remove_button,
            self.up_button,
            self.down_button,
            self.output_entry,
            self.output_browse,
            self.export_button,
            self.cleanup_check,
        ):
            widget.state(state)
        self._sync_cleanup_controls()

    def _selected_cleanup_mode(self) -> str:
        return "permanent" if self.cleanup_mode_combo.current() == 1 else "trash"

    def _sync_cleanup_controls(self) -> None:
        can_choose = bool(self.media and not self.busy and self.delete_original.get())
        if can_choose:
            self.cleanup_mode_combo.state(["!disabled", "readonly"])
        else:
            self.cleanup_mode_combo.state(["disabled"])

        if not self.delete_original.get():
            self.cleanup_hint.set(
                "L'originale verrà conservato. Questa scelta non modifica mai il file durante l'esportazione."
            )
            self.cleanup_hint_label.configure(style="Hint.TLabel")
        elif self._selected_cleanup_mode() == "permanent":
            self.cleanup_hint.set(
                "Attenzione: dopo la conferma il file originale non potrà essere recuperato."
            )
            self.cleanup_hint_label.configure(style="Danger.TLabel")
        else:
            self.cleanup_hint.set(
                "L'originale sarà spostato nel Cestino soltanto dopo la creazione corretta del nuovo file."
            )
            self.cleanup_hint_label.configure(style="Hint.TLabel")

    def _choose_input(self) -> None:
        if self.busy:
            return
        path = filedialog.askopenfilename(title="Scegli un filmato", filetypes=VIDEO_TYPES, parent=self)
        if path:
            self._load_input(Path(path))

    def _load_input(self, path: Path) -> None:
        if not self.tools or self.busy:
            return
        self.status_text.set("Analisi del filmato…")
        self.open_button.state(["disabled"])
        self.update_idletasks()
        try:
            media = probe_media(path, self.tools)
        except MediaError as exc:
            messagebox.showerror("Filmato non leggibile", str(exc), parent=self)
            self.status_text.set("FFmpeg pronto · copia diretta")
            self.open_button.state(["!disabled"])
            return
        if not media.video_streams:
            messagebox.showwarning("Nessun video", "Il file selezionato non contiene una traccia video.", parent=self)
            self.status_text.set("FFmpeg pronto · copia diretta")
            self.open_button.state(["!disabled"])
            return
        self.media = media
        self.tracks = list(media.tracks)
        self.input_path.set(str(path))
        self.file_heading.set(path.name)
        self.file_details.set(video_summary(media))
        self.output_path.set(str(path.with_name(f"{path.stem}_tracce.mkv")))
        self.progress_value.set(0)
        self.progress_text.set("Pronto")
        self.delete_original.set(False)
        self.cleanup_mode_combo.current(0)
        self._sync_cleanup_controls()
        self.output_hint.set("Il video verrà copiato bit per bit, senza perdita di qualità.")
        self._refresh_tree()
        self._set_media_controls(True)
        self.open_button.state(["!disabled"])
        self.status_text.set("FFmpeg pronto · copia diretta")

    def _add_tracks(self, kind: str) -> None:
        if not self.media or not self.tools or self.busy:
            return
        paths = filedialog.askopenfilenames(
            title="Aggiungi audio" if kind == "audio" else "Aggiungi sottotitoli",
            filetypes=AUDIO_TYPES if kind == "audio" else SUBTITLE_TYPES,
            parent=self,
        )
        if not paths:
            return
        added: list[Track] = []
        errors: list[str] = []
        self.status_text.set("Analisi delle nuove tracce…")
        self.update_idletasks()
        for raw_path in paths:
            path = Path(raw_path)
            try:
                info = probe_media(path, self.tools, external=True)
            except MediaError as exc:
                errors.append(str(exc))
                continue
            matches = [track for track in info.tracks if track.kind == kind]
            if not matches:
                errors.append(f"“{path.name}” non contiene {'audio' if kind == 'audio' else 'sottotitoli'}.")
                continue
            existing_uids = {track.uid for track in self.tracks}
            for track in matches:
                if track.uid in existing_uids:
                    continue
                track.default = False
                added.append(track)
                existing_uids.add(track.uid)
        self.tracks.extend(added)
        self._refresh_tree(select_uid=added[0].uid if added else None)
        self.status_text.set("FFmpeg pronto · copia diretta")
        if errors:
            messagebox.showwarning("Alcuni file non sono stati aggiunti", "\n\n".join(errors), parent=self)
        elif added:
            self.output_hint.set(f"Aggiunte {len(added)} tracce. Verranno copiate senza ricodifica.")

    def _selected_track(self) -> Track | None:
        selection = self.tree.selection()
        if not selection:
            return None
        uid = selection[0]
        return next((track for track in self.tracks if track.uid == uid), None)

    def _toggle_selected(self) -> None:
        if self.busy:
            return
        track = self._selected_track()
        if not track:
            return
        track.selected = not track.selected
        self._refresh_tree(select_uid=track.uid)

    def _remove_selected(self) -> None:
        if self.busy:
            return
        track = self._selected_track()
        if not track:
            return
        if track.external:
            self.tracks.remove(track)
            self._refresh_tree()
            self.output_hint.set("La traccia aggiunta è stata rimossa dal progetto.")
        else:
            track.selected = False
            self._refresh_tree(select_uid=track.uid)
            self.output_hint.set("La traccia sarà esclusa dal nuovo file; l'originale non verrà modificato.")

    def _edit_selected(self) -> None:
        if self.busy:
            return
        track = self._selected_track()
        if not track:
            return
        dialog = TrackDialog(self, track)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        track.language = str(dialog.result["language"])
        track.title = str(dialog.result["title"])
        track.forced = bool(dialog.result["forced"])
        wants_default = bool(dialog.result["default"])
        if wants_default:
            for other in self.tracks:
                if other.kind == track.kind:
                    other.default = other is track
        else:
            track.default = False
        self._refresh_tree(select_uid=track.uid)

    def _move_selected(self, delta: int) -> None:
        if self.busy:
            return
        track = self._selected_track()
        if not track:
            return
        same_kind = [item for item in self.tracks if item.kind == track.kind]
        kind_index = same_kind.index(track)
        target_kind_index = kind_index + delta
        if not 0 <= target_kind_index < len(same_kind):
            return
        other = same_kind[target_kind_index]
        first, second = self.tracks.index(track), self.tracks.index(other)
        self.tracks[first], self.tracks[second] = self.tracks[second], self.tracks[first]
        self._refresh_tree(select_uid=track.uid)

    def _refresh_tree(self, select_uid: str | None = None) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for track in self.tracks:
            flags: list[str] = []
            if track.default:
                flags.append("predefinita")
            if track.forced:
                flags.append("forzata")
            tag = "excluded" if not track.selected else "external" if track.external else ""
            self.tree.insert(
                "",
                "end",
                iid=track.uid,
                values=(
                    "✓" if track.selected else "—",
                    "Audio" if track.kind == "audio" else "Sottotitoli",
                    track.language,
                    track.title or "—",
                    track.details,
                    ", ".join(flags) or "—",
                    track.source_path.name if track.external else "Filmato originale",
                ),
                tags=(tag,) if tag else (),
            )
        if select_uid and self.tree.exists(select_uid):
            self.tree.selection_set(select_uid)
            self.tree.focus(select_uid)
            self.tree.see(select_uid)
        audio = sum(track.selected and track.kind == "audio" for track in self.tracks)
        subtitles = sum(track.selected and track.kind == "subtitle" for track in self.tracks)
        self.selection_summary.set(f"{audio} audio incluse · {subtitles} sottotitoli inclusi")

    def _choose_output(self) -> None:
        if not self.media or self.busy:
            return
        initial = Path(self.output_path.get()) if self.output_path.get() else self.media.path.with_suffix(".mkv")
        path = filedialog.asksaveasfilename(
            title="Salva il nuovo filmato",
            initialdir=str(initial.parent),
            initialfile=initial.name,
            defaultextension=".mkv",
            filetypes=[
                ("Matroska — consigliato", "*.mkv"),
                ("MPEG-4", "*.mp4"),
                ("QuickTime", "*.mov"),
                ("Tutti i file", "*.*"),
            ],
            parent=self,
        )
        if path:
            self.output_path.set(path)

    def _validate_export(self) -> tuple[Path, Path] | None:
        if not self.media or not self.tools:
            return None
        source = self.media.path.absolute()
        raw_output = self.output_path.get().strip()
        if not raw_output:
            messagebox.showwarning("Destinazione mancante", "Scegli dove salvare il nuovo filmato.", parent=self)
            return None
        output = Path(raw_output).expanduser()
        if not output.suffix:
            output = output.with_suffix(".mkv")
            self.output_path.set(str(output))
        try:
            if output.resolve() == source.resolve():
                messagebox.showwarning(
                    "Scegli un altro nome",
                    "Il filmato originale non verrà sovrascritto. Scegli un nome diverso.",
                    parent=self,
                )
                return None
        except OSError:
            pass
        if not output.parent.exists():
            messagebox.showwarning("Cartella inesistente", "La cartella di destinazione non esiste.", parent=self)
            return None
        if output.suffix.lower() not in {".mkv", ".mp4", ".mov", ".m4v", ".webm"}:
            if not messagebox.askyesno(
                "Contenitore insolito",
                "L'estensione scelta potrebbe non supportare le tracce selezionate. Continuare comunque?",
                parent=self,
            ):
                return None
        elif output.suffix.lower() != ".mkv":
            if any(track.selected and track.kind == "subtitle" for track in self.tracks):
                if not messagebox.askyesno(
                    "Compatibilità del contenitore",
                    "MP4/MOV/WebM non supportano tutti i formati di sottotitoli. "
                    "MKV è consigliato per una copia senza conversioni.\n\nContinuare con il formato scelto?",
                    parent=self,
                ):
                    return None
        if output.exists() and not messagebox.askyesno(
            "Sostituire il file?", f"“{output.name}” esiste già. Vuoi sostituirlo?", parent=self
        ):
            return None
        return source, output

    def _start_export(self) -> None:
        if self.busy:
            return
        validated = self._validate_export()
        if not validated or not self.media or not self.tools:
            return
        source, output = validated
        cleanup_mode = self._selected_cleanup_mode() if self.delete_original.get() else None
        if cleanup_mode == "permanent":
            confirmed = messagebox.askyesno(
                "Eliminazione definitiva dell'originale",
                f"Dopo la creazione corretta di “{output.name}”, il file originale\n"
                f"“{source.name}” verrà eliminato DEFINITIVAMENTE.\n\n"
                "Non sarà possibile recuperarlo dal Cestino. Vuoi continuare?",
                icon="warning",
                parent=self,
            )
            if not confirmed:
                return
        elif cleanup_mode == "trash":
            confirmed = messagebox.askyesno(
                "Spostare l'originale nel Cestino?",
                f"Dopo la creazione corretta di “{output.name}”, il file originale\n"
                f"“{source.name}” verrà spostato nel Cestino.\n\nVuoi continuare?",
                parent=self,
            )
            if not confirmed:
                return
        temporary = output.with_name(f".{output.stem}.partial-{uuid.uuid4().hex[:8]}{output.suffix}")
        command = build_ffmpeg_command(self.tools, source, temporary, self.tracks)
        self.export_process = ExportProcess()
        self.export_can_cancel = True
        self.progress_value.set(0)
        self.progress_has_value = False
        self.progress_text.set("Avvio…")
        self.output_hint.set("Esportazione in corso — il filmato originale resta invariato.")
        self._set_busy(True)
        # Force Tk to paint the disabled controls and animated progress bar
        # before the worker starts returning events.
        self.update_idletasks()

        def worker() -> None:
            assert self.export_process is not None
            ok, error = self.export_process.run(
                command,
                self.media.duration,
                lambda progress: self.events.put(("progress", progress)),
            )
            if ok:
                self.export_can_cancel = False
                self.events.put(("finalizing", cleanup_mode))
                try:
                    os.replace(temporary, output)
                except OSError as exc:
                    self.events.put(("error", f"Il file è stato creato ma non può essere finalizzato:\n{exc}"))
                    return
                try:
                    if not output.is_file() or output.stat().st_size <= 0:
                        raise OSError("il file esportato è assente o vuoto")
                except OSError as exc:
                    self.events.put(("error", f"Il nuovo file non può essere verificato:\n{exc}"))
                    return

                cleanup_succeeded = False
                cleanup_error = ""
                if cleanup_mode:
                    try:
                        remove_original(source, cleanup_mode)
                    except (MediaError, OSError) as exc:
                        cleanup_error = str(exc)
                    else:
                        cleanup_succeeded = True
                self.events.put(
                    (
                        "done",
                        ExportOutcome(
                            output=output,
                            cleanup_mode=cleanup_mode,
                            cleanup_succeeded=cleanup_succeeded,
                            cleanup_error=cleanup_error,
                        ),
                    )
                )
            else:
                self.export_can_cancel = False
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
                self.events.put(("error", error))

        self.export_thread = threading.Thread(target=worker, name="ffmpeg-export", daemon=True)
        self.export_thread.start()

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        if busy:
            self._set_media_controls(False)
            self.open_button.state(["disabled"])
            self.cancel_button.state(["!disabled"])
            self.tree.state(["disabled"])
            self.status_badge.configure(style="BusyPill.TLabel")
            self.output_hint_label.configure(style="BusyText.TLabel")
            self.export_button.configure(text="Esportazione in corso…")
            self.progress.configure(mode="indeterminate")
            self.progress.start(10)
            self.status_text.set("● Esportazione in corso")
        else:
            self.export_can_cancel = False
            self.progress.stop()
            self.progress.configure(mode="determinate")
            self._set_media_controls(self.media is not None)
            self.open_button.state(["!disabled"])
            self.cancel_button.state(["disabled"])
            self.tree.state(["!disabled"])
            self.status_badge.configure(style="Pill.TLabel")
            self.output_hint_label.configure(style="Hint.TLabel")
            self.export_button.configure(text="Esporta senza ricodifica")
            self.status_text.set("FFmpeg pronto · copia diretta")
        self._sync_cleanup_controls()

    def _cancel_export(self) -> None:
        if self.export_process and self.export_can_cancel:
            self.output_hint.set("Annullamento in corso…")
            self.progress_text.set("Annullamento…")
            self.cancel_button.state(["disabled"])
            self.export_process.cancel()
        elif self.busy:
            self.output_hint.set("Finalizzazione già iniziata: attendi il completamento dell'operazione.")

    def _poll_events(self) -> None:
        last_progress: float | None = None
        terminal_event: tuple[str, object] | None = None
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == "progress":
                    if value is not None:
                        last_progress = float(value)
                elif event == "finalizing":
                    self._show_finalizing(str(value) if value else None)
                elif event in {"done", "error"}:
                    terminal_event = (event, value)
        except queue.Empty:
            pass

        if last_progress is not None:
            self._show_progress(last_progress)
        if terminal_event is not None:
            event, value = terminal_event
            if event == "done":
                assert isinstance(value, ExportOutcome)
                self.progress.stop()
                self.progress.configure(mode="determinate")
                self.progress_value.set(100)
                self.progress_text.set("100% · completato")
                self.output_hint.set("Esportazione terminata, finalizzazione del file…")
                self.after(180, lambda outcome=value: self._finish_success(outcome))
            else:
                self.progress.stop()
                self.after(120, lambda error=str(value): self._finish_error(error))
        self.after(100, self._poll_events)

    def _show_finalizing(self, cleanup_mode: str | None) -> None:
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress_value.set(100)
        self.cancel_button.state(["disabled"])
        self.progress_text.set("Finalizzazione…")
        if cleanup_mode == "permanent":
            self.status_text.set("Eliminazione dell'originale")
            self.output_hint.set("Nuovo file verificato · eliminazione definitiva dell'originale…")
        elif cleanup_mode == "trash":
            self.status_text.set("Spostamento nel Cestino")
            self.output_hint.set("Nuovo file verificato · spostamento dell'originale nel Cestino…")
        else:
            self.status_text.set("Finalizzazione del nuovo file")
            self.output_hint.set("Esportazione terminata · finalizzazione del nuovo file…")

    def _show_progress(self, progress: float) -> None:
        percentage = max(0.0, min(100.0, progress * 100))
        # Keep the animation visible while FFmpeg is still at its initial zero.
        if percentage < 1 and not self.progress_has_value:
            self.progress_text.set("Elaborazione…")
            return
        if not self.progress_has_value:
            self.progress.stop()
            self.progress.configure(mode="determinate")
            self.progress_has_value = True
        self.progress_value.set(percentage)
        self.progress_text.set(f"{percentage:.0f}%")

    def _finish_success(self, outcome: ExportOutcome) -> None:
        self.last_output = outcome.output
        self._set_busy(False)
        self.progress_value.set(100)
        self.progress_text.set("Completata")
        if outcome.cleanup_succeeded:
            if outcome.cleanup_mode == "permanent":
                cleanup_message = "Originale eliminato definitivamente."
            else:
                cleanup_message = "Originale spostato nel Cestino."
            self.output_hint.set(f"Completato: {outcome.output.name} · {cleanup_message}")
            # The selected source no longer exists at its original path. Keep the
            # result visible, but require opening a file before another export.
            self.media = None
            self.delete_original.set(False)
            self._set_media_controls(False)
            self.file_details.set(f"{cleanup_message} Il nuovo file è: {outcome.output}")
        elif outcome.cleanup_error:
            self.output_hint.set(f"Completato: {outcome.output.name} · originale conservato per errore.")
        else:
            self.output_hint.set(f"Completato: {outcome.output.name}")
        # Let Tk render the final state before opening the modal dialog.
        self.after(100, lambda: self._show_success_dialog(outcome))

    def _show_success_dialog(self, outcome: ExportOutcome) -> None:
        if outcome.cleanup_succeeded and outcome.cleanup_mode == "permanent":
            cleanup_text = "\n\nIl file originale è stato eliminato definitivamente."
        elif outcome.cleanup_succeeded:
            cleanup_text = "\n\nIl file originale è stato spostato nel Cestino."
        elif outcome.cleanup_error:
            cleanup_text = (
                "\n\nIl nuovo filmato è valido, ma non è stato possibile rimuovere l'originale. "
                f"L'originale è stato conservato.\n\nDettaglio: {outcome.cleanup_error}"
            )
        else:
            cleanup_text = ""
        if messagebox.askyesno(
            "Esportazione completata",
            f"Il nuovo filmato è pronto.{cleanup_text}\n\nVuoi mostrarlo nella cartella?",
            icon="warning" if outcome.cleanup_error else "info",
            parent=self,
        ):
            self._reveal_file(outcome.output)

    def _finish_error(self, error: str) -> None:
        self._set_busy(False)
        self.progress_value.set(0)
        if error == "Esportazione annullata.":
            self.progress_text.set("Annullata")
            self.output_hint.set("Esportazione annullata; nessun file incompleto è stato conservato.")
            return
        self.progress_text.set("Non riuscita")
        self.output_hint.set("Esportazione non completata.")
        self.after(
            100,
            lambda: messagebox.showerror(
                "Esportazione non riuscita",
                f"{error}\n\nSuggerimento: usa il formato MKV se le tracce non sono compatibili con MP4/MOV.",
                parent=self,
            ),
        )

    def _reveal_file(self, path: Path) -> None:
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", "-R", str(path)])
            elif sys.platform.startswith("win"):
                subprocess.Popen(["explorer", "/select,", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path.parent)])
        except OSError:
            messagebox.showinfo("File creato", str(path), parent=self)

    def _on_close(self) -> None:
        if self.export_thread and self.export_thread.is_alive():
            if not self.export_can_cancel:
                messagebox.showinfo(
                    "Finalizzazione in corso",
                    "Il nuovo file è già stato creato e la finalizzazione è in corso. "
                    "Attendi qualche istante prima di chiudere l'applicazione.",
                    parent=self,
                )
                return
            if not messagebox.askyesno(
                "Uscire?", "È in corso un'esportazione. Vuoi annullarla e uscire?", parent=self
            ):
                return
            if self.export_process:
                self.export_process.cancel()
        self.destroy()


def run() -> None:
    app = TrackEditorApp()
    app.mainloop()


if __name__ == "__main__":
    run()
