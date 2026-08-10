from __future__ import annotations

import re
import shutil
import subprocess
import threading
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from queue import Queue
from tempfile import TemporaryDirectory
from tkinter import BooleanVar, StringVar, Tk, filedialog, messagebox, ttk

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:  # pragma: no cover - shown in the GUI at runtime
    PdfReader = None
    PdfWriter = None

try:
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover - shown in the GUI at runtime
    Image = None
    ImageOps = None


SUPPORTED_EXTENSIONS = {".pdf"}
CBR_EXTENSION = ".cbr"
CBZ_EXTENSION = ".cbz"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


@dataclass(frozen=True)
class ComicMetadata:
    path: Path
    title: str
    author: str
    year: str
    series: str
    number: str


@dataclass(frozen=True)
class ArchiveConversionResult:
    converted: int
    skipped: int
    errors: list[str]


def clean_piece(value: str) -> str:
    value = value.replace("_", " ").replace(".", " ")
    value = re.sub(r"\s+", " ", value).strip(" -_.,")
    return value


def natural_sort_key(path: Path) -> list[int | str]:
    return [
        int(piece) if piece.isdigit() else piece.lower()
        for piece in re.split(r"(\d+)", str(path))
    ]


def metadata_from_filename(path: Path) -> ComicMetadata:
    raw_title = path.stem
    parsed_name = clean_piece(path.stem)
    author = ""
    year = ""
    series = ""
    number = ""

    year_match = re.search(r"\((\d{4})\)\s*$", parsed_name)
    if year_match:
        year = year_match.group(1)
        parsed_name = clean_piece(parsed_name[: year_match.start()])

    parts = [clean_piece(part) for part in re.split(r"\s+-\s+", parsed_name, maxsplit=1)]
    if len(parts) == 2 and parts[0] and parts[1]:
        left, right = parts
        volume_match = re.match(r"^(?P<series>.+?)\s+(?P<number>\d{1,4})$", left)
        if volume_match:
            series = clean_piece(volume_match.group("series"))
            number = volume_match.group("number")
        else:
            author = left
    else:
        volume_match = re.match(
            r"^(?P<series>.+?)\s+(?P<number>\d{1,4})\s+(?P<title>.+)$",
            parsed_name,
        )
        if volume_match:
            series = clean_piece(volume_match.group("series"))
            number = volume_match.group("number")

    return ComicMetadata(
        path=path,
        title=raw_title,
        author=author,
        year=year,
        series=series,
        number=number,
    )


def build_pdf_metadata(comic: ComicMetadata) -> dict[str, str]:
    metadata = {
        "/Title": comic.title,
        "/Producer": "Comic Tag Editor",
    }
    if comic.author:
        metadata["/Author"] = comic.author
    if comic.year:
        metadata["/CreationDate"] = f"D:{comic.year}0101000000"

    keywords = []
    if comic.series:
        metadata["/Subject"] = comic.series
        metadata["/Series"] = comic.series
        keywords.append(f"Serie: {comic.series}")
    if comic.number:
        metadata["/SeriesIndex"] = comic.number
        keywords.append(f"Numero: {comic.number}")
    if comic.year:
        keywords.append(f"Anno: {comic.year}")
    if keywords:
        metadata["/Keywords"] = "; ".join(keywords)

    return metadata


def update_pdf_metadata(comic: ComicMetadata, create_backup: bool) -> None:
    if PdfReader is None or PdfWriter is None:
        raise RuntimeError(
            "La libreria pypdf non è installata. Esegui: pip install -r requirements.txt"
        )

    source = comic.path
    tmp_path = source.with_suffix(source.suffix + ".tmp")
    backup_path = source.with_suffix(source.suffix + ".bak")

    reader = PdfReader(str(source))
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    existing_metadata = {}
    if reader.metadata:
        existing_metadata.update(
            {key: str(value) for key, value in reader.metadata.items() if value}
        )
    existing_metadata.update(build_pdf_metadata(comic))
    writer.add_metadata(existing_metadata)

    with tmp_path.open("wb") as output_file:
        writer.write(output_file)

    if create_backup and not backup_path.exists():
        shutil.copy2(source, backup_path)

    tmp_path.replace(source)


def find_cbr_extractor() -> list[str] | None:
    for command in ("unar", "bsdtar", "7z", "7zz"):
        command_path = shutil.which(command)
        if command_path:
            return [command_path]
    return None


def extract_cbr(cbr_path: Path, destination: Path) -> None:
    extractor = find_cbr_extractor()
    if extractor is None:
        raise RuntimeError(
            "Per convertire CBR serve un estrattore RAR: installa unar, 7-Zip "
            "oppure usa un sistema con bsdtar compatibile con RAR."
        )

    command_name = Path(extractor[0]).name.lower()
    if command_name == "unar":
        command = [
            *extractor,
            "-quiet",
            "-force-overwrite",
            "-output-directory",
            str(destination),
            str(cbr_path),
        ]
    elif command_name == "bsdtar":
        command = [*extractor, "-xf", str(cbr_path), "-C", str(destination)]
    else:
        command = [*extractor, "x", "-y", f"-o{destination}", str(cbr_path)]

    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"Impossibile estrarre {cbr_path.name}: {details}")


def extract_cbz(cbz_path: Path, destination: Path) -> None:
    destination = destination.resolve()
    try:
        with zipfile.ZipFile(cbz_path) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue

                member_path = destination / member.filename
                target_path = member_path.resolve()
                if (
                    destination != target_path
                    and destination not in target_path.parents
                ):
                    raise RuntimeError(
                        f"Percorso non valido nell'archivio: {member.filename}"
                    )

                target_path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, target_path.open("wb") as target:
                    shutil.copyfileobj(source, target)
    except zipfile.BadZipFile as exc:
        raise RuntimeError(f"Archivio CBZ non valido: {cbz_path.name}") from exc


def image_files_in_folder(folder: Path) -> list[Path]:
    image_paths = [
        path
        for path in folder.rglob("*")
        if path.is_file()
        and path.suffix.lower() in IMAGE_EXTENSIONS
        and "__MACOSX" not in path.parts
        and not path.name.startswith("._")
    ]
    return sorted(image_paths, key=lambda path: natural_sort_key(path.relative_to(folder)))


def image_to_pdf_page(path: Path):
    if Image is None or ImageOps is None:
        raise RuntimeError(
            "La libreria Pillow non è installata. Esegui: pip install -r requirements.txt"
        )

    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        if image.mode == "RGB":
            return image.copy()

        if image.mode in {"RGBA", "LA"} or (
            image.mode == "P" and "transparency" in image.info
        ):
            background = Image.new("RGB", image.size, "white")
            alpha_source = image.convert("RGBA")
            background.paste(alpha_source, mask=alpha_source.getchannel("A"))
            return background

        return image.convert("RGB")


def archive_to_pdf(
    archive_path: Path, extract_archive: Callable[[Path, Path], None]
) -> Path:
    output_path = archive_path.with_suffix(".pdf")
    if output_path.exists():
        raise FileExistsError(f"{output_path.name} esiste già")

    with TemporaryDirectory(prefix="comic-tag-editor-") as temp_folder:
        extract_folder = Path(temp_folder)
        extract_archive(archive_path, extract_folder)
        image_paths = image_files_in_folder(extract_folder)
        if not image_paths:
            raise RuntimeError(f"Nessuna immagine trovata in {archive_path.name}")

        pages = [image_to_pdf_page(path) for path in image_paths]
        try:
            first_page, remaining_pages = pages[0], pages[1:]
            first_page.save(
                output_path, "PDF", save_all=True, append_images=remaining_pages
            )
        finally:
            for page in pages:
                page.close()

    return output_path


def cbr_to_pdf(cbr_path: Path) -> Path:
    return archive_to_pdf(cbr_path, extract_cbr)


def cbz_to_pdf(cbz_path: Path) -> Path:
    return archive_to_pdf(cbz_path, extract_cbz)


def convert_archive_files(
    archive_files: list[Path], converter: Callable[[Path], Path]
) -> ArchiveConversionResult:
    converted = 0
    skipped = 0
    errors = []

    for archive_file in archive_files:
        try:
            converter(archive_file)
            converted += 1
        except FileExistsError:
            skipped += 1
        except Exception as exc:
            errors.append(f"{archive_file.name}: {exc}")

    return ArchiveConversionResult(converted=converted, skipped=skipped, errors=errors)


def convert_cbr_files(cbr_files: list[Path]) -> ArchiveConversionResult:
    return convert_archive_files(cbr_files, cbr_to_pdf)


def convert_cbz_files(cbz_files: list[Path]) -> ArchiveConversionResult:
    return convert_archive_files(cbz_files, cbz_to_pdf)


def conversion_message(label: str, result: ArchiveConversionResult) -> str:
    message = f"{label} convertiti: {result.converted}."
    if result.skipped:
        message += f" Saltati perché il PDF esiste già: {result.skipped}."
    if result.errors:
        message += f" Errori: {len(result.errors)}. {result.errors[0]}"
    return message


def conversion_event_type(result: ArchiveConversionResult) -> str:
    return "converted_error" if result.errors else "converted"


class ComicTagEditorApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("Comic Tag Editor")
        self.root.geometry("1180x600")
        self.root.minsize(1040, 480)

        self.folder_var = StringVar()
        self.folder_series_var = StringVar()
        self.folder_author_var = StringVar()
        self.selected_pdf_var = StringVar(value="Nessun PDF selezionato")
        self.selected_series_var = StringVar()
        self.selected_author_var = StringVar()
        self.status_var = StringVar(value="Seleziona una cartella con PDF, CBR o CBZ.")
        self.backup_var = BooleanVar(value=True)
        self.comics: list[ComicMetadata] = []
        self.cbr_files: list[Path] = []
        self.cbz_files: list[Path] = []
        self.file_overrides: dict[Path, dict[str, str]] = {}
        self.item_paths: dict[str, Path] = {}
        self.item_types: dict[str, str] = {}
        self.selected_pdf_path: Path | None = None
        self.events: Queue[tuple[str, str]] = Queue()

        self._build_ui()
        self.folder_series_var.trace_add("write", self._shared_metadata_changed)
        self.folder_author_var.trace_add("write", self._shared_metadata_changed)
        self._check_worker_events()

    def _build_ui(self) -> None:
        root_frame = ttk.Frame(self.root, padding=12)
        root_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        root_frame.columnconfigure(0, weight=1)
        root_frame.rowconfigure(2, weight=1)

        top_bar = ttk.Frame(root_frame)
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top_bar.columnconfigure(1, weight=1)

        ttk.Button(top_bar, text="Scegli cartella", command=self.choose_folder).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Entry(top_bar, textvariable=self.folder_var, state="readonly").grid(
            row=0, column=1, sticky="ew", padx=(0, 8)
        )
        self.scan_button = ttk.Button(top_bar, text="Ricarica", command=self.scan_folder)
        self.scan_button.grid(row=0, column=2, padx=(0, 8))
        self.convert_cbr_button = ttk.Button(
            top_bar,
            text="Converti CBR in PDF",
            command=self.convert_cbrs,
            state="disabled",
        )
        self.convert_cbr_button.grid(row=0, column=3, padx=(0, 8))
        self.convert_cbz_button = ttk.Button(
            top_bar,
            text="Converti CBZ in PDF",
            command=self.convert_cbzs,
            state="disabled",
        )
        self.convert_cbz_button.grid(row=0, column=4, padx=(0, 8))
        self.apply_button = ttk.Button(
            top_bar,
            text="Scrivi metadati",
            command=self.apply_metadata,
            state="disabled",
        )
        self.apply_button.grid(row=0, column=5)

        metadata_bar = ttk.Frame(root_frame)
        metadata_bar.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        metadata_bar.columnconfigure(1, weight=1)
        metadata_bar.columnconfigure(3, weight=1)

        ttk.Label(metadata_bar, text="Serie per Kobo").grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        ttk.Entry(metadata_bar, textvariable=self.folder_series_var).grid(
            row=0, column=1, sticky="ew", padx=(0, 12)
        )
        ttk.Label(metadata_bar, text="Autori per Kobo").grid(
            row=0, column=2, sticky="w", padx=(0, 8)
        )
        ttk.Entry(metadata_bar, textvariable=self.folder_author_var).grid(
            row=0, column=3, sticky="ew"
        )

        columns = ("file", "type", "title", "author", "year", "series", "number")
        self.tree = ttk.Treeview(root_frame, columns=columns, show="headings", height=14)
        headings = {
            "file": "File",
            "type": "Tipo",
            "title": "Titolo",
            "author": "Autore",
            "year": "Anno",
            "series": "Serie",
            "number": "N.",
        }
        widths = {
            "file": 230,
            "type": 60,
            "title": 240,
            "author": 140,
            "year": 70,
            "series": 130,
            "number": 50,
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], minwidth=widths[column] // 2)

        scrollbar = ttk.Scrollbar(root_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self._selection_changed)
        self.tree.grid(row=2, column=0, sticky="nsew")
        scrollbar.grid(row=2, column=1, sticky="ns")

        selected_bar = ttk.LabelFrame(root_frame, text="PDF selezionato", padding=10)
        selected_bar.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        selected_bar.columnconfigure(1, weight=1)
        selected_bar.columnconfigure(3, weight=1)

        ttk.Label(selected_bar, textvariable=self.selected_pdf_var).grid(
            row=0, column=0, columnspan=7, sticky="w", pady=(0, 8)
        )
        ttk.Label(selected_bar, text="Serie").grid(
            row=1, column=0, sticky="w", padx=(0, 8)
        )
        self.selected_series_entry = ttk.Entry(
            selected_bar, textvariable=self.selected_series_var, state="disabled"
        )
        self.selected_series_entry.grid(row=1, column=1, sticky="ew", padx=(0, 12))
        ttk.Label(selected_bar, text="Autore").grid(
            row=1, column=2, sticky="w", padx=(0, 8)
        )
        self.selected_author_entry = ttk.Entry(
            selected_bar, textvariable=self.selected_author_var, state="disabled"
        )
        self.selected_author_entry.grid(row=1, column=3, sticky="ew", padx=(0, 12))
        self.save_selected_button = ttk.Button(
            selected_bar,
            text="Salva su questo PDF",
            command=self.save_selected_override,
            state="disabled",
        )
        self.save_selected_button.grid(row=1, column=4, padx=(0, 8))
        self.copy_title_selected_button = ttk.Button(
            selected_bar,
            text="Serie/Autore = Titolo",
            command=self.set_selected_fields_from_title,
            state="disabled",
        )
        self.copy_title_selected_button.grid(row=1, column=5, padx=(0, 8))
        self.clear_selected_button = ttk.Button(
            selected_bar,
            text="Usa valori globali",
            command=self.clear_selected_override,
            state="disabled",
        )
        self.clear_selected_button.grid(row=1, column=6)

        bottom_bar = ttk.Frame(root_frame)
        bottom_bar.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        bottom_bar.columnconfigure(1, weight=1)

        ttk.Checkbutton(
            bottom_bar,
            text="Crea backup .bak prima di salvare",
            variable=self.backup_var,
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(bottom_bar, textvariable=self.status_var).grid(
            row=0, column=1, sticky="e"
        )

    def choose_folder(self) -> None:
        folder = filedialog.askdirectory(title="Scegli cartella fumetti")
        if folder:
            self.folder_var.set(folder)
            self.folder_series_var.set(clean_piece(Path(folder).name))
            self.scan_folder()

    def scan_folder(self) -> None:
        folder_text = self.folder_var.get()
        if not folder_text:
            messagebox.showinfo("Comic Tag Editor", "Scegli prima una cartella.")
            return

        folder = Path(folder_text)
        if not folder.exists():
            messagebox.showerror("Comic Tag Editor", "La cartella selezionata non esiste.")
            return

        if not self.folder_series_var.get().strip():
            self.folder_series_var.set(clean_piece(folder.name))

        self.comics = [
            metadata_from_filename(path)
            for path in sorted(folder.iterdir(), key=lambda item: item.name.lower())
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        self.cbr_files = [
            path
            for path in sorted(folder.iterdir(), key=lambda item: item.name.lower())
            if path.is_file() and path.suffix.lower() == CBR_EXTENSION
        ]
        self.cbz_files = [
            path
            for path in sorted(folder.iterdir(), key=lambda item: item.name.lower())
            if path.is_file() and path.suffix.lower() == CBZ_EXTENSION
        ]
        current_pdf_paths = {comic.path for comic in self.comics}
        self.file_overrides = {
            path: override
            for path, override in self.file_overrides.items()
            if path in current_pdf_paths
        }
        self.selected_pdf_path = None
        self.selected_pdf_var.set("Nessun PDF selezionato")
        self.selected_series_var.set("")
        self.selected_author_var.set("")
        self._set_selected_editor_enabled(False)
        self.refresh_table()

    def metadata_with_shared_fields(self, comic: ComicMetadata) -> ComicMetadata:
        folder_series = self.folder_series_var.get().strip()
        folder_author = self.folder_author_var.get().strip()
        return replace(
            comic,
            author=folder_author or comic.author,
            series=folder_series or comic.series,
        )

    def metadata_with_all_overrides(self, comic: ComicMetadata) -> ComicMetadata:
        comic = self.metadata_with_shared_fields(comic)
        override = self.file_overrides.get(comic.path)
        if override is None:
            return comic

        return replace(
            comic,
            author=override.get("author", comic.author),
            series=override.get("series", comic.series),
        )

    def comics_with_all_overrides(self) -> list[ComicMetadata]:
        return [self.metadata_with_all_overrides(comic) for comic in self.comics]

    def refresh_table(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.item_paths = {}
        self.item_types = {}
        item_to_select = None

        for comic in self.comics_with_all_overrides():
            item_id = self.tree.insert(
                "",
                "end",
                values=(
                    comic.path.name,
                    "PDF",
                    comic.title,
                    comic.author,
                    comic.year,
                    comic.series,
                    comic.number,
                ),
            )
            self.item_paths[item_id] = comic.path
            self.item_types[item_id] = "PDF"
            if comic.path == self.selected_pdf_path:
                item_to_select = item_id

        for cbr_file in self.cbr_files:
            comic = self.metadata_with_shared_fields(metadata_from_filename(cbr_file))
            item_id = self.tree.insert(
                "",
                "end",
                values=(
                    comic.path.name,
                    "CBR",
                    comic.title,
                    comic.author,
                    comic.year,
                    comic.series,
                    comic.number,
                ),
            )
            self.item_paths[item_id] = comic.path
            self.item_types[item_id] = "CBR"

        for cbz_file in self.cbz_files:
            comic = self.metadata_with_shared_fields(metadata_from_filename(cbz_file))
            item_id = self.tree.insert(
                "",
                "end",
                values=(
                    comic.path.name,
                    "CBZ",
                    comic.title,
                    comic.author,
                    comic.year,
                    comic.series,
                    comic.number,
                ),
            )
            self.item_paths[item_id] = comic.path
            self.item_types[item_id] = "CBZ"

        count = len(self.comics)
        cbr_count = len(self.cbr_files)
        cbz_count = len(self.cbz_files)
        self.apply_button.configure(state="normal" if count else "disabled")
        self.convert_cbr_button.configure(state="normal" if cbr_count else "disabled")
        self.convert_cbz_button.configure(state="normal" if cbz_count else "disabled")
        pdf_text = f"{count} PDF trovato{'i' if count != 1 else ''}"
        cbr_text = f"{cbr_count} CBR trovato{'i' if cbr_count != 1 else ''}"
        cbz_text = f"{cbz_count} CBZ trovato{'i' if cbz_count != 1 else ''}"
        if count or cbr_count or cbz_count:
            self.status_var.set(f"{pdf_text}, {cbr_text}, {cbz_text}.")
        else:
            self.status_var.set("Nessun PDF, CBR o CBZ trovato nella cartella.")

        if item_to_select:
            self.tree.selection_set(item_to_select)
            self.tree.focus(item_to_select)
            self.tree.see(item_to_select)
        elif self.selected_pdf_path is not None:
            self.selected_pdf_path = None
            self._load_selected_pdf_values()

    def _shared_metadata_changed(self, *_args: object) -> None:
        if self.comics or self.cbr_files or self.cbz_files:
            self.refresh_table()
            self._load_selected_pdf_values()

    def _selection_changed(self, _event: object) -> None:
        selected_items = self.tree.selection()
        if not selected_items:
            self.selected_pdf_path = None
            self._load_selected_pdf_values()
            return

        item_id = selected_items[0]
        item_type = self.item_types.get(item_id)
        item_path = self.item_paths.get(item_id)
        if item_type != "PDF" or item_path is None:
            self.selected_pdf_path = None
            self.selected_pdf_var.set("Seleziona un PDF per modificare serie e autore")
            self.selected_series_var.set("")
            self.selected_author_var.set("")
            self._set_selected_editor_enabled(False)
            return

        self.selected_pdf_path = item_path
        self._load_selected_pdf_values()

    def _comic_by_path(self, path: Path) -> ComicMetadata | None:
        for comic in self.comics:
            if comic.path == path:
                return comic
        return None

    def _load_selected_pdf_values(self) -> None:
        if self.selected_pdf_path is None:
            self.selected_pdf_var.set("Nessun PDF selezionato")
            self.selected_series_var.set("")
            self.selected_author_var.set("")
            self._set_selected_editor_enabled(False)
            return

        comic = self._comic_by_path(self.selected_pdf_path)
        if comic is None:
            self.selected_pdf_path = None
            self._load_selected_pdf_values()
            return

        effective = self.metadata_with_all_overrides(comic)
        self.selected_pdf_var.set(f"File: {comic.path.name}")
        self.selected_series_var.set(effective.series)
        self.selected_author_var.set(effective.author)
        self._set_selected_editor_enabled(True)

    def _set_selected_editor_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.selected_series_entry.configure(state=state)
        self.selected_author_entry.configure(state=state)
        self.save_selected_button.configure(state=state)
        self.copy_title_selected_button.configure(state=state)
        self.clear_selected_button.configure(
            state=state
            if enabled and self.selected_pdf_path in self.file_overrides
            else "disabled"
        )

    def save_selected_override(self) -> None:
        if self.selected_pdf_path is None:
            return

        self.file_overrides[self.selected_pdf_path] = {
            "series": self.selected_series_var.get().strip(),
            "author": self.selected_author_var.get().strip(),
        }
        self.status_var.set(f"Modifica singola salvata per {self.selected_pdf_path.name}.")
        self.refresh_table()
        self._load_selected_pdf_values()

    def set_selected_fields_from_title(self) -> None:
        if self.selected_pdf_path is None:
            return

        comic = self._comic_by_path(self.selected_pdf_path)
        if comic is None:
            return

        self.selected_series_var.set(comic.title)
        self.selected_author_var.set(comic.title)
        self.save_selected_override()

    def clear_selected_override(self) -> None:
        if self.selected_pdf_path is None:
            return

        removed = self.file_overrides.pop(self.selected_pdf_path, None)
        if removed is not None:
            self.status_var.set(
                f"{self.selected_pdf_path.name} usa di nuovo serie e autori globali."
            )
        self.refresh_table()
        self._load_selected_pdf_values()

    def apply_metadata(self) -> None:
        if not self.comics:
            return

        comics_to_update = self.comics_with_all_overrides()
        create_backup = self.backup_var.get()
        self._set_busy(True)
        self.status_var.set("Scrittura metadati in corso...")
        worker = threading.Thread(
            target=self._apply_metadata_worker,
            args=(comics_to_update, create_backup),
            daemon=True,
        )
        worker.start()

    def convert_cbrs(self) -> None:
        if not self.cbr_files:
            return

        cbr_files = list(self.cbr_files)
        self._set_busy(True)
        self.status_var.set("Conversione CBR in PDF in corso...")
        worker = threading.Thread(
            target=self._convert_cbrs_worker,
            args=(cbr_files,),
            daemon=True,
        )
        worker.start()

    def convert_cbzs(self) -> None:
        if not self.cbz_files:
            return

        cbz_files = list(self.cbz_files)
        self._set_busy(True)
        self.status_var.set("Conversione CBZ in PDF in corso...")
        worker = threading.Thread(
            target=self._convert_cbzs_worker,
            args=(cbz_files,),
            daemon=True,
        )
        worker.start()

    def _convert_cbrs_worker(self, cbr_files: list[Path]) -> None:
        try:
            result = convert_cbr_files(cbr_files)
            self.events.put(
                (conversion_event_type(result), conversion_message("CBR", result))
            )
        except Exception as exc:  # pragma: no cover - user-facing safety net
            self.events.put(("error", str(exc)))

    def _convert_cbzs_worker(self, cbz_files: list[Path]) -> None:
        try:
            result = convert_cbz_files(cbz_files)
            self.events.put(
                (conversion_event_type(result), conversion_message("CBZ", result))
            )
        except Exception as exc:  # pragma: no cover - user-facing safety net
            self.events.put(("error", str(exc)))

    def _apply_metadata_worker(
        self, comics_to_update: list[ComicMetadata], create_backup: bool
    ) -> None:
        try:
            for comic in comics_to_update:
                update_pdf_metadata(comic, create_backup)
            self.events.put(
                ("done", f"Metadati aggiornati per {len(comics_to_update)} PDF.")
            )
        except Exception as exc:  # pragma: no cover - user-facing safety net
            self.events.put(("error", str(exc)))

    def _check_worker_events(self) -> None:
        while not self.events.empty():
            event_type, message = self.events.get()
            self._set_busy(False)
            self.status_var.set(message)
            if event_type in {"done", "converted"}:
                messagebox.showinfo("Comic Tag Editor", message)
                if event_type == "converted":
                    self.scan_folder()
            elif event_type == "converted_error":
                messagebox.showerror("Comic Tag Editor", message)
                self.scan_folder()
            else:
                messagebox.showerror("Comic Tag Editor", message)

        self.root.after(100, self._check_worker_events)

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.scan_button.configure(state=state)
        self.apply_button.configure(state=state if self.comics else "disabled")
        self.convert_cbr_button.configure(state=state if self.cbr_files else "disabled")
        self.convert_cbz_button.configure(state=state if self.cbz_files else "disabled")
        if busy:
            self._set_selected_editor_enabled(False)
        else:
            self._load_selected_pdf_values()


def main() -> None:
    root = Tk()
    app = ComicTagEditorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
