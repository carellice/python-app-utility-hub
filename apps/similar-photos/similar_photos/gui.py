from __future__ import annotations

import os
import platform
import queue
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageTk

from .core import (
    PhotoGroup,
    PhotoInfo,
    ScanResult,
    format_bytes,
    safe_move_to_trash,
    scan_folder,
)


COLORS = {
    "bg": "#fdf7ff",
    "surface": "#fffbfe",
    "surface_alt": "#f7f2fa",
    "surface_container": "#ece6f0",
    "primary": "#6750a4",
    "primary_hover": "#4f378b",
    "primary_container": "#eaddff",
    "on_primary_container": "#21005d",
    "secondary": "#006b5b",
    "secondary_container": "#9cf1dc",
    "on_secondary_container": "#002019",
    "tertiary": "#b3265c",
    "tertiary_container": "#ffd8e4",
    "on_tertiary_container": "#3f001d",
    "border": "#cac4d0",
    "text": "#1d1b20",
    "muted": "#625b71",
}


LANGUAGE_NAMES = {
    "it": "Italiano",
    "en": "English",
}

TRANSLATIONS = {
    "it": {
        "language": "Lingua",
        "scan": "Analizza",
        "choose_folder": "Scegli cartella",
        "recursive": "Sottocartelle",
        "similarity": "Somiglianza",
        "initial_status": "Scegli una cartella di fotografie.",
        "no_group_title": "Nessun gruppo selezionato",
        "intro_question": "Dopo l'analisi ti guiderò un gruppo alla volta.",
        "export_report": "Esporta report",
        "back": "Indietro",
        "next_group": "Prossimo gruppo",
        "finish_trash": "Fine: sposta nel Cestino",
        "keep_suggested": "Tieni solo la suggerita",
        "choose_folder_title": "Scegli la cartella con le fotografie",
        "missing_folder_title": "Cartella mancante",
        "missing_folder_msg": "Scegli prima una cartella da analizzare.",
        "invalid_folder_title": "Cartella non valida",
        "invalid_folder_msg": "La cartella scelta non esiste.",
        "scan_title": "Analisi in corso",
        "scan_question": "Sto cercando foto uguali e simili.",
        "scan_prepare": "Preparo la scansione...",
        "scan_stopped": "Analisi interrotta.",
        "error_title": "Errore",
        "scan_summary": "{photos} foto analizzate, {groups} gruppi trovati{skipped}",
        "scan_summary_skipped": ", {count} non leggibili.",
        "scan_summary_end": ".",
        "no_groups_found": "Nessun duplicato o gruppo simile trovato",
        "no_groups_question": "Non ho trovato gruppi da rivedere. Le foto uniche restano dove sono.",
        "group_title": "Gruppo {current} di {total}: foto {kind} ({count})",
        "group_question": "Quali vuoi conservare? Le foto senza spunta verranno spostate nel Cestino alla fine.",
        "kind_equal": "uguali",
        "kind_similar": "simili",
        "keep_this_photo": "Conserva questa foto",
        "suggested": "Suggerita",
        "open": "Apri",
        "reveal_finder": "Mostra nel Finder",
        "reveal_explorer": "Mostra in Explorer",
        "dimensions_unknown": "dimensioni n/d",
        "estimated_quality": "Qualità stimata",
        "preview_unavailable_title": "Anteprima non disponibile",
        "cannot_open_image": "Non posso aprire questa immagine:",
        "cannot_convert_image": "Non posso convertire in JPEG:",
        "fullscreen_hint": "Clic o Esc per chiudere",
        "no_keep_title": "Nessuna foto conservata",
        "no_keep_msg": "In questo gruppo non hai selezionato nessuna foto da conservare. Vuoi davvero mandarle tutte nel Cestino?",
        "incomplete_title": "Percorso incompleto",
        "incomplete_msg": "Rivedi tutti i gruppi prima di terminare.",
        "no_discard_title": "Nessuno scarto",
        "no_discard_msg": "Non ci sono foto marcate da spostare.",
        "trash_confirm_title": "Spostare nel Cestino?",
        "trash_confirm_msg": "Sposterò nel Cestino {count} foto non selezionate. Le foto selezionate resteranno nella cartella originale. Procedo?",
        "partial_move_title": "Spostamento parziale",
        "partial_move_msg": "Spostate nel Cestino {count} foto.",
        "done_title": "Fatto",
        "done_msg": "Spostate nel Cestino {count} foto.",
        "save_report_title": "Salva report",
        "text_file": "File di testo",
        "report_folder": "Cartella",
        "report_photos": "Foto analizzate",
        "report_groups": "Gruppi trovati",
        "report_group": "Gruppo",
        "report_suggested": "suggerita",
        "report_keep": "TIENI",
        "report_discard": "SCARTA",
        "report_saved_title": "Report salvato",
        "report_saved_msg": "Report salvato in:\n{target}",
        "threshold_low": "molto prudente: trova quasi solo foto uguali o quasi identiche.",
        "threshold_mid": "consigliato: trova duplicati e scatti molto simili senza esagerare.",
        "threshold_high": "più largo: può unire foto meno simili, utile dopo raffiche o scatti ripetuti.",
        "threshold_help": "Somiglianza {value}: {mode} Se trovi troppi gruppi strani, abbassala; se ne mancano, alzala.",
        "progress_converting": "Converto {name} in JPEG",
        "progress_conversion_done": "Conversione JPEG completata",
        "progress_reading": "Leggo {name}",
        "progress_grouping": "Raggruppo duplicati e immagini simili",
    },
    "en": {
        "language": "Language",
        "scan": "Scan",
        "choose_folder": "Choose folder",
        "recursive": "Subfolders",
        "similarity": "Similarity",
        "initial_status": "Choose a folder of photos.",
        "no_group_title": "No group selected",
        "intro_question": "After the scan I will guide you through one group at a time.",
        "export_report": "Export report",
        "back": "Back",
        "next_group": "Next group",
        "finish_trash": "Finish: move to Trash",
        "keep_suggested": "Keep suggested only",
        "choose_folder_title": "Choose the folder with your photos",
        "missing_folder_title": "Missing folder",
        "missing_folder_msg": "Choose a folder to scan first.",
        "invalid_folder_title": "Invalid folder",
        "invalid_folder_msg": "The selected folder does not exist.",
        "scan_title": "Scanning",
        "scan_question": "Looking for identical and similar photos.",
        "scan_prepare": "Preparing the scan...",
        "scan_stopped": "Scan stopped.",
        "error_title": "Error",
        "scan_summary": "{photos} photos scanned, {groups} groups found{skipped}",
        "scan_summary_skipped": ", {count} unreadable.",
        "scan_summary_end": ".",
        "no_groups_found": "No duplicates or similar groups found",
        "no_groups_question": "I did not find any groups to review. Unique photos stay where they are.",
        "group_title": "Group {current} of {total}: {kind} photos ({count})",
        "group_question": "Which ones do you want to keep? Unchecked photos will be moved to the Trash at the end.",
        "kind_equal": "identical",
        "kind_similar": "similar",
        "keep_this_photo": "Keep this photo",
        "suggested": "Suggested",
        "open": "Open",
        "reveal_finder": "Show in Finder",
        "reveal_explorer": "Show in Explorer",
        "dimensions_unknown": "size n/a",
        "estimated_quality": "Estimated quality",
        "preview_unavailable_title": "Preview unavailable",
        "cannot_open_image": "Cannot open this image:",
        "cannot_convert_image": "Cannot convert to JPEG:",
        "fullscreen_hint": "Click or Esc to close",
        "no_keep_title": "No photo kept",
        "no_keep_msg": "You have not selected any photo to keep in this group. Do you really want to move all of them to the Trash?",
        "incomplete_title": "Review incomplete",
        "incomplete_msg": "Review every group before finishing.",
        "no_discard_title": "Nothing to discard",
        "no_discard_msg": "There are no photos marked to move.",
        "trash_confirm_title": "Move to Trash?",
        "trash_confirm_msg": "I will move {count} unselected photos to the Trash. Selected photos will stay in the original folder. Continue?",
        "partial_move_title": "Partial move",
        "partial_move_msg": "{count} photos moved to the Trash.",
        "done_title": "Done",
        "done_msg": "{count} photos moved to the Trash.",
        "save_report_title": "Save report",
        "text_file": "Text file",
        "report_folder": "Folder",
        "report_photos": "Photos scanned",
        "report_groups": "Groups found",
        "report_group": "Group",
        "report_suggested": "suggested",
        "report_keep": "KEEP",
        "report_discard": "DISCARD",
        "report_saved_title": "Report saved",
        "report_saved_msg": "Report saved in:\n{target}",
        "threshold_low": "very cautious: finds almost only identical or nearly identical photos.",
        "threshold_mid": "recommended: finds duplicates and very similar shots without going too wide.",
        "threshold_high": "wider: can merge less similar photos, useful after bursts or repeated shots.",
        "threshold_help": "Similarity {value}: {mode} If you see too many odd groups, lower it; if groups are missing, raise it.",
        "progress_converting": "Converting {name} to JPEG",
        "progress_conversion_done": "JPEG conversion completed",
        "progress_reading": "Reading {name}",
        "progress_grouping": "Grouping duplicates and similar images",
    },
}


class SimilarPhotosApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Similar Photos")
        self.geometry("1180x760")
        self.minsize(980, 620)

        self.folder_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=True)
        self.threshold_var = tk.DoubleVar(value=8)
        self.threshold_label_var = tk.StringVar(value="8")
        self.language_code = "it"
        self.language_display_var = tk.StringVar(value=LANGUAGE_NAMES[self.language_code])
        self.status_var = tk.StringVar(value=self.t("initial_status"))
        self.progress_var = tk.DoubleVar(value=0)

        self.scan_result: ScanResult | None = None
        self.current_group: PhotoGroup | None = None
        self.current_group_index = 0
        self.visited_groups: set[int] = set()
        self.keep_vars: dict[Path, tk.BooleanVar] = {}
        self.preview_refs: list[ImageTk.PhotoImage] = []
        self.fullscreen_preview_ref: ImageTk.PhotoImage | None = None
        self.fullscreen_overlay: tk.Frame | None = None
        self.worker_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.is_scanning = False

        self._build_style()
        self._build_layout()
        self.after(100, self._drain_worker_queue)

    def t(self, key: str, **kwargs: object) -> str:
        text = TRANSLATIONS[self.language_code][key]
        return text.format(**kwargs) if kwargs else text

    def _language_changed(self, _event: tk.Event | None = None) -> None:
        selected = self.language_display_var.get()
        for code, name in LANGUAGE_NAMES.items():
            if name == selected:
                self.language_code = code
                break
        self._refresh_language()

    def _refresh_language(self) -> None:
        self.language_label.configure(text=self.t("language"))
        self.scan_button.configure(text=self.t("scan"))
        self.choose_folder_button.configure(text=self.t("choose_folder"))
        self.recursive_check.configure(text=self.t("recursive"))
        self.similarity_label.configure(text=self.t("similarity"))
        self.export_report_button.configure(text=self.t("export_report"))
        self.back_button.configure(text=self.t("back"))
        self.next_button.configure(text=self.t("next_group"))
        self.keep_suggested_button.configure(text=self.t("keep_suggested"))
        self.threshold_help_var.set(self._threshold_help_text())

        if self.current_group is not None:
            self.show_group(self.current_group)
            self._update_navigation()
            if self.scan_result is not None:
                self.status_var.set(self._scan_summary_text(self.scan_result))
        elif self.is_scanning:
            self.group_title_var.set(self.t("scan_title"))
            self.group_question_var.set(self.t("scan_question"))
        elif self.scan_result is not None and not self.scan_result.groups:
            self.group_title_var.set(self.t("no_groups_found"))
            self.group_question_var.set(self.t("no_groups_question"))
            self.status_var.set(self._scan_summary_text(self.scan_result))
        else:
            self.group_title_var.set(self.t("no_group_title"))
            self.group_question_var.set(self.t("intro_question"))
            self.status_var.set(self.t("initial_status"))

    def _group_kind_label(self, kind: str) -> str:
        return self.t("kind_equal") if kind == "uguali" else self.t("kind_similar")

    def _translate_progress_message(self, message: str) -> str:
        if self.language_code == "it":
            return message
        if message.startswith("Converto ") and message.endswith(" in JPEG"):
            return self.t("progress_converting", name=message.removeprefix("Converto ").removesuffix(" in JPEG"))
        if message == "Conversione JPEG completata":
            return self.t("progress_conversion_done")
        if message.startswith("Leggo "):
            return self.t("progress_reading", name=message.removeprefix("Leggo "))
        if message == "Raggruppo duplicati e immagini simili":
            return self.t("progress_grouping")
        return message

    def _translate_issue(self, issue: str | None) -> str:
        if issue is None or self.language_code == "it":
            return issue or ""
        if issue.startswith("Non posso aprire questa immagine:"):
            return issue.replace("Non posso aprire questa immagine:", self.t("cannot_open_image"), 1)
        if issue.startswith("Non posso convertire in JPEG:"):
            return issue.replace("Non posso convertire in JPEG:", self.t("cannot_convert_image"), 1)
        return issue

    def _scan_summary_text(self, result: ScanResult) -> str:
        skipped = self.t("scan_summary_skipped", count=len(result.skipped)) if result.skipped else self.t("scan_summary_end")
        return self.t("scan_summary", photos=len(result.photos), groups=len(result.groups), skipped=skipped)

    def _build_style(self) -> None:
        self.configure(bg=COLORS["bg"])
        self.option_add("*Font", "TkDefaultFont 11")
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Surface.TFrame", background=COLORS["surface"])
        style.configure("Soft.TFrame", background=COLORS["surface_alt"])
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"])
        style.configure("Surface.TLabel", background=COLORS["surface"], foreground=COLORS["text"])
        style.configure("Soft.TLabel", background=COLORS["surface_alt"], foreground=COLORS["text"])
        style.configure("Muted.TLabel", background=COLORS["bg"], foreground=COLORS["muted"])
        style.configure("SurfaceMuted.TLabel", background=COLORS["surface"], foreground=COLORS["muted"])
        style.configure("SoftMuted.TLabel", background=COLORS["surface_alt"], foreground=COLORS["muted"])
        style.configure("TButton", padding=(11, 7), relief="flat", borderwidth=1)
        style.configure("Accent.TButton", padding=(18, 10), background=COLORS["primary"], foreground="#ffffff", borderwidth=0)
        style.map(
            "Accent.TButton",
            background=[("active", COLORS["primary_hover"]), ("disabled", "#c8c1d0")],
            foreground=[("disabled", "#f7f2fa")],
        )
        style.configure("Secondary.TButton", padding=(12, 8), background=COLORS["surface_container"], foreground=COLORS["text"])
        style.map("Secondary.TButton", background=[("active", COLORS["primary_container"])])
        style.configure(
            "Tertiary.TButton",
            padding=(12, 8),
            background=COLORS["tertiary_container"],
            foreground=COLORS["on_tertiary_container"],
        )
        style.map("Tertiary.TButton", background=[("active", "#ffc1d6")])
        style.configure("TCheckbutton", background=COLORS["surface"], foreground=COLORS["text"])
        style.configure("M3.TCheckbutton", background=COLORS["primary_container"], foreground=COLORS["on_primary_container"])
        style.configure("Horizontal.TProgressbar", troughcolor=COLORS["surface_container"], background=COLORS["primary"], bordercolor=COLORS["surface_container"])

    def _build_layout(self) -> None:
        top = tk.Frame(
            self,
            bg=COLORS["primary_container"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            padx=20,
            pady=18,
        )
        top.pack(fill="x", padx=16, pady=(16, 10))

        title_row = tk.Frame(top, bg=COLORS["primary_container"])
        title_row.pack(fill="x")
        tk.Label(
            title_row,
            text="Similar Photos",
            bg=COLORS["primary_container"],
            fg=COLORS["on_primary_container"],
            font=("TkDefaultFont", 21, "bold"),
        ).pack(side="left")
        self.scan_button = ttk.Button(title_row, text=self.t("scan"), style="Accent.TButton", command=self.start_scan)
        self.scan_button.pack(side="right")

        language_box = tk.Frame(title_row, bg=COLORS["primary_container"])
        language_box.pack(side="right", padx=(0, 12))
        self.language_label = tk.Label(
            language_box,
            text=self.t("language"),
            bg=COLORS["primary_container"],
            fg=COLORS["on_primary_container"],
            font=("TkDefaultFont", 10, "bold"),
        )
        self.language_label.pack(anchor="w")
        self.language_menu = ttk.Combobox(
            language_box,
            textvariable=self.language_display_var,
            values=list(LANGUAGE_NAMES.values()),
            state="readonly",
            width=10,
        )
        self.language_menu.pack(anchor="w")
        self.language_menu.bind("<<ComboboxSelected>>", self._language_changed)

        controls = tk.Frame(top, bg=COLORS["primary_container"])
        controls.pack(fill="x", pady=(16, 0))

        self.choose_folder_button = ttk.Button(controls, text=self.t("choose_folder"), style="Secondary.TButton", command=self.choose_folder)
        self.choose_folder_button.pack(side="left")
        folder_entry = ttk.Entry(controls, textvariable=self.folder_var)
        folder_entry.pack(side="left", fill="x", expand=True, padx=(8, 12), ipady=3)
        self.recursive_check = ttk.Checkbutton(controls, text=self.t("recursive"), style="M3.TCheckbutton", variable=self.recursive_var)
        self.recursive_check.pack(side="left", padx=(0, 14))

        similarity_box = tk.Frame(controls, bg=COLORS["primary_container"])
        similarity_box.pack(side="left")
        self.similarity_label = tk.Label(
            similarity_box,
            text=self.t("similarity"),
            bg=COLORS["primary_container"],
            fg=COLORS["on_primary_container"],
            font=("TkDefaultFont", 10, "bold"),
        )
        self.similarity_label.pack(anchor="w")
        slider_row = tk.Frame(similarity_box, bg=COLORS["primary_container"])
        slider_row.pack(fill="x")
        ttk.Scale(
            slider_row,
            from_=2,
            to=18,
            variable=self.threshold_var,
            orient="horizontal",
            length=120,
            command=self._threshold_changed,
        ).pack(side="left")
        tk.Label(
            slider_row,
            textvariable=self.threshold_label_var,
            width=2,
            bg=COLORS["primary_container"],
            fg=COLORS["on_primary_container"],
            font=("TkDefaultFont", 10, "bold"),
        ).pack(side="left", padx=(5, 0))

        explanation = tk.Frame(top, bg=COLORS["secondary_container"], highlightbackground=COLORS["secondary"], highlightthickness=1, padx=14, pady=10)
        explanation.pack(fill="x", pady=(14, 0))
        self.threshold_help_var = tk.StringVar(value=self._threshold_help_text())
        tk.Label(
            explanation,
            textvariable=self.threshold_help_var,
            bg=COLORS["secondary_container"],
            fg=COLORS["on_secondary_container"],
            font=("TkDefaultFont", 10),
            wraplength=980,
            justify="left",
        ).pack(anchor="w")

        progress_frame = tk.Frame(self, bg=COLORS["bg"])
        progress_frame.pack(fill="x", padx=16, pady=(0, 10))
        ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100).pack(fill="x")
        ttk.Label(progress_frame, textvariable=self.status_var, style="Muted.TLabel").pack(anchor="w", pady=(6, 0))

        main = tk.Frame(
            self,
            bg=COLORS["surface"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            padx=18,
            pady=18,
        )
        main.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        header = tk.Frame(main, bg=COLORS["surface"])
        header.pack(fill="x")
        self.group_title_var = tk.StringVar(value=self.t("no_group_title"))
        tk.Label(
            header,
            textvariable=self.group_title_var,
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("TkDefaultFont", 15, "bold"),
        ).pack(side="left")
        self.export_report_button = ttk.Button(header, text=self.t("export_report"), style="Secondary.TButton", command=self.export_report)
        self.export_report_button.pack(side="right")

        self.group_question_var = tk.StringVar(value=self.t("intro_question"))
        tk.Label(
            main,
            textvariable=self.group_question_var,
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("TkDefaultFont", 11),
            wraplength=980,
            justify="left",
        ).pack(anchor="w", pady=(6, 0))

        canvas_frame = tk.Frame(main, bg=COLORS["surface"])
        canvas_frame.pack(fill="both", expand=True, pady=(14, 0))
        self.canvas = tk.Canvas(canvas_frame, bg=COLORS["surface"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.cards_frame = ttk.Frame(self.canvas, style="Surface.TFrame")
        self.cards_window = self.canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.cards_frame.bind("<Configure>", lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._resize_cards_frame)
        self._bind_mousewheel(self.canvas)
        self._bind_mousewheel(self.cards_frame)

        footer = tk.Frame(main, bg=COLORS["surface"])
        footer.pack(fill="x", pady=(14, 0))
        self.back_button = ttk.Button(footer, text=self.t("back"), style="Secondary.TButton", command=self.previous_group, state="disabled")
        self.back_button.pack(side="left")
        self.next_button = ttk.Button(footer, text=self.t("next_group"), style="Accent.TButton", command=self.next_group, state="disabled")
        self.next_button.pack(side="right")
        self.keep_suggested_button = ttk.Button(footer, text=self.t("keep_suggested"), style="Tertiary.TButton", command=self.keep_only_suggested, state="disabled")
        self.keep_suggested_button.pack(side="right", padx=(0, 8))

    def _resize_cards_frame(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.cards_window, width=event.width)

    def _bind_mousewheel(self, widget: tk.Widget) -> None:
        widget.bind("<Enter>", self._activate_mousewheel)
        widget.bind("<Leave>", self._deactivate_mousewheel)

    def _activate_mousewheel(self, _event: tk.Event) -> None:
        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind_all("<Button-4>", self._on_mousewheel)
        self.bind_all("<Button-5>", self._on_mousewheel)

    def _deactivate_mousewheel(self, _event: tk.Event) -> None:
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")
        self.unbind_all("<Button-5>")

    def _on_mousewheel(self, event: tk.Event) -> str:
        if getattr(event, "num", None) == 4:
            units = -3
        elif getattr(event, "num", None) == 5:
            units = 3
        else:
            delta = getattr(event, "delta", 0)
            units = -1 * int(delta / 120) if delta else 0
            if units == 0 and delta:
                units = -1 if delta > 0 else 1
        self.canvas.yview_scroll(units, "units")
        return "break"

    def choose_folder(self) -> None:
        folder = filedialog.askdirectory(title=self.t("choose_folder_title"))
        if folder:
            self.folder_var.set(folder)

    def _threshold_changed(self, value: str) -> None:
        self.threshold_label_var.set(str(round(float(value))))
        self.threshold_help_var.set(self._threshold_help_text())

    def _threshold_help_text(self) -> str:
        value = round(self.threshold_var.get())
        if value <= 5:
            mode = self.t("threshold_low")
        elif value <= 10:
            mode = self.t("threshold_mid")
        else:
            mode = self.t("threshold_high")
        return self.t("threshold_help", value=value, mode=mode)

    def start_scan(self) -> None:
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showinfo(self.t("missing_folder_title"), self.t("missing_folder_msg"))
            return
        if not Path(folder).is_dir():
            messagebox.showerror(self.t("invalid_folder_title"), self.t("invalid_folder_msg"))
            return

        self.is_scanning = True
        self.scan_button.configure(state="disabled")
        self._clear_cards()
        self._set_navigation_state("disabled")
        self.group_title_var.set(self.t("scan_title"))
        self.group_question_var.set(self.t("scan_question"))
        self.status_var.set(self.t("scan_prepare"))
        self.progress_var.set(0)

        thread = threading.Thread(target=self._scan_worker, args=(folder,), daemon=True)
        thread.start()

    def _scan_worker(self, folder: str) -> None:
        def progress(done: int, total: int, message: str) -> None:
            percent = 0 if total == 0 else done / total * 100
            self.worker_queue.put(("progress", (percent, message)))

        try:
            result = scan_folder(
                folder,
                recursive=self.recursive_var.get(),
                hamming_threshold=round(self.threshold_var.get()),
                progress=progress,
            )
            self.worker_queue.put(("done", result))
        except Exception as exc:  # pragma: no cover - surfaced in the GUI
            self.worker_queue.put(("error", str(exc)))

    def _drain_worker_queue(self) -> None:
        try:
            while True:
                kind, payload = self.worker_queue.get_nowait()
                if kind == "progress":
                    percent, message = payload  # type: ignore[misc]
                    self.progress_var.set(percent)
                    self.status_var.set(self._translate_progress_message(str(message)))
                elif kind == "done":
                    self._scan_finished(payload)  # type: ignore[arg-type]
                elif kind == "error":
                    self.is_scanning = False
                    self.scan_button.configure(state="normal")
                    self.status_var.set(self.t("scan_stopped"))
                    messagebox.showerror(self.t("error_title"), str(payload))
        except queue.Empty:
            pass
        self.after(100, self._drain_worker_queue)

    def _scan_finished(self, result: ScanResult) -> None:
        self.scan_result = result
        self.is_scanning = False
        self.keep_vars.clear()
        self.visited_groups.clear()
        self.current_group_index = 0

        for group in result.groups:
            for photo in group.photos:
                self.keep_vars.setdefault(photo.path, tk.BooleanVar(value=photo.path == group.best_path))

        self.progress_var.set(100)
        self.scan_button.configure(state="normal")
        self.status_var.set(self._scan_summary_text(result))

        if result.groups:
            self.show_group_at(0)
        else:
            self.group_title_var.set(self.t("no_groups_found"))
            self.group_question_var.set(self.t("no_groups_question"))
            self._clear_cards()
            self._set_navigation_state("disabled")

    def show_group_at(self, index: int) -> None:
        if self.scan_result is None:
            return
        self.current_group_index = index
        self.visited_groups.add(index)
        self.show_group(self.scan_result.groups[index])
        self._update_navigation()

    def show_group(self, group: PhotoGroup) -> None:
        self.current_group = group
        self._clear_cards()
        total = len(self.scan_result.groups) if self.scan_result else group.id
        self.group_title_var.set(
            self.t(
                "group_title",
                current=self.current_group_index + 1,
                total=total,
                kind=self._group_kind_label(group.kind),
                count=group.count,
            )
        )
        self.group_question_var.set(self.t("group_question"))
        self.preview_refs = []

        for index, photo in enumerate(group.photos):
            card = tk.Frame(
                self.cards_frame,
                bg=COLORS["surface"],
                highlightbackground=COLORS["border"],
                highlightthickness=1,
                padx=10,
                pady=10,
            )
            row = index // 3
            col = index % 3
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            self.cards_frame.columnconfigure(col, weight=1, uniform="cards")
            self._bind_mousewheel(card)

            preview = self._make_preview(photo)
            self.preview_refs.append(preview)
            image_label = tk.Label(card, image=preview, bg=COLORS["surface_alt"], bd=0)
            image_label.configure(cursor="hand2")
            image_label.pack(fill="x")
            self._bind_mousewheel(image_label)
            image_label.bind("<Button-1>", lambda _event, item=photo: self.show_fullscreen_photo(item))
            card.bind("<Double-Button-1>", lambda _event, item=photo: self.show_fullscreen_photo(item))

            keep_var = self.keep_vars.setdefault(photo.path, tk.BooleanVar(value=photo.path == group.best_path))
            action_row = tk.Frame(card, bg=COLORS["surface"])
            action_row.pack(fill="x", pady=(10, 4))
            self._bind_mousewheel(action_row)
            keep_check = ttk.Checkbutton(action_row, text=self.t("keep_this_photo"), variable=keep_var)
            keep_check.pack(side="left")
            self._bind_mousewheel(keep_check)
            if photo.path == group.best_path:
                badge = tk.Label(
                    action_row,
                    text=self.t("suggested"),
                    bg=COLORS["tertiary_container"],
                    fg=COLORS["on_tertiary_container"],
                    font=("TkDefaultFont", 10, "bold"),
                    padx=8,
                    pady=2,
                )
                badge.pack(side="right")
                self._bind_mousewheel(badge)

            name = tk.Label(
                card,
                text=photo.path.name,
                bg=COLORS["surface"],
                fg=COLORS["text"],
                anchor="w",
                justify="left",
                wraplength=290,
                font=("TkDefaultFont", 11, "bold"),
            )
            name.pack(fill="x")
            self._bind_mousewheel(name)
            details = self._photo_details(photo)
            details_label = tk.Label(
                card,
                text=details,
                bg=COLORS["surface"],
                fg=COLORS["muted"],
                anchor="w",
                justify="left",
                font=("TkDefaultFont", 10),
            )
            details_label.pack(fill="x", pady=(5, 0))
            self._bind_mousewheel(details_label)

            button_row = tk.Frame(card, bg=COLORS["surface"])
            button_row.pack(fill="x", pady=(10, 0))
            self._bind_mousewheel(button_row)
            open_button = ttk.Button(button_row, text=self.t("open"), style="Secondary.TButton", command=lambda item=photo: self.open_photo(item))
            open_button.pack(side="left")
            self._bind_mousewheel(open_button)
            reveal_button = ttk.Button(button_row, text=self._reveal_button_text(), style="Secondary.TButton", command=lambda item=photo: self.reveal_photo(item))
            reveal_button.pack(side="left", padx=(6, 0))
            self._bind_mousewheel(reveal_button)

    def _make_preview(self, photo: PhotoInfo) -> ImageTk.PhotoImage:
        try:
            with Image.open(photo.path) as image:
                image = ImageOps.exif_transpose(image)
                image.thumbnail((300, 220), Image.Resampling.LANCZOS)
                background = Image.new("RGB", (300, 220), COLORS["surface_alt"])
                x = (300 - image.width) // 2
                y = (220 - image.height) // 2
                background.paste(image.convert("RGB"), (x, y))
        except Exception:
            background = Image.new("RGB", (300, 220), COLORS["surface_alt"])
        return ImageTk.PhotoImage(background)

    def _photo_details(self, photo: PhotoInfo) -> str:
        dimensions = f"{photo.width}x{photo.height}" if photo.width and photo.height else self.t("dimensions_unknown")
        issue_text = self._translate_issue(photo.issue)
        issue = f"\n{issue_text}" if issue_text else ""
        return f"{dimensions}  |  {photo.megapixels:.1f} MP  |  {format_bytes(photo.size_bytes)}\n{self.t('estimated_quality')} {photo.quality_score:.2f}{issue}"

    def _clear_cards(self) -> None:
        for child in self.cards_frame.winfo_children():
            child.destroy()
        self.preview_refs = []

    def open_photo(self, photo: PhotoInfo) -> None:
        system = platform.system()
        if system == "Windows":
            os.startfile(photo.path)  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.Popen(["open", str(photo.path)])
        else:
            subprocess.Popen(["xdg-open", str(photo.path)])

    def reveal_photo(self, photo: PhotoInfo) -> None:
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(["explorer", "/select,", str(photo.path)])
        elif system == "Darwin":
            subprocess.Popen(["open", "-R", str(photo.path)])
        else:
            subprocess.Popen(["xdg-open", str(photo.path.parent)])

    def _reveal_button_text(self) -> str:
        return self.t("reveal_explorer") if platform.system() == "Windows" else self.t("reveal_finder")

    def show_fullscreen_photo(self, photo: PhotoInfo) -> None:
        self.close_fullscreen_photo()
        self.update_idletasks()
        max_width = max(self.winfo_width() - 48, 300)
        max_height = max(self.winfo_height() - 96, 220)

        try:
            with Image.open(photo.path) as image:
                image = ImageOps.exif_transpose(image)
                image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                display = image.convert("RGB")
        except Exception as exc:
            messagebox.showerror(self.t("preview_unavailable_title"), f"{self.t('cannot_open_image')}\n{exc}")
            return

        overlay = tk.Frame(self, bg="#000000")
        overlay.place(x=0, y=0, relwidth=1, relheight=1)
        overlay.lift()
        overlay.focus_set()
        overlay.bind("<Escape>", lambda _event: self.close_fullscreen_photo())
        overlay.bind("<Button-1>", lambda _event: self.close_fullscreen_photo())
        self.bind("<Escape>", lambda _event: self.close_fullscreen_photo())

        self.fullscreen_preview_ref = ImageTk.PhotoImage(display)
        image_label = tk.Label(overlay, image=self.fullscreen_preview_ref, bg="#000000")
        image_label.place(relx=0.5, rely=0.5, anchor="center")
        image_label.bind("<Button-1>", lambda _event: self.close_fullscreen_photo())

        hint = tk.Label(
            overlay,
            text=self.t("fullscreen_hint"),
            bg="#000000",
            fg="#ffffff",
            padx=12,
            pady=8,
        )
        hint.place(relx=0.5, rely=0.04, anchor="n")
        hint.bind("<Button-1>", lambda _event: self.close_fullscreen_photo())
        self.fullscreen_overlay = overlay

    def close_fullscreen_photo(self) -> None:
        if self.fullscreen_overlay is not None:
            self.fullscreen_overlay.destroy()
            self.fullscreen_overlay = None
        self.fullscreen_preview_ref = None

    def previous_group(self) -> None:
        if self.scan_result is None or self.current_group_index <= 0:
            return
        self.show_group_at(self.current_group_index - 1)

    def next_group(self) -> None:
        if self.scan_result is None or not self._confirm_group_has_keep():
            return
        if self.current_group_index < len(self.scan_result.groups) - 1:
            self.show_group_at(self.current_group_index + 1)
        else:
            self.finish_and_trash_discards()

    def keep_only_suggested(self) -> None:
        if self.current_group is None:
            return
        for photo in self.current_group.photos:
            keep_var = self.keep_vars.setdefault(photo.path, tk.BooleanVar(value=False))
            keep_var.set(photo.path == self.current_group.best_path)

    def _confirm_group_has_keep(self) -> bool:
        if self.current_group is None:
            return True
        has_keep = any(self.keep_vars.get(photo.path) is not None and self.keep_vars[photo.path].get() for photo in self.current_group.photos)
        if has_keep:
            return True
        return messagebox.askyesno(
            self.t("no_keep_title"),
            self.t("no_keep_msg"),
        )

    def _update_navigation(self) -> None:
        if self.scan_result is None or not self.scan_result.groups:
            self._set_navigation_state("disabled")
            return
        self.back_button.configure(state="normal" if self.current_group_index > 0 else "disabled")
        self.keep_suggested_button.configure(state="normal")
        last_group = self.current_group_index == len(self.scan_result.groups) - 1
        self.next_button.configure(state="normal", text=self.t("finish_trash") if last_group else self.t("next_group"))

    def _set_navigation_state(self, state: str) -> None:
        self.back_button.configure(state=state)
        self.next_button.configure(state=state)
        self.keep_suggested_button.configure(state=state)

    def finish_and_trash_discards(self) -> None:
        if self.scan_result is None:
            return
        if len(self.visited_groups) < len(self.scan_result.groups):
            messagebox.showinfo(self.t("incomplete_title"), self.t("incomplete_msg"))
            return

        discards: list[PhotoInfo] = []
        seen: set[Path] = set()
        for group in self.scan_result.groups:
            for photo in group.photos:
                keep_var = self.keep_vars.get(photo.path)
                if keep_var is not None and not keep_var.get() and photo.path not in seen and photo.path.exists():
                    discards.append(photo)
                    seen.add(photo.path)

        if not discards:
            messagebox.showinfo(self.t("no_discard_title"), self.t("no_discard_msg"))
            return

        confirmed = messagebox.askyesno(
            self.t("trash_confirm_title"),
            self.t("trash_confirm_msg", count=len(discards)),
        )
        if not confirmed:
            return

        moved = 0
        errors: list[str] = []
        for photo in discards:
            try:
                safe_move_to_trash(photo)
                moved += 1
            except OSError as exc:
                errors.append(f"{photo.rel_path}: {exc}")

        if errors:
            messagebox.showwarning(self.t("partial_move_title"), self.t("partial_move_msg", count=moved) + "\n\n" + "\n".join(errors[:8]))
        else:
            messagebox.showinfo(self.t("done_title"), self.t("done_msg", count=moved))
        self.start_scan()

    def export_report(self) -> None:
        if self.scan_result is None:
            return
        target = filedialog.asksaveasfilename(
            title=self.t("save_report_title"),
            defaultextension=".txt",
            filetypes=[(self.t("text_file"), "*.txt")],
            initialfile="similar_photos_report.txt",
        )
        if not target:
            return

        lines = [
            f"{self.t('report_folder')}: {self.scan_result.root}",
            f"{self.t('report_photos')}: {len(self.scan_result.photos)}",
            f"{self.t('report_groups')}: {len(self.scan_result.groups)}",
            "",
        ]
        for group in self.scan_result.groups:
            lines.append(f"{self.t('report_group')} {group.id} - {self._group_kind_label(group.kind)} - {self.t('report_suggested')}: {group.best_path}")
            for photo in group.photos:
                keep_var = self.keep_vars.get(photo.path)
                action = self.t("report_keep") if keep_var is not None and keep_var.get() else self.t("report_discard")
                lines.append(f"  [{action}] {photo.path}")
            lines.append("")

        Path(target).write_text("\n".join(lines), encoding="utf-8")
        messagebox.showinfo(self.t("report_saved_title"), self.t("report_saved_msg", target=target))


def main() -> None:
    os.environ.setdefault("TK_SILENCE_DEPRECATION", "1")
    app = SimilarPhotosApp()
    app.mainloop()
