#!/usr/bin/env python3
"""Extract every audio track from a video file.

Cross-platform GUI/CLI wrapper around ffmpeg and ffprobe.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


APP_NAME = "Estrai tracce audio"
DEFAULT_LANG = "it"

CODEC_EXTENSIONS = {
    "aac": ".m4a",
    "ac3": ".ac3",
    "alac": ".m4a",
    "dca": ".dts",
    "dts": ".dts",
    "eac3": ".eac3",
    "flac": ".flac",
    "mp2": ".mp2",
    "mp3": ".mp3",
    "opus": ".opus",
    "pcm_s16le": ".wav",
    "pcm_s24le": ".wav",
    "truehd": ".thd",
    "vorbis": ".ogg",
    "wmav1": ".wma",
    "wmav2": ".wma",
}

TEXTS = {
    "it": {
        "app_name": "Estrai tracce audio",
        "language": "Lingua",
        "choose_video_status": "Scegli un video da cui estrarre le tracce audio.",
        "video": "Video",
        "output": "Output",
        "browse": "Sfoglia",
        "format": "Formato",
        "copy_mode": "Mantieni audio originale, senza ricodifica",
        "wav_mode": "Converti ogni traccia in WAV",
        "extract": "Estrai tracce audio",
        "choose_video_title": "Scegli un video",
        "all_files": "Tutti i file",
        "choose_output_title": "Scegli cartella output",
        "missing_video": "Scegli prima un file video.",
        "naming_title": "Ascolta e nomina le tracce",
        "naming_header": "Trovate {count} tracce audio. Ascolta un'anteprima e scegli il nome di ogni traccia.",
        "track": "Traccia {number}",
        "track_details": "Traccia {number}: {codec}, {channels}, lingua {language}{title}",
        "track_name": "Nome traccia",
        "final_file": "File finale: {name}",
        "play": "Play",
        "pause": "Pausa",
        "preparing": "Preparo...",
        "cancel": "Annulla",
        "extract_with_names": "Estrai con questi nomi",
        "cancelled": "Estrazione annullata.",
        "completed_title": "Estrazione completata",
        "completed_message": "Estrazione completata:\n\n{files}",
        "unexpected_error": "Errore inatteso: {error}",
        "preview_prepare_log": "Preparo anteprima traccia {number} da {position}...",
        "preview_play_log": "Riproduco anteprima traccia {number}.",
        "preview_error_log": "Errore anteprima: {error}",
        "preview_track_error_log": "Errore anteprima traccia {number}: {error}",
        "analyzing": "Analizzo: {name}",
        "found_tracks": "Trovate {count} tracce audio.",
        "extracting_track": "Estrazione traccia {number}/{total} ({codec}, {language}) -> {name}",
        "fallback_container": "Formato non accettato dal contenitore. Riprovo senza conversione: {name}",
        "done": "Finito.",
        "created_files": "\nFile creati:",
        "error_prefix": "Errore: {error}",
        "video_missing": "Il video non esiste: {path}",
        "invalid_mode": "Modalita non valida. Usa 'copy' oppure 'wav'.",
        "ffprobe_failed": "FFprobe non riesce a leggere il video.",
        "ffprobe_invalid": "Risposta FFprobe non valida.",
        "no_audio": "Questo video non contiene tracce audio.",
        "too_many_files": "Troppi file con lo stesso nome nella cartella di output.",
        "extract_track_failed": "Errore estraendo la traccia {number}.",
        "preview_create_failed": "Non riesco a creare l'anteprima della traccia {number}.",
        "audio_player_missing": "Non trovo un player audio per riprodurre l'anteprima.",
        "tool_override_missing": "Non trovo {name}: {path}",
        "tool_missing": "Non trovo {name}. Installa FFmpeg oppure metti {name} nella cartella del programma.",
        "tk_missing": "Tkinter non disponibile: {error}",
        "cli_description": "Estrae tutte le tracce audio da un video.",
        "cli_video_help": "File video di input. Se omesso, apre la GUI.",
        "cli_output_help": "Cartella dove salvare le tracce.",
        "cli_mode_help": "copy mantiene il codec originale; wav converte ogni traccia in WAV.",
        "cli_ffmpeg_help": "Percorso manuale di ffmpeg.",
        "cli_ffprobe_help": "Percorso manuale di ffprobe.",
        "cli_lang_help": "Lingua dell'interfaccia.",
    },
    "en": {
        "app_name": "Extract audio tracks",
        "language": "Language",
        "choose_video_status": "Choose a video to extract audio tracks from.",
        "video": "Video",
        "output": "Output",
        "browse": "Browse",
        "format": "Format",
        "copy_mode": "Keep original audio, no re-encoding",
        "wav_mode": "Convert every track to WAV",
        "extract": "Extract audio tracks",
        "choose_video_title": "Choose a video",
        "all_files": "All files",
        "choose_output_title": "Choose output folder",
        "missing_video": "Choose a video file first.",
        "naming_title": "Preview and name tracks",
        "naming_header": "Found {count} audio tracks. Preview each one and choose its track name.",
        "track": "Track {number}",
        "track_details": "Track {number}: {codec}, {channels}, language {language}{title}",
        "track_name": "Track name",
        "final_file": "Final file: {name}",
        "play": "Play",
        "pause": "Pause",
        "preparing": "Preparing...",
        "cancel": "Cancel",
        "extract_with_names": "Extract with these names",
        "cancelled": "Extraction cancelled.",
        "completed_title": "Extraction complete",
        "completed_message": "Extraction complete:\n\n{files}",
        "unexpected_error": "Unexpected error: {error}",
        "preview_prepare_log": "Preparing track {number} preview from {position}...",
        "preview_play_log": "Playing track {number} preview.",
        "preview_error_log": "Preview error: {error}",
        "preview_track_error_log": "Track {number} preview error: {error}",
        "analyzing": "Analyzing: {name}",
        "found_tracks": "Found {count} audio tracks.",
        "extracting_track": "Extracting track {number}/{total} ({codec}, {language}) -> {name}",
        "fallback_container": "The format is not accepted by the container. Retrying without conversion: {name}",
        "done": "Done.",
        "created_files": "\nCreated files:",
        "error_prefix": "Error: {error}",
        "video_missing": "Video file does not exist: {path}",
        "invalid_mode": "Invalid mode. Use 'copy' or 'wav'.",
        "ffprobe_failed": "FFprobe cannot read the video.",
        "ffprobe_invalid": "Invalid FFprobe response.",
        "no_audio": "This video does not contain audio tracks.",
        "too_many_files": "Too many files with the same name in the output folder.",
        "extract_track_failed": "Error extracting track {number}.",
        "preview_create_failed": "Cannot create the preview for track {number}.",
        "audio_player_missing": "No audio player found for preview playback.",
        "tool_override_missing": "Cannot find {name}: {path}",
        "tool_missing": "Cannot find {name}. Install FFmpeg or place {name} in the program folder.",
        "tk_missing": "Tkinter is not available: {error}",
        "cli_description": "Extracts every audio track from a video.",
        "cli_video_help": "Input video file. If omitted, opens the GUI.",
        "cli_output_help": "Folder where extracted tracks will be saved.",
        "cli_mode_help": "copy keeps the original codec; wav converts every track to WAV.",
        "cli_ffmpeg_help": "Manual ffmpeg path.",
        "cli_ffprobe_help": "Manual ffprobe path.",
        "cli_lang_help": "Interface language.",
    },
}


def normalize_lang(lang: str | None) -> str:
    return lang if lang in TEXTS else DEFAULT_LANG


def tr(key: str, lang: str | None = None, **kwargs: object) -> str:
    language = normalize_lang(lang)
    template = TEXTS[language].get(key, TEXTS[DEFAULT_LANG][key])
    return template.format(**kwargs)


@dataclass(frozen=True)
class AudioStream:
    index: int
    audio_number: int
    codec: str
    channels: str
    language: str
    title: str
    duration: float


class ExtractionError(RuntimeError):
    pass


def find_tool(name: str, override: str | None = None, lang: str | None = None) -> str:
    if override:
        candidate = Path(override).expanduser()
        if candidate.is_file():
            return str(candidate)
        raise ExtractionError(tr("tool_override_missing", lang, name=name, path=candidate))

    found = shutil.which(name)
    if found:
        return found

    local_names = [name]
    if sys.platform.startswith("win"):
        local_names.insert(0, f"{name}.exe")

    script_dir = Path(__file__).resolve().parent
    for folder in (script_dir, script_dir / "ffmpeg", script_dir / "ffmpeg" / "bin"):
        for local_name in local_names:
            candidate = folder / local_name
            if candidate.is_file():
                return str(candidate)

    raise ExtractionError(tr("tool_missing", lang, name=name))


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    kwargs = {}
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    return subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        **kwargs,
    )


def probe_audio_streams(video_path: Path, ffprobe: str, lang: str | None = None) -> list[AudioStream]:
    result = run_command(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=index,codec_name,channels,channel_layout,duration:stream_tags=language,title:format=duration",
            "-of",
            "json",
            str(video_path),
        ]
    )
    if result.returncode != 0:
        raise ExtractionError(clean_error(result.stderr) or tr("ffprobe_failed", lang))

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ExtractionError(tr("ffprobe_invalid", lang)) from exc

    streams: list[AudioStream] = []
    format_duration = parse_float((payload.get("format") or {}).get("duration"), default=0.0)
    for audio_number, stream in enumerate(payload.get("streams", []), start=1):
        tags = stream.get("tags") or {}
        channels = stream.get("channel_layout") or stream.get("channels") or "audio"
        streams.append(
            AudioStream(
                index=int(stream["index"]),
                audio_number=audio_number,
                codec=str(stream.get("codec_name") or "unknown"),
                channels=str(channels),
                language=str(tags.get("language") or "und"),
                title=str(tags.get("title") or ""),
                duration=parse_float(stream.get("duration"), default=format_duration),
            )
        )

    return streams


def parse_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def sanitize_filename(value: str) -> str:
    value = value.strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip(" .")
    return value or "audio"


def stream_label(stream: AudioStream, lang: str | None = None) -> str:
    prefix = "track" if normalize_lang(lang) == "en" else "traccia"
    parts = [f"{prefix}-{stream.audio_number:02d}", stream.language, stream.codec, stream.channels]
    if stream.title:
        parts.append(stream.title)
    return sanitize_filename("_".join(parts))


def default_output_stem(video_path: Path, stream: AudioStream, lang: str | None = None) -> str:
    return f"{sanitize_filename(video_path.stem)}_{stream_label(stream, lang)}"


def remove_selected_suffix(name: str, suffix: str) -> str:
    if name.lower().endswith(suffix.lower()):
        return name[: -len(suffix)]
    return name


def unique_output_path(output_dir: Path, stem: str, suffix: str, lang: str | None = None) -> Path:
    stem = sanitize_filename(remove_selected_suffix(stem, suffix))
    candidate = output_dir / f"{stem}{suffix}"
    if not candidate.exists():
        return candidate

    for counter in range(2, 1000):
        candidate = output_dir / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
    raise ExtractionError(tr("too_many_files", lang))


def output_path_for_stream(
    video_path: Path,
    output_dir: Path,
    stream: AudioStream,
    mode: str,
    custom_name: str | None = None,
    lang: str | None = None,
) -> Path:
    suffix = ".wav" if mode == "wav" else CODEC_EXTENSIONS.get(stream.codec, ".mka")
    if custom_name:
        return unique_output_path(output_dir, custom_name, suffix, lang)
    return unique_output_path(output_dir, default_output_stem(video_path, stream, lang), suffix, lang)


def ffmpeg_extract_command(
    ffmpeg: str,
    video_path: Path,
    stream: AudioStream,
    output_path: Path,
    mode: str,
) -> list[str]:
    command = [
        ffmpeg,
        "-hide_banner",
        "-y",
        "-i",
        str(video_path),
        "-map",
        f"0:{stream.index}",
        "-vn",
    ]
    if mode == "wav":
        command += ["-c:a", "pcm_s16le"]
    else:
        command += ["-c:a", "copy"]
    command.append(str(output_path))
    return command


def clean_error(stderr: str) -> str:
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join(lines[-6:])


def create_preview_file(
    video_path: Path,
    stream: AudioStream,
    ffmpeg: str,
    temp_dir: Path,
    start_seconds: float = 0.0,
    seconds: int = 15,
    lang: str | None = None,
) -> Path:
    temp_dir.mkdir(parents=True, exist_ok=True)
    preview_path = temp_dir / f"anteprima_traccia_{stream.audio_number:02d}.wav"
    start_seconds = max(0.0, start_seconds)
    result = run_command(
        [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-ss",
            f"{start_seconds:.3f}",
            "-i",
            str(video_path),
            "-map",
            f"0:{stream.index}",
            "-vn",
            "-t",
            str(seconds),
            "-c:a",
            "pcm_s16le",
            "-ac",
            "2",
            "-ar",
            "44100",
            str(preview_path),
        ]
    )
    if result.returncode != 0:
        raise ExtractionError(
            clean_error(result.stderr) or tr("preview_create_failed", lang, number=stream.audio_number)
        )
    return preview_path


class PreviewPlayer:
    def __init__(self) -> None:
        self.process: subprocess.Popen[bytes] | None = None
        self.temp_dir = Path(tempfile.mkdtemp(prefix="extract-audio-preview-"))

    def stop(self) -> None:
        if sys.platform.startswith("win"):
            try:
                import winsound

                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass

        if self.process and self.process.poll() is None:
            self.process.terminate()
        self.process = None

    def play(self, wav_path: Path) -> None:
        self.stop()
        if sys.platform.startswith("win"):
            import winsound

            winsound.PlaySound(str(wav_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            return

        if sys.platform == "darwin":
            self.process = subprocess.Popen(["afplay", str(wav_path)])
            return

        player = shutil.which("paplay") or shutil.which("aplay") or shutil.which("ffplay")
        if not player:
            raise ExtractionError(tr("audio_player_missing"))
        command = [player, str(wav_path)]
        if Path(player).name == "ffplay":
            command = [player, "-nodisp", "-autoexit", str(wav_path)]
        self.process = subprocess.Popen(command)

    def cleanup(self) -> None:
        self.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)


def extract_audio_tracks(
    video_path: Path | str,
    output_dir: Path | str | None = None,
    mode: str = "copy",
    custom_names: dict[int, str] | None = None,
    ffmpeg_path: str | None = None,
    ffprobe_path: str | None = None,
    lang: str | None = None,
    log: Callable[[str], None] | None = None,
) -> list[Path]:
    lang = normalize_lang(lang)
    video_path = Path(video_path).expanduser().resolve()
    if not video_path.is_file():
        raise ExtractionError(tr("video_missing", lang, path=video_path))

    output_dir = Path(output_dir).expanduser().resolve() if output_dir else video_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    if mode not in {"copy", "wav"}:
        raise ExtractionError(tr("invalid_mode", lang))

    ffmpeg = find_tool("ffmpeg", ffmpeg_path, lang)
    ffprobe = find_tool("ffprobe", ffprobe_path, lang)

    emit = log or (lambda message: None)
    emit(tr("analyzing", lang, name=video_path.name))
    streams = probe_audio_streams(video_path, ffprobe, lang)
    if not streams:
        raise ExtractionError(tr("no_audio", lang))

    emit(tr("found_tracks", lang, count=len(streams)))
    extracted: list[Path] = []
    for stream in streams:
        output_path = output_path_for_stream(
            video_path,
            output_dir,
            stream,
            mode,
            custom_name=(custom_names or {}).get(stream.index),
            lang=lang,
        )
        emit(
            tr(
                "extracting_track",
                lang,
                number=stream.audio_number,
                total=len(streams),
                codec=stream.codec,
                language=stream.language,
                name=output_path.name,
            )
        )
        result = run_command(ffmpeg_extract_command(ffmpeg, video_path, stream, output_path, mode))

        if result.returncode != 0 and mode == "copy" and output_path.suffix != ".mka":
            fallback = output_path.with_suffix(".mka")
            emit(tr("fallback_container", lang, name=fallback.name))
            result = run_command(ffmpeg_extract_command(ffmpeg, video_path, stream, fallback, mode))
            output_path = fallback

        if result.returncode != 0:
            raise ExtractionError(
                clean_error(result.stderr) or tr("extract_track_failed", lang, number=stream.audio_number)
            )

        extracted.append(output_path)

    emit(tr("done", lang))
    return extracted


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    argv = list(argv)
    pre_lang = DEFAULT_LANG
    for index, value in enumerate(argv):
        if value == "--lang" and index + 1 < len(argv):
            pre_lang = normalize_lang(argv[index + 1])
        elif value.startswith("--lang="):
            pre_lang = normalize_lang(value.split("=", 1)[1])

    parser = argparse.ArgumentParser(description=tr("cli_description", pre_lang))
    parser.add_argument("video", nargs="?", help=tr("cli_video_help", pre_lang))
    parser.add_argument("-o", "--output", help=tr("cli_output_help", pre_lang))
    parser.add_argument(
        "--mode",
        choices=["copy", "wav"],
        default="copy",
        help=tr("cli_mode_help", pre_lang),
    )
    parser.add_argument("--ffmpeg", help=tr("cli_ffmpeg_help", pre_lang))
    parser.add_argument("--ffprobe", help=tr("cli_ffprobe_help", pre_lang))
    parser.add_argument("--lang", choices=["it", "en"], default=pre_lang, help=tr("cli_lang_help", pre_lang))
    return parser.parse_args(argv)


def run_cli(args: argparse.Namespace) -> int:
    lang = normalize_lang(args.lang)
    try:
        files = extract_audio_tracks(
            args.video,
            args.output,
            args.mode,
            custom_names=None,
            ffmpeg_path=args.ffmpeg,
            ffprobe_path=args.ffprobe,
            lang=lang,
            log=print,
        )
    except ExtractionError as exc:
        print(tr("error_prefix", lang, error=exc), file=sys.stderr)
        return 1

    print(tr("created_files", lang))
    for file_path in files:
        print(f"- {file_path}")
    return 0


def run_gui() -> int:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except Exception as exc:  # pragma: no cover - depends on local Python build
        print(f"Tkinter non disponibile: {exc}", file=sys.stderr)
        return 1

    root = tk.Tk()
    root.geometry("760x520")
    root.minsize(680, 460)

    lang_var = tk.StringVar(value=DEFAULT_LANG)
    video_var = tk.StringVar()
    output_var = tk.StringVar()
    mode_var = tk.StringVar(value="copy")
    status_var = tk.StringVar()
    preview_player = PreviewPlayer()

    def current_lang() -> str:
        return normalize_lang(lang_var.get())

    def gui_text(key: str, **kwargs: object) -> str:
        return tr(key, current_lang(), **kwargs)

    def choose_video() -> None:
        path = filedialog.askopenfilename(
            title=gui_text("choose_video_title"),
            filetypes=[
                ("Video", "*.mp4 *.mkv *.mov *.avi *.m4v *.webm *.wmv *.flv *.ts *.mts *.m2ts"),
                (gui_text("all_files"), "*.*"),
            ],
        )
        if path:
            video_var.set(path)
            if not output_var.get():
                output_var.set(str(Path(path).parent))

    def choose_output() -> None:
        path = filedialog.askdirectory(title=gui_text("choose_output_title"))
        if path:
            output_var.set(path)

    main = ttk.Frame(root, padding=18)
    main.pack(fill="both", expand=True)
    main.columnconfigure(1, weight=1)
    main.rowconfigure(7, weight=1)

    title_label = ttk.Label(main, font=("TkDefaultFont", 18, "bold"))
    title_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

    language_frame = ttk.Frame(main)
    language_frame.grid(row=0, column=2, sticky="e", pady=(0, 14))
    language_label = ttk.Label(language_frame)
    language_label.grid(row=0, column=0, padx=(0, 6))
    language_select = ttk.Combobox(language_frame, textvariable=lang_var, values=["it", "en"], width=5, state="readonly")
    language_select.grid(row=0, column=1)

    video_label = ttk.Label(main)
    video_label.grid(row=1, column=0, sticky="w", pady=6)
    ttk.Entry(main, textvariable=video_var).grid(row=1, column=1, sticky="ew", padx=8, pady=6)
    video_browse_button = ttk.Button(main, command=choose_video)
    video_browse_button.grid(row=1, column=2, sticky="ew", pady=6)

    output_label = ttk.Label(main)
    output_label.grid(row=2, column=0, sticky="w", pady=6)
    ttk.Entry(main, textvariable=output_var).grid(row=2, column=1, sticky="ew", padx=8, pady=6)
    output_browse_button = ttk.Button(main, command=choose_output)
    output_browse_button.grid(row=2, column=2, sticky="ew", pady=6)

    options = ttk.LabelFrame(main)
    options.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(10, 8))
    options.columnconfigure(0, weight=1)
    options.columnconfigure(1, weight=1)
    copy_radio = ttk.Radiobutton(
        options,
        variable=mode_var,
        value="copy",
    )
    copy_radio.grid(row=0, column=0, sticky="w", padx=10, pady=8)
    wav_radio = ttk.Radiobutton(
        options,
        variable=mode_var,
        value="wav",
    )
    wav_radio.grid(row=0, column=1, sticky="w", padx=10, pady=8)

    progress = ttk.Progressbar(main, mode="indeterminate")
    progress.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(8, 4))

    ttk.Label(main, textvariable=status_var).grid(row=5, column=0, columnspan=3, sticky="w", pady=(4, 8))

    log_box = tk.Text(main, height=12, wrap="word", state="disabled")
    log_box.grid(row=7, column=0, columnspan=3, sticky="nsew")
    scrollbar = ttk.Scrollbar(main, command=log_box.yview)
    scrollbar.grid(row=7, column=3, sticky="ns")
    log_box.configure(yscrollcommand=scrollbar.set)

    def append_log(message: str) -> None:
        root.after(0, lambda: _append_log_now(message))

    def _append_log_now(message: str) -> None:
        status_var.set(message)
        log_box.configure(state="normal")
        log_box.insert("end", message + "\n")
        log_box.see("end")
        log_box.configure(state="disabled")

    def set_running(is_running: bool) -> None:
        extract_button.configure(state="disabled" if is_running else "normal")
        if is_running:
            progress.start(12)
        else:
            progress.stop()

    def stream_details(stream: AudioStream) -> str:
        title = f", {stream.title}" if stream.title else ""
        return gui_text(
            "track_details",
            number=stream.audio_number,
            codec=stream.codec,
            channels=stream.channels,
            language=stream.language,
            title=title,
        )

    def format_time(seconds: float) -> str:
        seconds = max(0, int(seconds))
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def show_track_naming_dialog(
        video_path: Path,
        output_dir: Path,
        mode: str,
        ffmpeg: str,
        streams: list[AudioStream],
    ) -> None:
        set_running(False)

        dialog = tk.Toplevel(root)
        dialog.title(gui_text("naming_title"))
        dialog.geometry("760x540")
        dialog.minsize(640, 420)
        dialog.transient(root)
        dialog.grab_set()
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)

        header = ttk.Frame(dialog, padding=(16, 14, 16, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            text=gui_text("naming_header", count=len(streams)),
            font=("TkDefaultFont", 11, "bold"),
        ).grid(row=0, column=0, sticky="w")

        body = ttk.Frame(dialog, padding=(12, 0, 12, 8))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        canvas = tk.Canvas(body, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        track_scrollbar = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        track_scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=track_scrollbar.set)

        rows = ttk.Frame(canvas)
        rows_window = canvas.create_window((0, 0), window=rows, anchor="nw")
        rows.columnconfigure(0, weight=1)
        rows.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(rows_window, width=event.width))

        name_vars: dict[int, tk.StringVar] = {}
        base_output_name = sanitize_filename(video_path.stem)
        preview_seconds = 15
        active_state: dict[str, object] | None = None

        def output_suffix_for_stream(stream: AudioStream) -> str:
            return ".wav" if mode == "wav" else CODEC_EXTENSIONS.get(stream.codec, ".mka")

        def default_track_name(stream: AudioStream) -> str:
            if stream.title:
                return sanitize_filename(stream.title)
            prefix = "track" if current_lang() == "en" else "traccia"
            return f"{prefix}-{stream.audio_number:02d}"

        def output_stem_from_track_name(stream: AudioStream, track_name: str) -> str:
            track_name = sanitize_filename(track_name or default_track_name(stream))
            return f"{base_output_name}_{track_name}"

        def update_final_name_preview(
            stream: AudioStream,
            track_name_var: tk.StringVar,
            final_name_var: tk.StringVar,
        ) -> None:
            final_name_var.set(
                gui_text(
                    "final_file",
                    name=f"{output_stem_from_track_name(stream, track_name_var.get())}"
                    f"{output_suffix_for_stream(stream)}",
                )
            )

        def state_duration(state: dict[str, object]) -> float:
            return float(state["duration"])

        def state_position(state: dict[str, object]) -> float:
            return float(state["position_var"].get())

        def clamp_position(state: dict[str, object], value: float) -> float:
            duration = state_duration(state)
            if duration > 0:
                return min(max(0.0, value), duration)
            return max(0.0, value)

        def set_position(state: dict[str, object], value: float) -> None:
            position = clamp_position(state, value)
            state["position_var"].set(position)
            update_position_label(state, position)

        def update_position_label(state: dict[str, object], position: float | None = None) -> None:
            if position is None:
                position = state_position(state)
            duration = state_duration(state)
            if duration > 0:
                state["position_label_var"].set(f"{format_time(position)} / {format_time(duration)}")
            else:
                state["position_label_var"].set(format_time(position))

        def set_player_button(state: dict[str, object], playing: bool, busy: bool = False) -> None:
            state["busy"] = busy
            button = state["toggle_button"]
            if busy:
                button.configure(text=gui_text("preparing"), state="disabled")
            elif playing:
                button.configure(text=gui_text("pause"), state="normal")
            else:
                button.configure(text=gui_text("play"), state="normal")

        def stop_active(update_position: bool = True) -> None:
            nonlocal active_state
            state = active_state
            if not state:
                preview_player.stop()
                return
            if update_position and state.get("playing"):
                elapsed = time.monotonic() - float(state["started_at"])
                set_position(state, float(state["chunk_start"]) + elapsed)
            preview_player.stop()
            state["playing"] = False
            set_player_button(state, playing=False)
            active_state = None

        def begin_playback(state: dict[str, object], generation: int, preview: Path, start_position: float) -> None:
            nonlocal active_state
            if generation != int(state["generation"]):
                return
            try:
                preview_player.play(preview)
            except Exception as exc:
                messagebox.showerror(gui_text("app_name"), str(exc))
                append_log(gui_text("preview_track_error_log", number=state["stream"].audio_number, error=exc))
                set_player_button(state, playing=False)
                return

            active_state = state
            state["playing"] = True
            state["chunk_start"] = start_position
            state["started_at"] = time.monotonic()
            set_player_button(state, playing=True)
            append_log(gui_text("preview_play_log", number=state["stream"].audio_number))
            root.after(250, lambda: tick_playback(state, generation))

        def tick_playback(state: dict[str, object], generation: int) -> None:
            if state is not active_state or generation != int(state["generation"]) or not state.get("playing"):
                return
            if state.get("scrubbing"):
                root.after(250, lambda: tick_playback(state, generation))
                return
            elapsed = time.monotonic() - float(state["started_at"])
            position = float(state["chunk_start"]) + elapsed
            duration = state_duration(state)
            segment_end = float(state["chunk_start"]) + preview_seconds
            if duration > 0:
                segment_end = min(segment_end, duration)

            if position >= segment_end:
                set_position(state, segment_end)
                stop_active(update_position=False)
                return

            set_position(state, position)
            root.after(250, lambda: tick_playback(state, generation))

        def play_from_position(state: dict[str, object]) -> None:
            stop_active(update_position=True)
            state["generation"] = int(state["generation"]) + 1
            generation = int(state["generation"])
            start_position = clamp_position(state, state_position(state))
            set_position(state, start_position)
            set_player_button(state, playing=False, busy=True)
            stream = state["stream"]
            append_log(gui_text("preview_prepare_log", number=stream.audio_number, position=format_time(start_position)))

            def worker() -> None:
                try:
                    preview = create_preview_file(
                        video_path,
                        stream,
                        ffmpeg,
                        preview_player.temp_dir,
                        start_seconds=start_position,
                        seconds=preview_seconds,
                        lang=current_lang(),
                    )
                except Exception as exc:
                    error_text = str(exc)
                    root.after(0, lambda text=error_text: messagebox.showerror(gui_text("app_name"), text))
                    append_log(gui_text("preview_error_log", error=exc))
                    root.after(0, lambda: set_player_button(state, playing=False))
                else:
                    root.after(0, lambda: begin_playback(state, generation, preview, start_position))

            threading.Thread(target=worker, daemon=True).start()

        def pause_state(state: dict[str, object]) -> None:
            if state is active_state and state.get("playing"):
                stop_active(update_position=True)

        def toggle_playback(state: dict[str, object]) -> None:
            if state is active_state and state.get("playing"):
                pause_state(state)
            else:
                play_from_position(state)

        def start_slider_seek(state: dict[str, object]) -> None:
            if state.get("busy"):
                state["generation"] = int(state["generation"]) + 1
                set_player_button(state, playing=False)
            state["resume_after_seek"] = state is active_state and bool(state.get("playing"))
            if state["resume_after_seek"]:
                stop_active(update_position=True)
            state["scrubbing"] = True

        def finish_slider_seek(state: dict[str, object]) -> None:
            set_position(state, state_position(state))
            state["scrubbing"] = False
            if state.get("resume_after_seek"):
                state["resume_after_seek"] = False
                play_from_position(state)

        def seek_to_slider_position(state: dict[str, object], value: str) -> None:
            update_position_label(state, float(value))

        for row, stream in enumerate(streams):
            track_frame = ttk.LabelFrame(rows, text=gui_text("track", number=stream.audio_number), padding=(10, 8))
            track_frame.grid(row=row, column=0, sticky="ew", padx=(0, 4), pady=(0, 8))
            track_frame.columnconfigure(1, weight=1)

            ttk.Label(track_frame, text=stream_details(stream)).grid(
                row=0, column=0, columnspan=3, sticky="w", pady=(0, 6)
            )

            toggle_button = ttk.Button(track_frame, text=gui_text("play"), width=9)
            toggle_button.grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(0, 6))

            position_var = tk.DoubleVar(value=0.0)
            position_label_var = tk.StringVar(value="")
            scale_to = stream.duration if stream.duration > 0 else 1.0
            position_scale = ttk.Scale(track_frame, from_=0.0, to=scale_to, variable=position_var)
            position_scale.grid(row=1, column=1, sticky="ew", pady=(0, 6))
            ttk.Label(track_frame, textvariable=position_label_var, width=16).grid(
                row=1, column=2, sticky="e", padx=(8, 0), pady=(0, 6)
            )

            state: dict[str, object] = {
                "stream": stream,
                "duration": stream.duration,
                "position_var": position_var,
                "position_label_var": position_label_var,
                "toggle_button": toggle_button,
                "playing": False,
                "busy": False,
                "scrubbing": False,
                "resume_after_seek": False,
                "chunk_start": 0.0,
                "started_at": 0.0,
                "generation": 0,
            }
            update_position_label(state, 0.0)
            position_scale.configure(command=lambda value, st=state: seek_to_slider_position(st, value))
            position_scale.bind("<ButtonPress-1>", lambda event, st=state: start_slider_seek(st))
            position_scale.bind("<ButtonRelease-1>", lambda event, st=state: finish_slider_seek(st))
            toggle_button.configure(command=lambda st=state: toggle_playback(st))

            var = tk.StringVar(value=default_track_name(stream))
            name_vars[stream.index] = var
            final_name_var = tk.StringVar()
            update_final_name_preview(stream, var, final_name_var)
            var.trace_add("write", lambda *_args, s=stream, v=var, f=final_name_var: update_final_name_preview(s, v, f))
            ttk.Label(track_frame, text=gui_text("track_name")).grid(row=2, column=0, sticky="w", padx=(0, 8))
            ttk.Entry(track_frame, textvariable=var).grid(row=2, column=1, columnspan=2, sticky="ew")
            ttk.Label(track_frame, textvariable=final_name_var).grid(
                row=3, column=1, columnspan=2, sticky="w", pady=(4, 0)
            )

        actions = ttk.Frame(dialog, padding=(16, 8, 16, 16))
        actions.grid(row=2, column=0, sticky="ew")
        actions.columnconfigure(0, weight=1)

        def cancel() -> None:
            stop_active(update_position=False)
            dialog.destroy()
            status_var.set(gui_text("cancelled"))

        def confirm() -> None:
            stop_active(update_position=False)
            names = {
                stream.index: output_stem_from_track_name(stream, name_vars[stream.index].get().strip())
                for stream in streams
            }
            dialog.destroy()
            start_named_extraction(video_path, output_dir, mode, names)

        ttk.Button(actions, text=gui_text("cancel"), command=cancel).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(actions, text=gui_text("extract_with_names"), command=confirm).grid(row=0, column=2)

        dialog.protocol("WM_DELETE_WINDOW", cancel)

    def start_named_extraction(
        video_path: Path,
        output_dir: Path,
        mode: str,
        custom_names: dict[int, str],
    ) -> None:
        set_running(True)

        def worker() -> None:
            try:
                files = extract_audio_tracks(
                    video_path,
                    output_dir,
                    mode,
                    custom_names=custom_names,
                    lang=current_lang(),
                    log=append_log,
                )
            except ExtractionError as exc:
                error_text = str(exc)
                root.after(0, lambda text=error_text: messagebox.showerror(gui_text("app_name"), text))
                append_log(gui_text("error_prefix", error=exc))
            except Exception as exc:  # pragma: no cover - defensive GUI boundary
                error_text = gui_text("unexpected_error", error=exc)
                root.after(0, lambda text=error_text: messagebox.showerror(gui_text("app_name"), text))
                append_log(gui_text("unexpected_error", error=exc))
            else:
                created = "\n".join(str(path) for path in files)
                root.after(
                    0,
                    lambda: messagebox.showinfo(
                        gui_text("completed_title"),
                        gui_text("completed_message", files=created),
                    ),
                )
            finally:
                root.after(0, lambda: set_running(False))

        threading.Thread(target=worker, daemon=True).start()

    def start_extraction() -> None:
        video = video_var.get().strip()
        output = output_var.get().strip()
        if not video:
            messagebox.showwarning(gui_text("app_name"), gui_text("missing_video"))
            return
        if not output:
            output = str(Path(video).parent)
            output_var.set(output)

        set_running(True)
        video_path = Path(video).expanduser().resolve()
        output_dir = Path(output).expanduser().resolve()
        mode = mode_var.get()

        def worker() -> None:
            try:
                lang = current_lang()
                ffmpeg = find_tool("ffmpeg", lang=lang)
                ffprobe = find_tool("ffprobe", lang=lang)
                append_log(tr("analyzing", lang, name=video_path.name))
                streams = probe_audio_streams(video_path, ffprobe, lang)
                if not streams:
                    raise ExtractionError(tr("no_audio", lang))
                append_log(tr("found_tracks", lang, count=len(streams)))
            except ExtractionError as exc:
                error_text = str(exc)
                root.after(0, lambda text=error_text: messagebox.showerror(gui_text("app_name"), text))
                append_log(gui_text("error_prefix", error=exc))
                root.after(0, lambda: set_running(False))
            except Exception as exc:  # pragma: no cover - defensive GUI boundary
                error_text = gui_text("unexpected_error", error=exc)
                root.after(0, lambda text=error_text: messagebox.showerror(gui_text("app_name"), text))
                append_log(gui_text("unexpected_error", error=exc))
                root.after(0, lambda: set_running(False))
            else:
                root.after(0, lambda: show_track_naming_dialog(video_path, output_dir, mode, ffmpeg, streams))

        threading.Thread(target=worker, daemon=True).start()

    extract_button = ttk.Button(main, text="Estrai tracce audio", command=start_extraction)
    extract_button.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(0, 12))

    def refresh_texts() -> None:
        root.title(gui_text("app_name"))
        title_label.configure(text=gui_text("app_name"))
        language_label.configure(text=gui_text("language"))
        video_label.configure(text=gui_text("video"))
        output_label.configure(text=gui_text("output"))
        video_browse_button.configure(text=gui_text("browse"))
        output_browse_button.configure(text=gui_text("browse"))
        options.configure(text=gui_text("format"))
        copy_radio.configure(text=gui_text("copy_mode"))
        wav_radio.configure(text=gui_text("wav_mode"))
        extract_button.configure(text=gui_text("extract"))
        if not video_var.get().strip():
            status_var.set(gui_text("choose_video_status"))

    language_select.bind("<<ComboboxSelected>>", lambda _event: refresh_texts())
    refresh_texts()

    def on_close() -> None:
        preview_player.cleanup()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.video:
        return run_cli(args)
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
