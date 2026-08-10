from __future__ import annotations

import hashlib
import math
import platform
import shutil
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError


SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
    ".heic",
    ".heif",
}
JPEG_EXTENSIONS = {".jpg", ".jpeg"}


@dataclass(frozen=True)
class PhotoInfo:
    path: Path
    rel_path: str
    sha256: str
    size_bytes: int
    mtime: float
    width: int | None = None
    height: int | None = None
    dhash: int | None = None
    color_signature: tuple[int, ...] | None = None
    quality_score: float = 0.0
    issue: str | None = None

    @property
    def megapixels(self) -> float:
        if not self.width or not self.height:
            return 0.0
        return (self.width * self.height) / 1_000_000


@dataclass(frozen=True)
class PhotoGroup:
    id: int
    kind: str
    photos: list[PhotoInfo]
    best_path: Path

    @property
    def count(self) -> int:
        return len(self.photos)


@dataclass(frozen=True)
class ScanResult:
    root: Path
    photos: list[PhotoInfo]
    groups: list[PhotoGroup]
    skipped: list[PhotoInfo]


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left == root_right:
            return
        if self.rank[root_left] < self.rank[root_right]:
            self.parent[root_left] = root_right
        elif self.rank[root_left] > self.rank[root_right]:
            self.parent[root_right] = root_left
        else:
            self.parent[root_right] = root_left
            self.rank[root_left] += 1


class BKTree:
    """Tiny BK-tree for fast Hamming-neighbor lookups over integer hashes."""

    def __init__(self) -> None:
        self.root: tuple[int, list[int], dict[int, object]] | None = None

    @staticmethod
    def distance(left: int, right: int) -> int:
        return (left ^ right).bit_count()

    def add(self, value: int, index: int) -> None:
        if self.root is None:
            self.root = (value, [index], {})
            return

        node = self.root
        while True:
            node_value, indexes, children = node
            distance = self.distance(value, node_value)
            if distance == 0:
                indexes.append(index)
                return
            child = children.get(distance)
            if child is None:
                children[distance] = (value, [index], {})
                return
            node = child  # type: ignore[assignment]

    def query(self, value: int, threshold: int) -> list[int]:
        matches: list[int] = []
        if self.root is None:
            return matches

        stack = [self.root]
        while stack:
            node_value, indexes, children = stack.pop()
            distance = self.distance(value, node_value)
            if distance <= threshold:
                matches.extend(indexes)
            for child_distance, child in children.items():
                if distance - threshold <= child_distance <= distance + threshold:
                    stack.append(child)  # type: ignore[arg-type]
        return matches


def iter_image_files(root: Path, recursive: bool) -> Iterable[Path]:
    pattern = "**/*" if recursive else "*"
    for path in root.glob(pattern):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def iter_jpeg_files(root: Path, recursive: bool) -> Iterable[Path]:
    pattern = "**/*" if recursive else "*"
    for path in root.glob(pattern):
        if path.is_file() and path.suffix.lower() in JPEG_EXTENSIONS:
            yield path


def jpeg_target_for(source: Path) -> Path:
    if source.suffix.lower() in JPEG_EXTENSIONS:
        return source
    return source.with_suffix(".jpg")


def convert_supported_images_to_jpeg(
    root: Path,
    recursive: bool,
    progress: Callable[[int, int, str], None] | None = None,
) -> tuple[list[Path], list[tuple[Path, str]]]:
    files = sorted(iter_image_files(root, recursive), key=lambda item: str(item).lower())
    candidates = [path for path in files if path.suffix.lower() not in JPEG_EXTENSIONS]
    converted: list[Path] = []
    failed: list[tuple[Path, str]] = []

    for index, source in enumerate(candidates, start=1):
        target = jpeg_target_for(source)
        if progress:
            progress(index - 1, len(candidates), f"Converto {source.name} in JPEG")
        if target.exists() and target.stat().st_mtime >= source.stat().st_mtime:
            converted.append(target)
            continue
        try:
            converted.append(convert_image_to_jpeg(source, target))
        except OSError as exc:
            failed.append((source, str(exc)))

    if progress and candidates:
        progress(len(candidates), len(candidates), "Conversione JPEG completata")
    return converted, failed


def convert_image_to_jpeg(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_target = target.with_name(f".{target.stem}.tmp.jpg")

    try:
        convert_with_pillow(source, temp_target)
    except (OSError, UnidentifiedImageError, ValueError):
        if temp_target.exists():
            temp_target.unlink()
        try:
            convert_with_platform_tool(source, temp_target)
        except OSError:
            if temp_target.exists():
                temp_target.unlink()
            raise

    if target.exists():
        target.unlink()
    temp_target.replace(target)
    return target


def convert_with_pillow(source: Path, target: Path) -> None:
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            background = Image.new("RGB", image.size, "#ffffff")
            alpha = image.convert("RGBA")
            background.paste(alpha, mask=alpha.getchannel("A"))
            output = background
        else:
            output = image.convert("RGB")
        output.save(target, "JPEG", quality=95, optimize=True)


def convert_with_platform_tool(source: Path, target: Path) -> None:
    if platform.system() == "Darwin" and shutil.which("sips"):
        result = subprocess.run(
            ["sips", "-s", "format", "jpeg", str(source), "--out", str(target)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0 and target.exists():
            return
    raise OSError(f"Non posso convertire {source.name} in JPEG")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_fingerprint(path: Path) -> tuple[int, int, int, tuple[int, ...], float]:
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        width, height = image.size

        gray = image.convert("L")
        hash_image = gray.resize((9, 8), Image.Resampling.LANCZOS)
        pixels = list(hash_image.getdata())
        dhash = 0
        for row in range(8):
            for col in range(8):
                left = pixels[row * 9 + col]
                right = pixels[row * 9 + col + 1]
                dhash = (dhash << 1) | int(left > right)

        color_image = image.convert("RGB").resize((4, 4), Image.Resampling.BILINEAR)
        color_signature: list[int] = []
        for red, green, blue in color_image.getdata():
            color_signature.extend((red, green, blue))

        quality_score = score_image(gray, width, height)
        return width, height, dhash, tuple(color_signature), quality_score


def score_image(gray: Image.Image, width: int, height: int) -> float:
    preview = gray.resize((256, 256), Image.Resampling.BILINEAR)
    pixels = list(preview.getdata())
    mean = sum(pixels) / len(pixels)
    exposure = max(0.0, 1.0 - abs(mean - 128.0) / 128.0)

    edges = preview.filter(ImageFilter.FIND_EDGES)
    edge_pixels = list(edges.getdata())
    edge_mean = sum(edge_pixels) / len(edge_pixels)
    edge_variance = sum((pixel - edge_mean) ** 2 for pixel in edge_pixels) / len(edge_pixels)
    sharpness = min(edge_variance / 1800.0, 3.0)

    megapixels = (width * height) / 1_000_000
    resolution = min(math.sqrt(megapixels), 6.0)
    return resolution * 2.0 + sharpness + exposure


def color_distance(left: tuple[int, ...] | None, right: tuple[int, ...] | None) -> float:
    if left is None or right is None:
        return 999.0
    return sum(abs(a - b) for a, b in zip(left, right)) / len(left)


def scan_folder(
    root: str | Path,
    recursive: bool = True,
    hamming_threshold: int = 8,
    color_threshold: int = 38,
    convert_to_jpeg: bool = True,
    progress: Callable[[int, int, str], None] | None = None,
) -> ScanResult:
    root_path = Path(root).expanduser().resolve()
    conversion_failures: list[tuple[Path, str]] = []
    if convert_to_jpeg:
        _converted, conversion_failures = convert_supported_images_to_jpeg(root_path, recursive, progress)
        files = sorted(iter_jpeg_files(root_path, recursive), key=lambda item: str(item).lower())
    else:
        files = sorted(iter_image_files(root_path, recursive), key=lambda item: str(item).lower())
    photos: list[PhotoInfo] = []

    for index, path in enumerate(files, start=1):
        if progress:
            progress(index - 1, len(files), f"Leggo {path.name}")
        stat = path.stat()
        sha256 = file_sha256(path)
        rel_path = str(path.relative_to(root_path))
        try:
            width, height, dhash, color_signature, quality_score = image_fingerprint(path)
            photo = PhotoInfo(
                path=path,
                rel_path=rel_path,
                sha256=sha256,
                size_bytes=stat.st_size,
                mtime=stat.st_mtime,
                width=width,
                height=height,
                dhash=dhash,
                color_signature=color_signature,
                quality_score=quality_score,
            )
        except (OSError, UnidentifiedImageError, ValueError) as exc:
            photo = PhotoInfo(
                path=path,
                rel_path=rel_path,
                sha256=sha256,
                size_bytes=stat.st_size,
                mtime=stat.st_mtime,
                issue=f"Non posso aprire questa immagine: {exc}",
            )
        photos.append(photo)

    if progress:
        progress(len(files), len(files), "Raggruppo duplicati e immagini simili")

    union = UnionFind(len(photos))
    by_sha: dict[str, list[int]] = defaultdict(list)
    for index, photo in enumerate(photos):
        by_sha[photo.sha256].append(index)
    for indexes in by_sha.values():
        for index in indexes[1:]:
            union.union(indexes[0], index)

    tree = BKTree()
    for index, photo in enumerate(photos):
        if photo.dhash is None:
            continue
        for candidate_index in tree.query(photo.dhash, hamming_threshold):
            candidate = photos[candidate_index]
            if color_distance(photo.color_signature, candidate.color_signature) <= color_threshold:
                union.union(index, candidate_index)
        tree.add(photo.dhash, index)

    components: dict[int, list[PhotoInfo]] = defaultdict(list)
    for index, photo in enumerate(photos):
        components[union.find(index)].append(photo)

    groups: list[PhotoGroup] = []
    for component in components.values():
        if len(component) < 2:
            continue
        readable = [photo for photo in component if photo.issue is None]
        candidates = readable or component
        best = max(
            candidates,
            key=lambda photo: (
                photo.quality_score,
                photo.megapixels,
                photo.size_bytes,
                -photo.mtime,
            ),
        )
        kind = "uguali" if len({photo.sha256 for photo in component}) == 1 else "simili"
        sorted_photos = sorted(
            component,
            key=lambda photo: (
                photo.path != best.path,
                -photo.quality_score,
                photo.rel_path.lower(),
            ),
        )
        groups.append(PhotoGroup(id=len(groups) + 1, kind=kind, photos=sorted_photos, best_path=best.path))

    groups.sort(key=lambda group: (group.kind != "uguali", -group.count, group.photos[0].rel_path.lower()))
    groups = [PhotoGroup(id=index + 1, kind=group.kind, photos=group.photos, best_path=group.best_path) for index, group in enumerate(groups)]
    skipped = [photo for photo in photos if photo.issue]
    skipped.extend(conversion_failure_to_photo(root_path, path, issue) for path, issue in conversion_failures)
    return ScanResult(root=root_path, photos=photos, groups=groups, skipped=skipped)


def conversion_failure_to_photo(root: Path, path: Path, issue: str) -> PhotoInfo:
    try:
        stat = path.stat()
        size = stat.st_size
        mtime = stat.st_mtime
        sha256 = file_sha256(path)
        rel_path = str(path.relative_to(root))
    except OSError:
        size = 0
        mtime = 0
        sha256 = ""
        rel_path = path.name

    return PhotoInfo(
        path=path,
        rel_path=rel_path,
        sha256=sha256,
        size_bytes=size,
        mtime=mtime,
        issue=f"Non posso convertire in JPEG: {issue}",
    )


def safe_move_to_trash(photo: PhotoInfo, trash_root: Path | None = None) -> Path:
    if trash_root is None and platform.system() == "Windows":
        return move_to_windows_recycle_bin(photo.path)

    trash = trash_root or Path.home() / ".Trash"
    trash.mkdir(parents=True, exist_ok=True)
    destination = trash / photo.path.name

    if destination.exists():
        stem = destination.stem
        suffix = destination.suffix
        counter = 2
        while True:
            candidate = destination.with_name(f"{stem}_{counter}{suffix}")
            if not candidate.exists():
                destination = candidate
                break
            counter += 1

    shutil.move(str(photo.path), str(destination))
    return destination


def move_to_windows_recycle_bin(path: Path) -> Path:
    import ctypes
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", wintypes.UINT),
            ("pFrom", wintypes.LPCWSTR),
            ("pTo", wintypes.LPCWSTR),
            ("fFlags", wintypes.USHORT),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", wintypes.LPVOID),
            ("lpszProgressTitle", wintypes.LPCWSTR),
        ]

    source = str(path.resolve()) + "\0\0"
    operation = SHFILEOPSTRUCTW()
    operation.wFunc = 0x0003
    operation.pFrom = source
    operation.fFlags = 0x0040 | 0x0010 | 0x0004 | 0x0400

    result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(operation))
    if result != 0 or operation.fAnyOperationsAborted:
        raise OSError(f"Impossibile spostare nel Cestino di Windows: codice {result}")
    return path


def format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} {unit}"
        value /= 1024
    return f"{size} B"
