from __future__ import annotations

import base64
import io
import os
import platform
import shutil
import subprocess
import sys
import threading
import types
from dataclasses import dataclass
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, VERTICAL, X, Y, filedialog, messagebox, ttk
import tkinter as tk

from mutagen import File as MutagenFile
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, COMM, ID3, TALB, TCOM, TCON, TDRC, TIT2, TPE1, TPE2, TPOS, TRCK, error as ID3Error
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

try:
    from PIL import Image, ImageTk
except Exception:  # pragma: no cover - optional runtime dependency
    Image = None
    ImageTk = None

try:
    if "tkinter.tix" not in sys.modules:
        tix_stub = types.ModuleType("tkinter.tix")
        tix_stub.Tk = tk.Tk
        sys.modules["tkinter.tix"] = tix_stub
        setattr(tk, "tix", tix_stub)
    from tkinterdnd2 import DND_FILES, TkinterDnD
except Exception:  # pragma: no cover - optional runtime dependency
    DND_FILES = None
    TkinterDnD = None

DND_ACTIVE = False


AUDIO_EXTENSIONS = {
    ".aac",
    ".aiff",
    ".alac",
    ".ape",
    ".flac",
    ".m4a",
    ".m4b",
    ".mp3",
    ".mp4",
    ".oga",
    ".ogg",
    ".opus",
    ".wav",
    ".wma",
}

COVER_EXTENSIONS = {".jpg", ".jpeg", ".png"}
INVALID_FILENAME_CHARS = '<>:"/\\|?*'

TAG_FIELDS = {
    "title": "Titolo",
    "artist": "Artista brano",
    "album": "Album",
    "album_artist": "Artista album",
    "track": "Numero brano",
    "disc": "Disco",
    "genre": "Genere",
    "date": "Anno/Data",
    "composer": "Compositore",
    "comment": "Commento",
}

VORBIS_FIELD_MAP = {
    "title": "title",
    "artist": "artist",
    "album": "album",
    "album_artist": "albumartist",
    "track": "tracknumber",
    "disc": "discnumber",
    "genre": "genre",
    "date": "date",
    "composer": "composer",
    "comment": "comment",
}

MP4_FIELD_MAP = {
    "title": "\xa9nam",
    "artist": "\xa9ART",
    "album": "\xa9alb",
    "album_artist": "aART",
    "track": "trkn",
    "disc": "disk",
    "genre": "\xa9gen",
    "date": "\xa9day",
    "composer": "\xa9wrt",
    "comment": "\xa9cmt",
}

ID3_FRAMES = {
    "title": TIT2,
    "artist": TPE1,
    "album": TALB,
    "album_artist": TPE2,
    "track": TRCK,
    "disc": TPOS,
    "genre": TCON,
    "date": TDRC,
    "composer": TCOM,
}


@dataclass
class Track:
    path: Path
    tags: dict[str, str]


def make_root() -> tk.Tk:
    global DND_ACTIVE, DND_FILES, TkinterDnD
    if TkinterDnD is not None:
        try:
            root = TkinterDnD.Tk()
            DND_ACTIVE = True
            return root
        except Exception:
            DND_FILES = None
            TkinterDnD = None
            DND_ACTIVE = False
    return tk.Tk()


def parse_drop_paths(raw: str, root: tk.Tk) -> list[Path]:
    try:
        parts = root.tk.splitlist(raw)
    except tk.TclError:
        parts = [raw]
    return [Path(part) for part in parts]


def is_audio(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS


def collect_audio(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            for child in path.rglob("*"):
                if is_audio(child):
                    found.append(child)
        elif is_audio(path):
            found.append(path)
    return sorted(set(found), key=lambda item: str(item).lower())


def collect_cover_images(paths: list[Path]) -> list[Path]:
    images: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix.lower() in COVER_EXTENSIONS:
            images.append(path)
    return images


def first_text(values) -> str:
    if not values:
        return ""
    if isinstance(values, list):
        return str(values[0]) if values else ""
    return str(values)


def read_tags(path: Path) -> dict[str, str]:
    audio = MutagenFile(path, easy=True)
    tags = {key: "" for key in TAG_FIELDS}
    if audio is None:
        return tags

    for field, key in VORBIS_FIELD_MAP.items():
        tags[field] = first_text(audio.tags.get(key) if audio.tags else "")
    return tags


def read_cover_bytes(path: Path) -> bytes | None:
    suffix = path.suffix.lower()
    try:
        if suffix == ".mp3":
            tags = ID3(path)
            for frame in tags.getall("APIC"):
                return frame.data
            return None

        if suffix in {".m4a", ".m4b", ".mp4"}:
            audio = MP4(path)
            covers = audio.tags.get("covr") if audio.tags else None
            return bytes(covers[0]) if covers else None

        audio = MutagenFile(path)
        if isinstance(audio, FLAC) and audio.pictures:
            return audio.pictures[0].data
        if isinstance(audio, (OggOpus, OggVorbis)) and audio.tags:
            pictures = audio.tags.get("metadata_block_picture")
            if pictures:
                return Picture(base64.b64decode(pictures[0])).data
            coverart = audio.tags.get("coverart")
            if coverart:
                return base64.b64decode(coverart[0])
    except Exception:
        return None
    return None


def cover_preview_from_bytes(data: bytes, size: int = 190):
    if Image is None or ImageTk is None:
        return None
    image = Image.open(io.BytesIO(data))
    image.thumbnail((size, size))
    canvas = Image.new("RGB", (size, size), "#f2f2f2")
    x = (size - image.width) // 2
    y = (size - image.height) // 2
    canvas.paste(image.convert("RGB"), (x, y))
    return ImageTk.PhotoImage(canvas)


def ensure_id3(path: Path) -> ID3:
    try:
        return ID3(path)
    except ID3Error:
        id3 = ID3()
        id3.save(path)
        return ID3(path)


def write_mp3_tags(path: Path, values: dict[str, str], cover_path: Path | None) -> None:
    audio = MP3(path, ID3=ID3)
    if audio.tags is None:
        audio.add_tags()

    assert audio.tags is not None
    for field, frame_cls in ID3_FRAMES.items():
        value = values.get(field, "").strip()
        audio.tags.delall(frame_cls.__name__)
        if value:
            audio.tags.add(frame_cls(encoding=3, text=value))

    comment = values.get("comment", "").strip()
    audio.tags.delall("COMM")
    if comment:
        audio.tags.add(COMM(encoding=3, lang="ita", desc="", text=comment))

    if cover_path:
        mime = "image/png" if cover_path.suffix.lower() == ".png" else "image/jpeg"
        audio.tags.delall("APIC")
        audio.tags.add(
            APIC(
                encoding=3,
                mime=mime,
                type=3,
                desc="Cover",
                data=cover_path.read_bytes(),
            )
        )
    audio.save(v2_version=3)


def write_mp4_tags(path: Path, values: dict[str, str], cover_path: Path | None) -> None:
    audio = MP4(path)
    if audio.tags is None:
        audio.add_tags()

    for field, key in MP4_FIELD_MAP.items():
        value = values.get(field, "").strip()
        if not value:
            audio.tags.pop(key, None)
            continue

        if field in {"track", "disc"}:
            try:
                number = int(value.split("/")[0].strip())
            except ValueError:
                continue
            audio.tags[key] = [(number, 0)]
        else:
            audio.tags[key] = [value]

    if cover_path:
        image_format = MP4Cover.FORMAT_PNG if cover_path.suffix.lower() == ".png" else MP4Cover.FORMAT_JPEG
        audio.tags["covr"] = [MP4Cover(cover_path.read_bytes(), imageformat=image_format)]
    audio.save()


def write_vorbis_tags(path: Path, values: dict[str, str], cover_path: Path | None) -> None:
    audio = MutagenFile(path)
    if audio is None:
        raise ValueError(f"Formato non supportato: {path.name}")
    if audio.tags is None:
        audio.add_tags()

    for field, key in VORBIS_FIELD_MAP.items():
        value = values.get(field, "").strip()
        if value:
            audio.tags[key] = [value]
        elif key in audio.tags:
            del audio.tags[key]

    if cover_path:
        if isinstance(audio, FLAC):
            audio.clear_pictures()
            picture = Picture()
            picture.type = 3
            picture.mime = "image/png" if cover_path.suffix.lower() == ".png" else "image/jpeg"
            picture.desc = "Cover"
            picture.data = cover_path.read_bytes()
            audio.add_picture(picture)
        elif isinstance(audio, (OggOpus, OggVorbis)):
            picture = Picture()
            picture.type = 3
            picture.mime = "image/png" if cover_path.suffix.lower() == ".png" else "image/jpeg"
            picture.desc = "Cover"
            picture.data = cover_path.read_bytes()
            audio.tags["metadata_block_picture"] = [base64.b64encode(picture.write()).decode("ascii")]

    audio.save()


def write_tags(path: Path, values: dict[str, str], cover_path: Path | None = None) -> None:
    suffix = path.suffix.lower()
    if suffix == ".mp3":
        write_mp3_tags(path, values, cover_path)
    elif suffix in {".m4a", ".m4b", ".mp4"}:
        write_mp4_tags(path, values, cover_path)
    else:
        write_vorbis_tags(path, values, cover_path)


def run_ffmpeg(source: Path, destination: Path, bitrate: str) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg non trovato. Installalo e aggiungilo al PATH.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-map_metadata",
        "0",
        "-vn",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        bitrate,
        str(destination),
    ]
    subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem} ({counter}){path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def safe_folder_name(value: str, fallback: str = "Artista sconosciuto") -> str:
    cleaned = "".join("_" if char in INVALID_FILENAME_CHARS else char for char in value).strip()
    cleaned = " ".join(cleaned.split())
    cleaned = cleaned.strip(". ")
    return cleaned or fallback


def artist_folder_for_track(track: Track) -> str:
    artist = track.tags.get("album_artist") or track.tags.get("artist") or ""
    return safe_folder_name(artist)


def common_base(paths: list[Path]) -> Path | None:
    if not paths:
        return None
    try:
        return Path(os.path.commonpath([str(path.resolve()) for path in paths]))
    except Exception:
        return paths[0].resolve()


class TagEditorApp:
    def __init__(self, initial_paths: list[Path] | None = None) -> None:
        self.root = make_root()
        self.root.title("MP3 Tag Editor")
        self.root.geometry("1180x720")
        self.root.minsize(980, 600)

        self.tracks: dict[str, Track] = {}
        self.source_roots: list[Path] = []
        self.field_vars = {field: tk.StringVar() for field in TAG_FIELDS}
        self.loading_form = False
        self.dirty_fields: set[str] = set()
        self.bitrate_var = tk.StringVar(value="320k")
        self.cover_path: Path | None = None
        self.cover_preview = None
        self.sort_column: str | None = None
        self.sort_reverse = False
        self.tree_headings: dict[str, str] = {}
        self.status_var = tk.StringVar(value="Trascina qui file audio o cartelle.")

        self.configure_field_tracking()
        self.build_ui()
        self.configure_dnd()
        self.configure_shortcuts()
        if initial_paths:
            self.add_paths(initial_paths)

    def build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main = ttk.Frame(self.root)
        main.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=0, minsize=360)
        main.rowconfigure(0, weight=1)

        left = ttk.Frame(main)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        right_outer = ttk.Frame(main, width=360)
        right_outer.grid(row=0, column=1, sticky="ns")
        right_outer.grid_propagate(False)
        right_outer.columnconfigure(0, weight=1)
        right_outer.rowconfigure(0, weight=1)

        right_canvas = tk.Canvas(right_outer, highlightthickness=0, borderwidth=0)
        right_scrollbar = ttk.Scrollbar(right_outer, orient=VERTICAL, command=right_canvas.yview)
        right_canvas.configure(yscrollcommand=right_scrollbar.set)
        right_canvas.grid(row=0, column=0, sticky="nsew")
        right_scrollbar.grid(row=0, column=1, sticky="ns")

        right = ttk.Frame(right_canvas, padding=(0, 0, 8, 0))
        right_window = right_canvas.create_window((0, 0), window=right, anchor="nw")

        def update_side_scrollregion(_event=None) -> None:
            right_canvas.configure(scrollregion=right_canvas.bbox("all"))

        def keep_side_width(event) -> None:
            right_canvas.itemconfigure(right_window, width=event.width)

        def scroll_side(event) -> str:
            if event.delta:
                if platform.system() == "Darwin":
                    direction = -1 if event.delta > 0 else 1
                    steps = direction * 8
                else:
                    steps = int(-event.delta / 120) * 5
                    if steps == 0:
                        steps = -5 if event.delta > 0 else 5
                right_canvas.yview_scroll(steps, "units")
            return "break"

        right.bind("<Configure>", update_side_scrollregion)
        right_canvas.bind("<Configure>", keep_side_width)
        right_canvas.bind("<Enter>", lambda _event: right_canvas.bind_all("<MouseWheel>", scroll_side))
        right_canvas.bind("<Leave>", lambda _event: right_canvas.unbind_all("<MouseWheel>"))
        right.bind("<Enter>", lambda _event: right_canvas.bind_all("<MouseWheel>", scroll_side))
        right.bind("<Leave>", lambda _event: right_canvas.unbind_all("<MouseWheel>"))
        right_canvas.bind("<Button-4>", lambda _event: right_canvas.yview_scroll(-5, "units"))
        right_canvas.bind("<Button-5>", lambda _event: right_canvas.yview_scroll(5, "units"))

        toolbar = ttk.Frame(left)
        toolbar.pack(fill=X, pady=(0, 8))

        ttk.Button(toolbar, text="Aggiungi file", command=self.add_files).pack(side=LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Aggiungi cartella", command=self.add_folder).pack(side=LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Rimuovi selezionati", command=self.remove_selected).pack(side=LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Svuota", command=self.clear_all).pack(side=LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Cartelle per artista", command=self.organize_by_artist).pack(side=LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Rinomina file", command=self.rename_files_from_title).pack(side=LEFT)

        table_frame = ttk.Frame(left)
        table_frame.pack(fill=BOTH, expand=True)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        columns = ("file", "title", "artist", "album", "album_artist", "track", "genre", "date")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended")
        headings = {
            "file": "File",
            "title": "Titolo",
            "artist": "Artista",
            "album": "Album",
            "album_artist": "Artista album",
            "track": "Traccia",
            "genre": "Genere",
            "date": "Data",
        }
        self.tree_headings = headings
        widths = {
            "file": 220,
            "title": 170,
            "artist": 150,
            "album": 150,
            "album_artist": 150,
            "track": 70,
            "genre": 100,
            "date": 80,
        }
        for col in columns:
            self.tree.heading(col, text=headings[col], command=lambda column=col: self.sort_by_column(column))
            self.tree.column(col, width=widths[col], minwidth=50, stretch=True)

        yscroll = ttk.Scrollbar(table_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self.on_selection_changed)
        self.tree.bind("<Double-1>", self.load_first_selected)

        drop_hint = ttk.Label(left, textvariable=self.status_var, anchor="w")
        drop_hint.pack(fill=X, pady=(8, 0))

        self.build_side_panel(right)

        bottom = ttk.Frame(self.root)
        bottom.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

        ttk.Label(bottom, text="Bitrate").grid(row=0, column=0, padx=(0, 4))
        ttk.Combobox(bottom, textvariable=self.bitrate_var, width=7, values=("192k", "256k", "320k"), state="readonly").grid(
            row=0, column=1
        )
        ttk.Button(bottom, text="Converti selezionati in MP3", command=self.convert_selected).grid(row=0, column=2, padx=(10, 4))
        ttk.Button(bottom, text="Converti tutti in MP3", command=self.convert_all).grid(row=0, column=3)

    def configure_field_tracking(self) -> None:
        for field, var in self.field_vars.items():
            var.trace_add("write", lambda *_args, field=field: self.mark_field_dirty(field))

    def mark_field_dirty(self, field: str) -> None:
        if not self.loading_form:
            self.dirty_fields.add(field)

    def build_side_panel(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Tag", font=("", 13, "bold")).pack(anchor="w", pady=(0, 8))

        for field, label in TAG_FIELDS.items():
            ttk.Label(parent, text=label).pack(anchor="w", pady=(3, 1))
            ttk.Entry(parent, textvariable=self.field_vars[field]).pack(fill=X, ipady=1)

        cover_row = ttk.Frame(parent)
        cover_row.pack(fill=X, pady=(10, 4))
        ttk.Button(cover_row, text="Scegli copertina", command=self.choose_cover).pack(side=LEFT)
        ttk.Button(cover_row, text="Rimuovi", command=self.clear_cover).pack(side=LEFT, padx=(6, 0))
        self.cover_label = ttk.Label(parent, text="Nessuna copertina scelta", wraplength=300)
        self.cover_label.pack(anchor="w", pady=(0, 8))

        ttk.Button(parent, text="Carica dal brano selezionato", command=self.load_first_selected).pack(fill=X, pady=(4, 0))
        ttk.Button(parent, text="Applica tag", command=self.apply_to_selected).pack(fill=X, pady=(6, 0))
        ttk.Button(parent, text="Applica copertina", command=self.apply_cover_to_selected).pack(fill=X, pady=(6, 0))

        ttk.Separator(parent).pack(fill=X, pady=(12, 8))
        ttk.Label(parent, text="Copertina", font=("", 11, "bold")).pack(anchor="w", pady=(0, 5))
        self.cover_preview_label = ttk.Label(parent, text="Nessuna copertina", anchor="center")
        self.cover_preview_label.pack(fill=X, pady=(0, 4))

    def configure_dnd(self) -> None:
        if not DND_ACTIVE or DND_FILES is None or not hasattr(self.root, "drop_target_register"):
            if platform.system() == "Darwin":
                self.status_var.set("Drag-and-drop finestra non disponibile: usa Aggiungi oppure trascina su Avvia_Mac.command.")
            else:
                self.status_var.set("Drag-and-drop non disponibile su questo avvio: usa Aggiungi file o Aggiungi cartella.")
            return
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self.on_drop)
        self.tree.drop_target_register(DND_FILES)
        self.tree.dnd_bind("<<Drop>>", self.on_drop)
        self.cover_preview_label.drop_target_register(DND_FILES)
        self.cover_preview_label.dnd_bind("<<Drop>>", self.on_drop)
        self.status_var.set("Trascina file audio, cartelle o immagini copertina nella finestra.")

    def configure_shortcuts(self) -> None:
        self.root.bind_all("<Command-a>", self.select_all_tracks)
        self.root.bind_all("<Control-a>", self.select_all_tracks)

    def select_all_tracks(self, event=None) -> str | None:
        focus = self.root.focus_get()
        if focus is not None and focus.winfo_class() in {"Entry", "TEntry", "Text", "TCombobox"}:
            return None
        items = self.tree.get_children()
        if items:
            self.tree.selection_set(items)
            self.tree.focus(items[0])
            self.status_var.set(f"{len(items)} brani selezionati.")
        return "break"

    def on_drop(self, event) -> None:
        paths = parse_drop_paths(event.data, self.root)
        cover_images = collect_cover_images(paths)
        audio_files = collect_audio(paths)

        if cover_images and not audio_files:
            self.set_cover_path(cover_images[0])
            selected = len(self.selected_tracks())
            if selected:
                if messagebox.askyesno("Applicare copertina", f"Vuoi sovrascrivere subito la copertina di {selected} brani selezionati?"):
                    self.apply_cover_to_selected()
                else:
                    self.status_var.set(f"Copertina pronta per {selected} brani selezionati.")
            else:
                self.status_var.set("Copertina caricata. Seleziona i brani e premi Applica ai selezionati.")
            return

        self.add_paths(paths)

    def add_files(self) -> None:
        names = filedialog.askopenfilenames(
            title="Scegli file audio",
            filetypes=(("File audio", " ".join(f"*{ext}" for ext in sorted(AUDIO_EXTENSIONS))), ("Tutti i file", "*.*")),
        )
        self.add_paths([Path(name) for name in names])

    def add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Scegli cartella")
        if folder:
            self.add_paths([Path(folder)])

    def add_paths(self, paths: list[Path]) -> None:
        files = collect_audio(paths)
        if files:
            self.remember_source_roots(paths, files)
        added = 0
        for path in files:
            key = str(path.resolve())
            if key in self.tracks:
                continue
            try:
                tags = read_tags(path)
            except Exception:
                tags = {field: "" for field in TAG_FIELDS}
            self.tracks[key] = Track(path=path, tags=tags)
            self.tree.insert(
                "",
                END,
                iid=key,
                values=(
                    path.name,
                    tags["title"],
                    tags["artist"],
                    tags["album"],
                    tags["album_artist"],
                    tags["track"],
                    tags["genre"],
                    tags["date"],
                ),
            )
            added += 1
        self.apply_current_sort()
        self.status_var.set(f"{len(self.tracks)} brani caricati. Ultima aggiunta: {added}.")

    def remember_source_roots(self, paths: list[Path], files: list[Path]) -> None:
        roots: list[Path] = []
        for path in paths:
            if path.is_dir():
                roots.append(path.resolve())
            elif is_audio(path):
                roots.append(path.parent.resolve())
        if not roots:
            roots = [file.parent.resolve() for file in files]

        existing = {str(root) for root in self.source_roots}
        for root in roots:
            key = str(root)
            if key not in existing:
                self.source_roots.append(root)
                existing.add(key)

    def remove_selected(self) -> None:
        for iid in self.tree.selection():
            self.tracks.pop(iid, None)
            self.tree.delete(iid)
        if not self.tracks:
            self.source_roots.clear()
        self.status_var.set(f"{len(self.tracks)} brani caricati.")

    def clear_all(self) -> None:
        self.tracks.clear()
        self.source_roots.clear()
        self.tree.delete(*self.tree.get_children())
        self.status_var.set("Lista svuotata.")

    def organize_by_artist(self) -> None:
        tracks = list(self.tracks.values())
        if not tracks:
            messagebox.showinfo("Nessun brano", "Aggiungi almeno un brano da organizzare.")
            return

        base = self.library_base_folder()
        if base is None:
            messagebox.showinfo("Nessuna cartella", "Non riesco a determinare la cartella dei brani caricati.")
            return

        if not messagebox.askyesno(
            "Cartelle per artista",
            f"Spostare {len(tracks)} brani in sottocartelle per artista dentro:\n{base}",
        ):
            return

        errors: list[str] = []
        moved = 0
        skipped = 0
        updated_tracks: dict[str, Track] = {}

        for old_key, track in list(self.tracks.items()):
            artist_folder = artist_folder_for_track(track)
            destination_dir = base / artist_folder

            try:
                if track.path.parent.resolve() == destination_dir.resolve():
                    skipped += 1
                    updated_tracks[str(track.path.resolve())] = track
                    continue

                destination_dir.mkdir(parents=True, exist_ok=True)
                destination = unique_destination(destination_dir / track.path.name)
                shutil.move(str(track.path), str(destination))
                track.path = destination
                moved += 1
                updated_tracks[str(destination.resolve())] = track
            except Exception as exc:
                errors.append(f"{track.path.name}: {exc}")
                updated_tracks[old_key] = track

        self.tracks = updated_tracks
        self.rebuild_table()

        if errors:
            messagebox.showerror("Alcuni brani non sono stati spostati", "\n".join(errors[:8]))
        self.status_var.set(f"Organizzazione completata: {moved} spostati, {skipped} gia a posto.")

    def library_base_folder(self) -> Path | None:
        roots = self.source_roots or [track.path.parent for track in self.tracks.values()]
        base = common_base(roots)
        if base and base.is_file():
            return base.parent
        return base

    def target_tracks(self) -> list[Track]:
        selected = self.selected_tracks()
        return selected if selected else list(self.tracks.values())

    def rename_files_from_title(self) -> None:
        tracks = self.target_tracks()
        if not tracks:
            messagebox.showinfo("Nessun brano", "Aggiungi almeno un brano da rinominare.")
            return

        if not messagebox.askyesno(
            "Rinomina file",
            f"Rinominare {len(tracks)} file usando solo il titolo del brano?",
        ):
            return

        errors: list[str] = []
        renamed = 0
        skipped = 0
        updated_tracks = dict(self.tracks)

        for track in tracks:
            title = safe_folder_name(track.tags.get("title", ""), fallback="")
            if not title:
                skipped += 1
                continue

            target = track.path.with_name(f"{title}{track.path.suffix.lower()}")
            try:
                if track.path.resolve() == target.resolve():
                    skipped += 1
                    continue

                destination = unique_destination(target)
                old_key = str(track.path.resolve())
                shutil.move(str(track.path), str(destination))
                track.path = destination
                updated_tracks.pop(old_key, None)
                updated_tracks[str(destination.resolve())] = track
                renamed += 1
            except Exception as exc:
                errors.append(f"{track.path.name}: {exc}")

        self.tracks = updated_tracks
        self.rebuild_table()

        if errors:
            messagebox.showerror("Alcuni file non sono stati rinominati", "\n".join(errors[:8]))
        self.status_var.set(f"Rinomina completata: {renamed} rinominati, {skipped} saltati.")

    def rebuild_table(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for key, track in self.tracks.items():
            self.tree.insert(
                "",
                END,
                iid=key,
                values=(
                    track.path.name,
                    track.tags["title"],
                    track.tags["artist"],
                    track.tags["album"],
                    track.tags["album_artist"],
                    track.tags["track"],
                    track.tags["genre"],
                    track.tags["date"],
                ),
            )
        self.apply_current_sort()

    def sort_by_column(self, column: str) -> None:
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False

        self.apply_current_sort()
        self.update_sort_headings()

    def apply_current_sort(self) -> None:
        if not self.sort_column:
            return

        items = list(self.tree.get_children())
        items.sort(key=lambda iid: self.sort_value(iid, self.sort_column or ""), reverse=self.sort_reverse)
        for index, iid in enumerate(items):
            self.tree.move(iid, "", index)

    def sort_value(self, iid: str, column: str):
        track = self.tracks.get(iid)
        if track is None:
            return ""
        if column == "file":
            return track.path.name.lower()
        if column == "track":
            value = track.tags.get("track", "").split("/")[0].strip()
            try:
                return int(value)
            except ValueError:
                return 10**9
        return track.tags.get(column, "").lower()

    def update_sort_headings(self) -> None:
        for column, label in self.tree_headings.items():
            suffix = ""
            if column == self.sort_column:
                suffix = " v" if self.sort_reverse else " ^"
            self.tree.heading(column, text=f"{label}{suffix}", command=lambda col=column: self.sort_by_column(col))

    def selected_tracks(self) -> list[Track]:
        return [self.tracks[iid] for iid in self.tree.selection() if iid in self.tracks]

    def on_selection_changed(self, _event=None) -> None:
        selection = self.selected_tracks()
        if len(selection) == 1:
            self.load_track_into_form(selection[0])
        elif len(selection) > 1:
            self.load_common_values_into_form(selection)
            if self.cover_path is None:
                self.clear_cover_preview(f"{len(selection)} brani selezionati")
            self.status_var.set(f"{len(selection)} brani selezionati.")

    def load_first_selected(self, _event=None) -> None:
        selection = self.selected_tracks()
        if selection:
            self.load_track_into_form(selection[0])

    def load_track_into_form(self, track: Track) -> None:
        self.set_form_values(track.tags)
        if self.cover_path is None:
            self.show_track_cover(track)
        self.status_var.set(f"Tag caricati da {track.path.name}.")

    def load_common_values_into_form(self, tracks: list[Track]) -> None:
        common_values: dict[str, str] = {}
        for field in TAG_FIELDS:
            values = [track.tags.get(field, "") for track in tracks]
            common_values[field] = values[0] if values and all(value == values[0] for value in values) else ""
        self.set_form_values(common_values)

    def set_form_values(self, values: dict[str, str]) -> None:
        self.loading_form = True
        try:
            for field in TAG_FIELDS:
                self.field_vars[field].set(values.get(field, ""))
        finally:
            self.loading_form = False
            self.dirty_fields.clear()

    def choose_cover(self) -> None:
        name = filedialog.askopenfilename(
            title="Scegli copertina",
            filetypes=(("Immagini", "*.jpg *.jpeg *.png"), ("Tutti i file", "*.*")),
        )
        if not name:
            return
        self.set_cover_path(Path(name))

    def set_cover_path(self, cover: Path) -> bool:
        if not cover.is_file() or cover.suffix.lower() not in COVER_EXTENSIONS:
            messagebox.showerror("Copertina non valida", "Scegli un file JPG o PNG.")
            return False
        self.cover_path = cover
        self.cover_label.configure(text=cover.name)
        self.show_cover_file(cover)
        return True

    def clear_cover(self) -> None:
        self.cover_path = None
        self.cover_label.configure(text="Nessuna copertina scelta")
        selection = self.selected_tracks()
        if len(selection) == 1:
            self.show_track_cover(selection[0])
        else:
            self.clear_cover_preview()

    def clear_cover_preview(self, text: str = "Nessuna copertina") -> None:
        self.cover_preview = None
        self.cover_preview_label.configure(image="", text=text)

    def show_cover_bytes(self, data: bytes | None) -> None:
        if not data:
            self.clear_cover_preview()
            return
        try:
            preview = cover_preview_from_bytes(data)
        except Exception:
            preview = None
        if preview is None:
            self.clear_cover_preview("Anteprima non disponibile")
            return
        self.cover_preview = preview
        self.cover_preview_label.configure(image=self.cover_preview, text="")

    def show_cover_file(self, path: Path) -> None:
        try:
            self.show_cover_bytes(path.read_bytes())
        except Exception:
            self.clear_cover_preview("Anteprima non disponibile")

    def show_track_cover(self, track: Track) -> None:
        self.show_cover_bytes(read_cover_bytes(track.path))

    def form_values(self) -> dict[str, str]:
        return {field: var.get() for field, var in self.field_vars.items()}

    def apply_to_selected(self) -> None:
        tracks = self.selected_tracks()
        if not tracks:
            messagebox.showinfo("Nessuna selezione", "Seleziona uno o piu brani.")
            return
        raw_values = self.form_values()
        changed_fields = set(self.dirty_fields)
        if not changed_fields and self.cover_path is None:
            messagebox.showinfo("Nessuna modifica", "Modifica almeno un campo o scegli una copertina.")
            return

        errors: list[str] = []
        for track in tracks:
            values = self.values_for_track(track, raw_values, changed_fields)
            try:
                write_tags(track.path, values, self.cover_path)
                for field in changed_fields:
                    track.tags[field] = values.get(field, "")
                self.refresh_row(track)
            except Exception as exc:
                errors.append(f"{track.path.name}: {exc}")
        if errors:
            messagebox.showerror("Alcuni tag non sono stati salvati", "\n".join(errors[:8]))
        self.apply_current_sort()
        if not errors:
            self.dirty_fields.clear()
        self.status_var.set(f"Tag applicati a {len(tracks) - len(errors)} brani.")

    def apply_cover_to_selected(self) -> None:
        tracks = self.selected_tracks()
        if not tracks:
            messagebox.showinfo("Nessuna selezione", "Seleziona uno o piu brani.")
            return
        if self.cover_path is None:
            messagebox.showinfo("Nessuna copertina", "Scegli o trascina prima una copertina JPG o PNG.")
            return

        errors: list[str] = []
        for track in tracks:
            try:
                write_tags(track.path, dict(track.tags), self.cover_path)
            except Exception as exc:
                errors.append(f"{track.path.name}: {exc}")

        if errors:
            messagebox.showerror("Alcune copertine non sono state salvate", "\n".join(errors[:8]))
        self.status_var.set(f"Copertina applicata a {len(tracks) - len(errors)} brani.")

    def values_for_track(self, track: Track, raw_values: dict[str, str], changed_fields: set[str]) -> dict[str, str]:
        values = dict(track.tags)
        for field in changed_fields:
            values[field] = raw_values.get(field, "")
        return values

    def refresh_row(self, track: Track) -> None:
        key = str(track.path.resolve())
        self.tree.item(
            key,
            values=(
                track.path.name,
                track.tags["title"],
                track.tags["artist"],
                track.tags["album"],
                track.tags["album_artist"],
                track.tags["track"],
                track.tags["genre"],
                track.tags["date"],
            ),
        )

    def convert_selected(self) -> None:
        self.start_conversion(self.selected_tracks())

    def convert_all(self) -> None:
        self.start_conversion(list(self.tracks.values()))

    def start_conversion(self, tracks: list[Track]) -> None:
        if not tracks:
            messagebox.showinfo("Nessun brano", "Aggiungi o seleziona almeno un brano.")
            return
        mp3_count = sum(1 for track in tracks if track.path.suffix.lower() == ".mp3")
        tracks_to_convert = [track for track in tracks if track.path.suffix.lower() != ".mp3"]
        if not tracks_to_convert:
            messagebox.showinfo("Nessuna conversione", "I brani scelti sono gia MP3: non c'e nulla da convertire.")
            self.status_var.set(f"{mp3_count} MP3 gia pronti, nessuna conversione necessaria.")
            return
        bitrate = self.bitrate_var.get()
        if mp3_count:
            self.status_var.set(f"Conversione in corso: {mp3_count} MP3 saltati.")
        else:
            self.status_var.set("Conversione in corso...")
        thread = threading.Thread(target=self.convert_worker, args=(tracks_to_convert, bitrate, mp3_count), daemon=True)
        thread.start()

    def convert_worker(self, tracks: list[Track], bitrate: str, skipped: int = 0) -> None:
        errors: list[str] = []
        converted_paths: list[tuple[str, Track, Path]] = []
        converted = 0
        for track in tracks:
            destination = unique_destination(track.path.with_suffix(".mp3"))
            try:
                run_ffmpeg(track.path, destination, bitrate)
                if track.tags:
                    write_tags(destination, track.tags, None)
                converted += 1
                converted_paths.append((str(track.path.resolve()), track, destination))
                if skipped:
                    message = f"Convertiti {converted}/{len(tracks)} brani non MP3... ({skipped} MP3 saltati)"
                else:
                    message = f"Convertiti {converted}/{len(tracks)} brani..."
                self.root.after(0, self.status_var.set, message)
            except subprocess.CalledProcessError as exc:
                detail = exc.stderr.decode(errors="ignore").strip().splitlines()[-1:] or [str(exc)]
                errors.append(f"{track.path.name}: {detail[0]}")
            except Exception as exc:
                errors.append(f"{track.path.name}: {exc}")

        def finish() -> None:
            if converted_paths:
                updated_tracks = dict(self.tracks)
                for old_key, track, destination in converted_paths:
                    track.path = destination
                    updated_tracks.pop(old_key, None)
                    updated_tracks[str(destination.resolve())] = track
                self.tracks = updated_tracks
                self.rebuild_table()

            if skipped:
                self.status_var.set(f"Conversione completata: {converted}/{len(tracks)} convertiti, {skipped} MP3 saltati.")
            else:
                self.status_var.set(f"Conversione completata: {converted}/{len(tracks)} brani.")
            if errors:
                messagebox.showerror("Errori di conversione", "\n".join(errors[:8]))
            else:
                extra = f"\n{skipped} file MP3 gia esistenti sono stati saltati." if skipped else ""
                messagebox.showinfo("Conversione completata", f"{converted} file MP3 creati accanto ai file originali.{extra}")

        self.root.after(0, finish)

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    if platform.system() == "Windows":
        try:
            from ctypes import windll

            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    initial_paths = [Path(arg) for arg in sys.argv[1:]]
    TagEditorApp(initial_paths).run()
