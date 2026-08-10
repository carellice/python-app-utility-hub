"""Motore di conversione, indipendente dall'interfaccia grafica."""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image, ImageOps


SUPPORTED_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
)
_NUMBER_RE = re.compile(r"(\d+)")

LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int, int, str], None]


class ExistingFilePolicy(str, Enum):
    """Comportamento da adottare quando il PDF di destinazione esiste."""

    OVERWRITE = "overwrite"
    SKIP = "skip"
    NUMBERED_COPY = "numbered_copy"


@dataclass(slots=True)
class ConversionSummary:
    """Statistiche prodotte da una conversione completa."""

    folders_found: int = 0
    pdfs_created: int = 0
    folders_skipped: int = 0
    images_failed: int = 0
    errors: list[str] = field(default_factory=list)
    output_files: list[Path] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.errors)


def natural_sort_key(path: Path) -> tuple[tuple[tuple[int, object], ...], str]:
    """Restituisce una chiave che ordina ``2.png`` prima di ``10.png``."""

    components: list[tuple[int, object]] = []
    for part in _NUMBER_RE.split(path.name.casefold()):
        if part.isdigit():
            components.append((1, int(part)))
        else:
            components.append((0, part))
    return tuple(components), path.name.casefold()


def natural_sorted(paths: Iterable[Path]) -> list[Path]:
    return sorted(paths, key=natural_sort_key)


class ImageFolderConverter:
    """Converte la sorgente o le sue sottocartelle dirette in PDF omonimi."""

    def __init__(
        self,
        source_directory: Path | str,
        output_directory: Path | str,
        existing_policy: ExistingFilePolicy = ExistingFilePolicy.OVERWRITE,
        *,
        on_log: LogCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> None:
        self.source_directory = Path(source_directory).expanduser()
        self.output_directory = Path(output_directory).expanduser()
        self.existing_policy = ExistingFilePolicy(existing_policy)
        self.on_log = on_log or (lambda _message: None)
        self.on_progress = on_progress or (
            lambda _completed, _total, _folder: None
        )

    def run(self) -> ConversionSummary:
        """Esegue l'intero ciclo e restituisce il riepilogo."""

        source = self.source_directory.resolve()
        output = self.output_directory.resolve()

        if not source.is_dir():
            raise ValueError("La cartella principale non esiste o non è accessibile.")

        try:
            direct_images = self._find_supported_images(source)
        except OSError as exc:
            raise ValueError(
                f"Impossibile leggere la cartella principale: {exc}"
            ) from exc

        if direct_images:
            folders = [source]
            self.on_log(
                f"[INFO] Modalità cartella singola: trovate "
                f"{len(direct_images)} immagini in {source.name}. "
                "Le sottocartelle non verranno analizzate."
            )
        else:
            folders = self._find_direct_subfolders(source, output)
            self.on_log(
                f"[INFO] Nessuna immagine nella cartella selezionata. "
                f"Trovate {len(folders)} sottocartelle da analizzare."
            )

        summary = ConversionSummary(folders_found=len(folders))
        output.mkdir(parents=True, exist_ok=True)

        if not folders:
            self.on_progress(0, 0, "")
            return summary

        for index, folder in enumerate(folders, start=1):
            self.on_progress(index - 1, len(folders), folder.name)
            try:
                selected_images = direct_images if folder == source else None
                self._convert_folder(
                    folder, output, summary, image_paths=selected_images
                )
            except Exception as exc:  # un errore di una cartella non ferma il ciclo
                message = f"{folder.name}: {exc}"
                summary.errors.append(message)
                summary.folders_skipped += 1
                self.on_log(f"[ERRORE] {message}")
            finally:
                self.on_progress(index, len(folders), folder.name)

        return summary

    def _find_direct_subfolders(self, source: Path, output: Path) -> list[Path]:
        try:
            candidates = [entry for entry in source.iterdir() if entry.is_dir()]
        except OSError as exc:
            raise ValueError(
                f"Impossibile leggere la cartella principale: {exc}"
            ) from exc

        # Se l'output è una cartella diretta della sorgente, non è un capitolo.
        candidates = [
            folder for folder in candidates if folder.resolve() != output
        ]
        return natural_sorted(candidates)

    def _convert_folder(
        self,
        folder: Path,
        output: Path,
        summary: ConversionSummary,
        *,
        image_paths: list[Path] | None = None,
    ) -> None:
        if image_paths is None:
            try:
                image_paths = self._find_supported_images(folder)
            except OSError as exc:
                raise OSError(f"impossibile leggere la cartella ({exc})") from exc

        if not image_paths:
            summary.folders_skipped += 1
            self.on_log(
                f"[IGNORATA] {folder.name}: nessuna immagine trovata"
            )
            return

        requested_target = output / f"{folder.name}.pdf"
        target = self._resolve_target(requested_target)
        if target is None:
            summary.folders_skipped += 1
            self.on_log(
                f"[SALTATA] {folder.name}: {requested_target.name} esiste già"
            )
            return

        pages: list[Image.Image] = []
        try:
            for image_path in image_paths:
                try:
                    pages.append(self._read_page(image_path))
                except Exception as exc:
                    relative_name = f"{folder.name}/{image_path.name}"
                    message = f"{relative_name}: immagine non leggibile ({exc})"
                    summary.images_failed += 1
                    summary.errors.append(message)
                    self.on_log(f"[ERRORE] {message}")

            if not pages:
                summary.folders_skipped += 1
                self.on_log(
                    f"[IGNORATA] {folder.name}: nessuna immagine valida"
                )
                return

            self._save_pdf_atomically(pages, target)
        finally:
            for page in pages:
                page.close()

        summary.pdfs_created += 1
        summary.output_files.append(target)
        self.on_log(
            f"[OK] Creato {target.name} con {len(pages)} "
            f"{'pagina' if len(pages) == 1 else 'pagine'} valide"
        )

    @staticmethod
    def _find_supported_images(folder: Path) -> list[Path]:
        return natural_sorted(
            path
            for path in folder.iterdir()
            if path.is_file() and path.suffix.casefold() in SUPPORTED_EXTENSIONS
        )

    def _resolve_target(self, requested_target: Path) -> Path | None:
        if not requested_target.exists():
            return requested_target
        if self.existing_policy is ExistingFilePolicy.OVERWRITE:
            return requested_target
        if self.existing_policy is ExistingFilePolicy.SKIP:
            return None

        counter = 1
        while True:
            candidate = requested_target.with_name(
                f"{requested_target.stem} ({counter}){requested_target.suffix}"
            )
            if not candidate.exists():
                return candidate
            counter += 1

    @staticmethod
    def _read_page(image_path: Path) -> Image.Image:
        """Carica, orienta e converte un'immagine in una pagina RGB autonoma."""

        with Image.open(image_path) as source:
            source.seek(0)
            source.load()
            oriented = ImageOps.exif_transpose(source)

            try:
                has_alpha = oriented.mode in {"RGBA", "LA"} or (
                    "transparency" in oriented.info
                )
                if has_alpha:
                    rgba = oriented.convert("RGBA")
                    try:
                        page = Image.new("RGB", rgba.size, "white")
                        page.paste(rgba, mask=rgba.getchannel("A"))
                        return page
                    finally:
                        rgba.close()

                if oriented.mode == "RGB":
                    return oriented.copy()
                return oriented.convert("RGB")
            finally:
                if oriented is not source:
                    oriented.close()

    @staticmethod
    def _save_pdf_atomically(pages: list[Image.Image], target: Path) -> None:
        """Scrive prima un file temporaneo per non lasciare PDF incompleti."""

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=".immagini-in-pdf-",
                suffix=".pdf",
                dir=target.parent,
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)

            first, *remaining = pages
            first.save(
                temporary_path,
                format="PDF",
                save_all=True,
                append_images=remaining,
                resolution=96.0,
                quality=100,
                subsampling=0,
                optimize=True,
            )
            os.replace(temporary_path, target)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
