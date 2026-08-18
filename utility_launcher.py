#!/usr/bin/env python3
"""Menu unico per avviare le utility Python raccolte in questo progetto."""

from __future__ import annotations

import os
import runpy
import subprocess
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk



def is_frozen() -> bool:
    """Indica se il programma è stato distribuito come applicazione PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def bundled_candidates() -> tuple[Path, ...]:
    """Elenca le possibili radici della release sui sistemi supportati."""
    executable_directory = Path(sys.executable).resolve().parent
    contents_directory = executable_directory.parent
    meipass = Path(getattr(sys, "_MEIPASS", executable_directory))
    return (
        meipass,
        executable_directory,
        contents_directory / "Resources",
        contents_directory / "Frameworks",
    )


def runtime_root() -> Path:
    """Restituisce la radice dei dati inclusi o del progetto sorgente."""
    if is_frozen():
        return next((path for path in bundled_candidates() if (path / "apps").is_dir()), bundled_candidates()[0])
    return Path(__file__).resolve().parent


def bundled_tools_dir() -> Path:
    """Trova FFmpeg incluso, che PyInstaller colloca in modo diverso su macOS."""
    if not is_frozen():
        return ROOT_DIR / "tools"
    return next(
        (path / "tools" for path in bundled_candidates() if (path / "tools").is_dir()),
        ROOT_DIR / "tools",
    )


ROOT_DIR = runtime_root()
APPS_DIR = ROOT_DIR / "apps"
VENV_DIR = ROOT_DIR / ".venv"
REQUIREMENTS_FILE = ROOT_DIR / "requirements.txt"
TOOLS_DIR = bundled_tools_dir()

COLORS = {
    "canvas": "#f5f6fa",
    "card": "#ffffff",
    "text": "#1c1c1e",
    "muted": "#6e6e73",
    "border": "#d1d1d6",
    "accent": "#0a84ff",
    "accent_active": "#006edc",
    "warning": "#9a4f00",
}


@dataclass(frozen=True)
class Utility:
    key: str
    folder: str
    entry_point: str

    @property
    def directory(self) -> Path:
        return APPS_DIR / self.folder

    @property
    def program(self) -> Path:
        return self.directory / self.entry_point

    @property
    def icon(self) -> Path:
        return self.directory / "logo.png"


UTILITIES = (
    Utility("comic_tag_editor", "comic-tag-editor", "comic_tag_editor.py"),
    Utility("mp3_tag_editor", "mp3-tag-editor", "app.py"),
    Utility("photo_color_correction", "photos-color-correction", "gui_app.py"),
    Utility("similar_photos", "similar-photos", "app.py"),
    Utility("images_to_pdf", "images-to-pdfs", "main.py"),
    Utility("extract_audio", "extract-audios-from-video", "extract_audio_tracks.py"),
    Utility("track_subtitle_editor", "video-track-and-sub-editor", "main.py"),
)

LANGUAGE_NAMES = {"it": "Italiano", "en": "English"}

TEXT = {
    "it": {
        "title": "Le mie utility",
        "subtitle": "Seleziona un programma e premi Apri.",
        "language": "Lingua",
        "details": "Dettagli",
        "open_folder": "Apri cartella",
        "exit": "Esci",
        "open": "Apri",
        "ready": "Pronto",
        "opened": "Aperto: {name}",
        "program_missing": "Programma non trovato",
        "program_missing_message": "Non trovo {path}.",
        "launch_error": "Impossibile avviare",
        "folder_error": "Impossibile aprire la cartella",
        "utilities": {
            "comic_tag_editor": {
                "name": "Comic Tag Editor",
                "description": "Modifica i metadati di fumetti PDF, CBR e CBZ.",
                "note": "",
            },
            "mp3_tag_editor": {
                "name": "MP3 Tag Editor",
                "description": "Converte audio in MP3 e modifica i tag dei brani.",
                "note": "Richiede FFmpeg per la conversione.",
            },
            "photo_color_correction": {
                "name": "Correzione colore foto",
                "description": "Migliora automaticamente colore, contrasto e nitidezza delle foto.",
                "note": "",
            },
            "similar_photos": {
                "name": "Foto simili",
                "description": "Trova foto duplicate o simili e aiuta a selezionare quelle da conservare.",
                "note": "",
            },
            "images_to_pdf": {
                "name": "Immagini in PDF",
                "description": "Crea uno o più PDF a partire dalle immagini di una cartella.",
                "note": "",
            },
            "extract_audio": {
                "name": "Estrai audio da video",
                "description": "Estrae una o più tracce audio da un filmato.",
                "note": "Richiede FFmpeg e FFprobe nel PATH.",
            },
            "track_subtitle_editor": {
                "name": "Editor tracce e sottotitoli",
                "description": "Aggiunge, rimuove e riordina tracce audio e sottotitoli nei video.",
                "note": "Richiede FFmpeg e FFprobe nel PATH.",
            },
        },
    },
    "en": {
        "title": "My utilities",
        "subtitle": "Choose a program and press Open.",
        "language": "Language",
        "details": "Details",
        "open_folder": "Open folder",
        "exit": "Exit",
        "open": "Open",
        "ready": "Ready",
        "opened": "Opened: {name}",
        "program_missing": "Program not found",
        "program_missing_message": "Cannot find {path}.",
        "launch_error": "Unable to launch",
        "folder_error": "Unable to open the folder",
        "utilities": {
            "comic_tag_editor": {
                "name": "Comic Tag Editor",
                "description": "Edit metadata for PDF, CBR, and CBZ comic books.",
                "note": "",
            },
            "mp3_tag_editor": {
                "name": "MP3 Tag Editor",
                "description": "Convert audio to MP3 and edit track tags.",
                "note": "FFmpeg is required for conversion.",
            },
            "photo_color_correction": {
                "name": "Photo Color Correction",
                "description": "Automatically improve photo color, contrast, and sharpness.",
                "note": "",
            },
            "similar_photos": {
                "name": "Similar Photos",
                "description": "Find duplicate or similar photos and choose which ones to keep.",
                "note": "",
            },
            "images_to_pdf": {
                "name": "Images to PDF",
                "description": "Create one or more PDFs from the images in a folder.",
                "note": "",
            },
            "extract_audio": {
                "name": "Extract Audio from Video",
                "description": "Extract one or more audio tracks from a video.",
                "note": "FFmpeg and FFprobe must be available in PATH.",
            },
            "track_subtitle_editor": {
                "name": "Track & Subtitle Editor",
                "description": "Add, remove, and reorder audio tracks and subtitles in videos.",
                "note": "FFmpeg and FFprobe must be available in PATH.",
            },
        },
    },
}


def venv_python() -> Path:
    """Restituisce il percorso del Python dell'ambiente condiviso."""
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def ensure_shared_environment() -> None:
    """Prepara le dipendenze anche quando il launcher è avviato da Terminale."""
    # La release PyInstaller contiene già Python e ogni dipendenza: non deve
    # creare un ambiente virtuale né tentare download al primo avvio.
    if is_frozen():
        return
    if os.environ.get("UTILITY_HUB_BOOTSTRAPPED") == "1":
        return

    python = venv_python()
    try:
        if not python.is_file():
            print("Creo l'ambiente Python condiviso…")
            subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)

        required_imports = "import PIL, mutagen, pypdf, tkinterdnd2"
        installed = subprocess.run(
            [str(python), "-c", required_imports],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode == 0
        if not installed:
            print("Installo le dipendenze condivise…")
            subprocess.run(
                [str(python), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
                check=True,
            )
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError(
            "Non riesco a preparare l'ambiente Python. "
            "Controlla la connessione e che Python 3 sia installato."
        ) from error

    environment = os.environ.copy()
    environment["UTILITY_HUB_BOOTSTRAPPED"] = "1"
    os.execve(str(python), [str(python), str(Path(__file__).resolve())], environment)


def configure_bundled_tools() -> None:
    """Rende FFmpeg e FFprobe inclusi nella release visibili alle utility."""
    if not is_frozen() or not TOOLS_DIR.is_dir():
        return
    current_path = os.environ.get("PATH", "")
    os.environ["PATH"] = str(TOOLS_DIR) + (os.pathsep + current_path if current_path else "")


def run_bundled_utility(key: str) -> None:
    """Esegue una utility inclusa nella release in un processo GUI dedicato."""
    utility = next((item for item in UTILITIES if item.key == key), None)
    if utility is None:
        raise RuntimeError(f"Utility sconosciuta: {key}")
    if not utility.program.is_file():
        raise RuntimeError(f"Programma non trovato: {utility.program}")

    # Le utility sono file dati della release: il loro import locale (ad
    # esempio `from image_to_pdfs import …`) deve cercare prima nella cartella
    # dell'applicazione selezionata.
    sys.path.insert(0, str(utility.directory))
    os.chdir(utility.directory)
    runpy.run_path(str(utility.program), run_name="__main__")


def verify_release() -> int:
    """Controllo non grafico usato dalla pipeline che crea gli installer."""
    missing = [
        str(path.relative_to(ROOT_DIR))
        for utility in UTILITIES
        for path in (utility.program, utility.icon)
        if not path.is_file()
    ]
    if is_frozen():
        extension = ".exe" if os.name == "nt" else ""
        missing.extend(
            str(path.relative_to(ROOT_DIR))
            for path in (TOOLS_DIR / f"ffmpeg{extension}", TOOLS_DIR / f"ffprobe{extension}")
            if not path.is_file()
        )
    if missing:
        print("File mancanti nella release:", ", ".join(missing), file=sys.stderr)
        return 1
    import_errors = verify_utility_imports()
    if import_errors:
        print("Import non disponibili nella release:", *import_errors, sep="\n", file=sys.stderr)
        return 1
    print("Python App Utility Hub: release verificata.")
    return 0


def verify_utility_imports() -> list[str]:
    """Carica ogni utility senza avviarne la GUI.

    Le utility sono file dati eseguiti con :mod:`runpy`, quindi PyInstaller non
    riesce a rilevarne i moduli necessari in fase di analisi statica.  Questo
    controllo viene eseguito sul bundle appena creato e impedisce di pubblicare
    una release in cui una voce dell'hub si chiuderebbe subito per un import
    mancante.
    """
    errors: list[str] = []
    initial_directory = Path.cwd()
    for utility in UTILITIES:
        inserted_path = str(utility.directory)
        try:
            # Gli import locali (come ``from app import run``) devono risolvere
            # nella cartella della utility, esattamente come al suo avvio.
            sys.path.insert(0, inserted_path)
            os.chdir(utility.directory)
            runpy.run_path(
                str(utility.program),
                run_name=f"__utility_import_check_{utility.key}__",
            )
        except Exception as error:  # pragma: no cover - esercitato nel bundle PyInstaller
            errors.append(f"{utility.folder}: {error.__class__.__name__}: {error}")
        finally:
            os.chdir(initial_directory)
            try:
                sys.path.remove(inserted_path)
            except ValueError:
                pass
            # Moduli locali con nomi generici, per esempio ``app``, non devono
            # venire riutilizzati dalla verifica dell'utility successiva.
            for name, module in list(sys.modules.items()):
                module_file = getattr(module, "__file__", None)
                if module_file is None:
                    continue
                try:
                    Path(module_file).resolve().relative_to(utility.directory)
                except (OSError, ValueError):
                    continue
                sys.modules.pop(name, None)
    return errors


class UtilityHub:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.language_code = "it"
        self.language_var = tk.StringVar(value=LANGUAGE_NAMES[self.language_code])
        self.status_utility: Utility | None = None
        root.title("Python App Utility Hub")
        root.minsize(800, 500)
        root.geometry("920x580")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        self.menu_icons = self.load_icons(44)
        self.detail_icons = self.load_icons(96)

        header = ttk.Frame(root, style="Header.TFrame", padding=(28, 24, 28, 22))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        self.title_label = ttk.Label(header, style="Header.Title.TLabel")
        self.title_label.grid(row=0, column=0, sticky="w")
        self.subtitle_label = ttk.Label(
            header,
            style="Header.Subtitle.TLabel",
        )
        self.subtitle_label.grid(row=1, column=0, sticky="w", pady=(5, 0))

        language_picker = ttk.Frame(header, style="Header.TFrame")
        language_picker.grid(row=0, column=1, rowspan=2, sticky="ne")
        self.language_label = ttk.Label(language_picker, style="Header.Subtitle.TLabel")
        self.language_label.grid(row=0, column=0, sticky="e", padx=(0, 8))
        self.language_selector = ttk.Combobox(
            language_picker,
            state="readonly",
            style="Language.TCombobox",
            textvariable=self.language_var,
            values=tuple(LANGUAGE_NAMES.values()),
            width=10,
        )
        self.language_selector.grid(row=0, column=1, sticky="e")
        self.language_selector.bind("<<ComboboxSelected>>", self.change_language)

        content = ttk.Frame(root, style="App.TFrame", padding=(28, 0, 28, 18))
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=4)
        content.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            content,
            columns=(),
            selectmode="browse",
            show="tree",
            style="Utilities.Treeview",
        )
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        for index, utility in enumerate(UTILITIES):
            self.tree.insert(
                "",
                "end",
                iid=str(index),
                image=self.menu_icons[index],
            )
        self.tree.bind("<<TreeviewSelect>>", self.update_details)
        self.tree.bind("<Double-Button-1>", self.launch_selected)
        self.tree.selection_set("0")
        self.tree.focus("0")

        self.detail_box = ttk.LabelFrame(content, style="Card.TLabelframe", padding=20)
        self.detail_box.grid(row=0, column=1, sticky="nsew")
        self.detail_box.columnconfigure(1, weight=1)
        self.detail_icon = ttk.Label(self.detail_box, style="Card.TLabel")
        self.detail_icon.grid(row=0, column=0, rowspan=3, sticky="nw", padx=(0, 18))
        self.detail_title = ttk.Label(self.detail_box, style="Detail.Title.TLabel", wraplength=265)
        self.detail_title.grid(row=0, column=1, sticky="nw")
        self.description = ttk.Label(
            self.detail_box,
            justify="left",
            style="Info.TLabel",
            wraplength=265,
        )
        self.description.grid(row=1, column=1, sticky="nw", pady=(10, 0))
        self.note = ttk.Label(self.detail_box, justify="left", style="Note.TLabel", wraplength=265)
        self.note.grid(row=2, column=1, sticky="nw", pady=(14, 0))

        buttons = ttk.Frame(root, style="App.TFrame", padding=(28, 0, 28, 18))
        buttons.grid(row=2, column=0, sticky="ew")
        buttons.columnconfigure(0, weight=1)
        self.open_folder_button = ttk.Button(buttons, command=self.open_selected_folder)
        self.open_folder_button.grid(
            row=0, column=1, padx=(0, 8)
        )
        self.exit_button = ttk.Button(buttons, command=root.destroy)
        self.exit_button.grid(row=0, column=2, padx=(0, 8))
        self.open_button = ttk.Button(buttons, command=self.launch_selected)
        self.open_button.grid(row=0, column=3)

        footer = ttk.Frame(root, style="Footer.TFrame", padding=(28, 12))
        footer.grid(row=3, column=0, sticky="ew")
        self.status = ttk.Label(footer, style="Status.TLabel")
        self.status.pack(anchor="w")
        self.refresh_texts()

    @staticmethod
    def load_icon(path: Path, size: int) -> tk.PhotoImage:
        """Ridimensiona un logo senza modificare l'icona originale sul disco."""
        from PIL import Image, ImageTk

        with Image.open(path) as source:
            image = source.convert("RGBA")
            image.thumbnail((size, size), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        offset = ((size - image.width) // 2, (size - image.height) // 2)
        canvas.alpha_composite(image, offset)
        return ImageTk.PhotoImage(canvas)

    def load_icons(self, size: int) -> tuple[tk.PhotoImage, ...]:
        icons: list[tk.PhotoImage] = []
        for utility in UTILITIES:
            try:
                icons.append(self.load_icon(utility.icon, size))
            except (OSError, ValueError):
                icons.append(tk.PhotoImage(width=size, height=size))
        return tuple(icons)

    def selected_utility(self) -> Utility | None:
        selection = self.tree.selection()
        return UTILITIES[int(selection[0])] if selection else None

    def text(self, key: str, **values: str) -> str:
        return TEXT[self.language_code][key].format(**values)

    def utility_text(self, utility: Utility) -> dict[str, str]:
        return TEXT[self.language_code]["utilities"][utility.key]

    def refresh_status(self) -> None:
        if self.status_utility is None:
            self.status.configure(text=self.text("ready"))
            return
        name = self.utility_text(self.status_utility)["name"]
        self.status.configure(text=self.text("opened", name=name))

    def refresh_texts(self) -> None:
        self.root.title("Python App Utility Hub")
        self.title_label.configure(text=self.text("title"))
        self.subtitle_label.configure(text=self.text("subtitle"))
        self.language_label.configure(text=self.text("language"))
        self.detail_box.configure(text=self.text("details"))
        self.open_folder_button.configure(text=self.text("open_folder"))
        self.exit_button.configure(text=self.text("exit"))
        self.open_button.configure(text=self.text("open"))
        for index, utility in enumerate(UTILITIES):
            self.tree.item(str(index), text=f"  {self.utility_text(utility)['name']}")
        self.update_details()
        self.refresh_status()

    def change_language(self, _event: object | None = None) -> None:
        chosen_name = self.language_var.get()
        self.language_code = next(
            code for code, language_name in LANGUAGE_NAMES.items() if language_name == chosen_name
        )
        self.refresh_texts()

    def update_details(self, _event: object | None = None) -> None:
        utility = self.selected_utility()
        if utility is None:
            return
        index = UTILITIES.index(utility)
        details = self.utility_text(utility)
        self.detail_icon.configure(image=self.detail_icons[index])
        self.detail_title.configure(text=details["name"])
        self.description.configure(text=details["description"])
        self.note.configure(text=details["note"])

    def launch_selected(self, _event: object | None = None) -> None:
        utility = self.selected_utility()
        if utility is None:
            return
        if not utility.program.is_file():
            messagebox.showerror(
                self.text("program_missing"),
                self.text("program_missing_message", path=str(utility.program.relative_to(ROOT_DIR))),
                parent=self.root,
            )
            return
        try:
            if is_frozen():
                # Il medesimo eseguibile avvia la utility selezionata con i
                # dati e le librerie già inclusi, senza richiedere Python.
                subprocess.Popen([sys.executable, "--run-utility", utility.key])
            else:
                subprocess.Popen([sys.executable, str(utility.program)], cwd=utility.directory)
        except OSError as error:
            messagebox.showerror(self.text("launch_error"), str(error), parent=self.root)
            return
        self.status_utility = utility
        self.refresh_status()

    def open_selected_folder(self) -> None:
        utility = self.selected_utility()
        if utility is None:
            return
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", str(utility.directory)])
            elif os.name == "nt":
                os.startfile(utility.directory)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(utility.directory)])
        except OSError as error:
            messagebox.showerror(self.text("folder_error"), str(error), parent=self.root)


def configure_theme(root: tk.Tk) -> None:
    """Usa gli stessi colori in modalità chiara e scura di macOS."""
    root.configure(background=COLORS["canvas"])
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=COLORS["canvas"], foreground=COLORS["text"])
    style.configure("App.TFrame", background=COLORS["canvas"])
    style.configure("Header.TFrame", background=COLORS["canvas"])
    style.configure(
        "Header.Title.TLabel",
        background=COLORS["canvas"],
        foreground=COLORS["text"],
        font=("TkDefaultFont", 22, "bold"),
    )
    style.configure(
        "Header.Subtitle.TLabel",
        background=COLORS["canvas"],
        foreground=COLORS["muted"],
        font=("TkDefaultFont", 12),
    )
    style.configure(
        "Language.TCombobox",
        arrowcolor=COLORS["text"],
        background=COLORS["card"],
        fieldbackground=COLORS["card"],
        foreground=COLORS["text"],
        padding=(7, 4),
    )
    style.map(
        "Language.TCombobox",
        fieldbackground=[("readonly", COLORS["card"])],
        foreground=[("readonly", COLORS["text"])],
        selectbackground=[("readonly", COLORS["card"])],
        selectforeground=[("readonly", COLORS["text"])],
    )
    style.configure("Card.TLabelframe", background=COLORS["card"], bordercolor=COLORS["border"])
    style.configure(
        "Card.TLabelframe.Label",
        background=COLORS["card"],
        foreground=COLORS["text"],
        font=("TkDefaultFont", 13, "bold"),
    )
    style.configure(
        "Info.TLabel",
        background=COLORS["card"],
        foreground=COLORS["text"],
        font=("TkDefaultFont", 13),
    )
    style.configure(
        "Note.TLabel",
        background=COLORS["card"],
        foreground=COLORS["warning"],
        font=("TkDefaultFont", 12),
    )
    style.configure("Card.TLabel", background=COLORS["card"])
    style.configure(
        "Detail.Title.TLabel",
        background=COLORS["card"],
        foreground=COLORS["text"],
        font=("TkDefaultFont", 15, "bold"),
    )
    style.configure(
        "Utilities.Treeview",
        background=COLORS["card"],
        borderwidth=0,
        fieldbackground=COLORS["card"],
        font=("TkDefaultFont", 13),
        foreground=COLORS["text"],
        rowheight=56,
    )
    style.map(
        "Utilities.Treeview",
        background=[("selected", COLORS["accent"])],
        foreground=[("selected", COLORS["card"])],
    )
    style.configure("TButton", padding=(18, 9), font=("TkDefaultFont", 12))
    style.map(
        "TButton",
        background=[("active", "#e5e5ea")],
        foreground=[("disabled", COLORS["muted"])],
    )
    style.configure("Footer.TFrame", background=COLORS["canvas"])
    style.configure("Status.TLabel", background=COLORS["canvas"], foreground=COLORS["muted"])


def main() -> None:
    configure_bundled_tools()
    if len(sys.argv) == 2 and sys.argv[1] == "--verify-package":
        raise SystemExit(verify_release())
    if len(sys.argv) == 3 and sys.argv[1] == "--run-utility":
        try:
            run_bundled_utility(sys.argv[2])
        except Exception as error:  # pragma: no cover - confine della GUI distribuita
            messagebox.showerror(
                "Python App Utility Hub",
                f"Non riesco ad avviare l'app selezionata.\n\n{error}",
            )
            raise SystemExit(1) from error
        return
    try:
        ensure_shared_environment()
    except RuntimeError as error:
        messagebox.showerror("Python App Utility Hub", str(error))
        raise SystemExit(1)

    root = tk.Tk()
    configure_theme(root)
    UtilityHub(root)
    root.mainloop()


if __name__ == "__main__":
    main()
