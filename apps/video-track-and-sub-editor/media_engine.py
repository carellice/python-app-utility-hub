"""FFprobe/FFmpeg integration for the track editor.

The module deliberately builds every subprocess command as an argument list.  No
shell is involved, so paths containing spaces (or shell metacharacters) are safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Callable, Iterable


class MediaError(RuntimeError):
    """An actionable error to show in the user interface."""


def remove_original(path: Path, mode: str) -> None:
    """Remove *path* permanently or move it to the operating-system trash.

    This function is intentionally called only after a completed export has
    already been atomically moved into its final destination.
    """
    if mode == "permanent":
        try:
            path.unlink()
        except OSError as exc:
            raise MediaError(f"Impossibile eliminare definitivamente l'originale: {exc}") from exc
        return
    if mode != "trash":
        raise ValueError(f"Modalità di rimozione sconosciuta: {mode}")

    if sys.platform == "darwin":
        command = [
            "osascript",
            "-e",
            "on run argv",
            "-e",
            "set targetPath to item 1 of argv",
            "-e",
            "set targetFile to POSIX file targetPath as alias",
            "-e",
            'tell application "Finder" to delete targetFile',
            "-e",
            "end run",
            str(path),
        ]
    elif sys.platform.startswith("win"):
        script = (
            "Add-Type -AssemblyName Microsoft.VisualBasic; "
            "[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($args[0], "
            "[Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs, "
            "[Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin)"
        )
        command = ["powershell", "-NoProfile", "-NonInteractive", "-Command", script, str(path)]
    elif shutil.which("gio"):
        command = ["gio", "trash", str(path)]
    elif shutil.which("trash-put"):
        command = ["trash-put", str(path)]
    else:
        raise MediaError("Il Cestino di sistema non è disponibile su questo computer.")

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise MediaError(f"Impossibile usare il Cestino di sistema: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "errore sconosciuto"
        raise MediaError(f"Impossibile spostare l'originale nel Cestino: {detail}")
    if path.exists():
        raise MediaError("Il sistema non ha confermato lo spostamento dell'originale nel Cestino.")


def _find_binary(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    # GUI applications on macOS do not always inherit the user's shell PATH.
    for directory in ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin"):
        candidate = Path(directory, name)
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


@dataclass(frozen=True)
class FFmpegTools:
    ffmpeg: str
    ffprobe: str

    @classmethod
    def discover(cls) -> "FFmpegTools":
        ffmpeg = _find_binary("ffmpeg")
        ffprobe = _find_binary("ffprobe")
        if not ffmpeg or not ffprobe:
            raise MediaError(
                "FFmpeg non è installato o non è raggiungibile.\n\n"
                "Su macOS puoi installarlo con:  brew install ffmpeg\n"
                "Su Windows: https://ffmpeg.org/download.html"
            )
        return cls(ffmpeg=ffmpeg, ffprobe=ffprobe)


@dataclass
class Track:
    uid: str
    kind: str
    stream_index: int
    source_path: Path
    codec: str = "sconosciuto"
    language: str = "und"
    title: str = ""
    channels: int | None = None
    channel_layout: str = ""
    disposition: dict[str, int] = field(default_factory=dict)
    selected: bool = True
    external: bool = False

    @property
    def default(self) -> bool:
        return bool(self.disposition.get("default", 0))

    @default.setter
    def default(self, value: bool) -> None:
        self.disposition["default"] = int(value)

    @property
    def forced(self) -> bool:
        return bool(self.disposition.get("forced", 0))

    @forced.setter
    def forced(self, value: bool) -> None:
        self.disposition["forced"] = int(value)

    @property
    def details(self) -> str:
        if self.kind == "audio":
            parts = [self.codec]
            if self.channels:
                parts.append(f"{self.channels} ch")
            if self.channel_layout:
                parts.append(self.channel_layout)
            return " · ".join(parts)
        return self.codec


@dataclass
class MediaInfo:
    path: Path
    tracks: list[Track]
    video_streams: list[dict[str, Any]]
    duration: float | None
    format_name: str
    size: int | None

    @property
    def audio_tracks(self) -> list[Track]:
        return [track for track in self.tracks if track.kind == "audio"]

    @property
    def subtitle_tracks(self) -> list[Track]:
        return [track for track in self.tracks if track.kind == "subtitle"]


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_probe(path: Path, payload: dict[str, Any], *, external: bool = False) -> MediaInfo:
    """Convert ffprobe JSON into the small model needed by the GUI."""
    tracks: list[Track] = []
    video_streams: list[dict[str, Any]] = []
    for stream in payload.get("streams", []):
        kind = stream.get("codec_type", "")
        if kind == "video":
            video_streams.append(stream)
            continue
        if kind not in {"audio", "subtitle"}:
            continue
        tags = stream.get("tags") or {}
        index = int(stream.get("index", 0))
        uid = f"{'ext' if external else 'main'}:{path}:{index}"
        tracks.append(
            Track(
                uid=uid,
                kind=kind,
                stream_index=index,
                source_path=path,
                codec=str(stream.get("codec_name") or "sconosciuto"),
                language=str(tags.get("language") or "und"),
                title=str(tags.get("title") or ""),
                channels=_int_or_none(stream.get("channels")),
                channel_layout=str(stream.get("channel_layout") or ""),
                disposition={
                    str(key): int(value)
                    for key, value in (stream.get("disposition") or {}).items()
                    if isinstance(value, (int, bool))
                },
                external=external,
            )
        )

    format_info = payload.get("format") or {}
    return MediaInfo(
        path=path,
        tracks=tracks,
        video_streams=video_streams,
        duration=_float_or_none(format_info.get("duration")),
        format_name=str(format_info.get("format_long_name") or format_info.get("format_name") or ""),
        size=_int_or_none(format_info.get("size")),
    )


def probe_media(path: Path, tools: FFmpegTools, *, external: bool = False) -> MediaInfo:
    command = [
        tools.ffprobe,
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise MediaError(f"Impossibile avviare FFprobe: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or "formato non riconosciuto"
        raise MediaError(f"Impossibile analizzare “{path.name}”.\n\n{detail}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise MediaError("FFprobe ha restituito dati non validi.") from exc
    return parse_probe(path, payload, external=external)


def _disposition_value(disposition: dict[str, int]) -> str:
    enabled = [key for key, value in disposition.items() if value]
    return "+".join(enabled) if enabled else "0"


def build_ffmpeg_command(
    tools: FFmpegTools,
    source: Path,
    output: Path,
    tracks: Iterable[Track],
) -> list[str]:
    """Build a lossless-remux command.

    "Lossless" here means packet-for-packet stream copy: video, selected audio and
    selected subtitles are never decoded/re-encoded.
    """
    selected = [track for track in tracks if track.selected]
    external_paths: list[Path] = []
    for track in selected:
        if track.external and track.source_path not in external_paths:
            external_paths.append(track.source_path)
    input_index = {path: index + 1 for index, path in enumerate(external_paths)}

    command = [
        tools.ffmpeg,
        "-hide_banner",
        "-y",
        "-stats_period",
        "0.2",
        "-i",
        str(source),
    ]
    for path in external_paths:
        command.extend(["-i", str(path)])

    # Keep every video stream plus attachments from the original container.
    command.extend(["-map", "0:v?", "-map", "0:t?"])
    for track in selected:
        source_index = input_index[track.source_path] if track.external else 0
        command.extend(["-map", f"{source_index}:{track.stream_index}"])

    command.extend(
        [
            "-map_metadata",
            "0",
            "-map_chapters",
            "0",
            "-c",
            "copy",
        ]
    )

    for kind, specifier in (("audio", "a"), ("subtitle", "s")):
        kind_tracks = [track for track in selected if track.kind == kind]
        for output_index, track in enumerate(kind_tracks):
            command.extend(
                [
                    f"-metadata:s:{specifier}:{output_index}",
                    f"language={track.language.strip() or 'und'}",
                    f"-metadata:s:{specifier}:{output_index}",
                    f"title={track.title.strip()}",
                    f"-disposition:{specifier}:{output_index}",
                    _disposition_value(track.disposition),
                ]
            )

    command.extend(
        [
            "-max_muxing_queue_size",
            "4096",
            "-progress",
            "pipe:1",
            "-nostats",
            "-loglevel",
            "error",
            str(output),
        ]
    )
    return command


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "durata sconosciuta"
    rounded = max(0, int(round(seconds)))
    hours, remainder = divmod(rounded, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_size(size: int | None) -> str:
    if size is None:
        return "dimensione sconosciuta"
    amount = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if amount < 1024 or unit == "TB":
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    return f"{amount:.1f} TB"


def video_summary(info: MediaInfo) -> str:
    if not info.video_streams:
        return "Nessuna traccia video trovata"
    stream = info.video_streams[0]
    codec = str(stream.get("codec_name") or "codec sconosciuto").upper()
    width = stream.get("width")
    height = stream.get("height")
    resolution = f"{width}×{height}" if width and height else "risoluzione sconosciuta"
    suffix = "" if len(info.video_streams) == 1 else f" · {len(info.video_streams)} flussi video"
    return f"{codec} · {resolution} · {format_duration(info.duration)} · {format_size(info.size)}{suffix}"


class ExportProcess:
    """Small cancellable wrapper used by the GUI's worker thread."""

    def __init__(self) -> None:
        self.process: subprocess.Popen[str] | None = None

    def run(
        self,
        command: list[str],
        duration: float | None,
        on_progress: Callable[[float | None], None],
    ) -> tuple[bool, str]:
        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as exc:
            return False, f"Impossibile avviare FFmpeg: {exc}"

        output_lines: list[str] = []
        assert self.process.stdout is not None
        for raw_line in self.process.stdout:
            line = raw_line.strip()
            if not line:
                continue
            if "=" not in line:
                output_lines.append(line)
                continue
            key, value = line.split("=", 1)
            if key in {"out_time_us", "out_time_ms"} and duration and duration > 0:
                # Current FFmpeg reports both values in microseconds despite the
                # historical out_time_ms name.
                try:
                    on_progress(min(0.995, max(0.0, int(value) / 1_000_000 / duration)))
                except ValueError:
                    pass
            elif key == "progress" and value == "end":
                on_progress(1.0)

        self.process.stdout.close()
        return_code = self.process.wait()
        if return_code == 0:
            return True, ""
        detail = "\n".join(output_lines[-12:]).strip()
        if return_code < 0:
            return False, "Esportazione annullata."
        return False, detail or f"FFmpeg è terminato con codice {return_code}."

    def cancel(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
