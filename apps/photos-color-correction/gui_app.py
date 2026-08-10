#!/usr/bin/env python3
"""
Small desktop launcher for the photo color correction tool.
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import BooleanVar, DoubleVar, IntVar, StringVar, Text, Tk, filedialog, messagebox
from tkinter import ttk

from PIL import Image, ImageOps, ImageTk

from photo_color_corrector import (
    DEFAULT_PRESET,
    PRESETS,
    clamp,
    discover_images,
    enhance,
    get_preset,
    output_path_for,
    process_image,
)


LANGUAGES = {
    "it": "Italiano",
    "en": "English",
}
LANGUAGE_CODES = {label: code for code, label in LANGUAGES.items()}

TEXT = {
    "it": {
        "language": "Lingua",
        "status_choose_folder": "Scegli una cartella di fotografie.",
        "input_folder": "Cartella foto",
        "choose": "Scegli...",
        "default_output": "Salva automaticamente in una cartella 'corrected'",
        "output": "Output",
        "preset": "Preset",
        "intensity": "Intensita'",
        "quality": "Qualita'",
        "include_subfolders": "Includi sottocartelle",
        "overwrite": "Sovrascrivi risultati esistenti",
        "sample_preview": "Anteprima campione",
        "previous_photo": "Foto precedente",
        "next_photo": "Foto successiva",
        "no_sample": "Nessuna foto campione",
        "original": "Originale",
        "corrected": "Corretto",
        "customize_photo": "Personalizza solo questa foto",
        "copy_globals": "Copia dai globali",
        "global_settings": "Questa foto usa i settaggi globali",
        "custom_settings": "Personalizzata: {preset}, {strength:.2f}",
        "start": "Avvia correzione",
        "open_output": "Apri output",
        "log": "Log",
        "choose_input_title": "Scegli la cartella delle foto",
        "choose_output_title": "Scegli la cartella di output",
        "invalid_folder": "Cartella non valida",
        "no_photos_found": "Nessuna foto trovata",
        "preview_unavailable": "Anteprima non disponibile: {error}",
        "close": "Chiudi",
        "corrected_large": "Corretto - {preset}, {strength:.2f}",
        "missing_folder_title": "Cartella mancante",
        "missing_folder_message": "Scegli prima la cartella delle fotografie.",
        "invalid_folder_title": "Cartella non valida",
        "invalid_folder_message": "La cartella non esiste:\n{folder}",
        "missing_output_title": "Output mancante",
        "missing_output_message": "Scegli una cartella di output oppure usa quella automatica.",
        "processing": "Elaborazione in corso...",
        "no_supported": "Nessuna immagine supportata trovata.\n",
        "found_images": "Trovate {count} immagini.\n",
        "preset_log": "Preset: {preset}\n",
        "intensity_log": "Intensita': {strength:.2f}\n\n",
        "custom_photos_log": "Foto personalizzate: {count}\n\n",
        "done_status": "Finite. Elaborate: {processed}. Saltate: {skipped}. Fallite: {failed}.",
        "completed_errors_title": "Completato con errori",
        "completed_errors_message": "Alcune immagini non sono state elaborate.",
        "completed_title": "Completato",
        "completed_message": "Correzione completata.",
        "error": "Errore",
        "error_status": "Errore.",
        "output_missing_title": "Output non trovato",
        "output_missing_message": "La cartella di output non esiste ancora.",
        "skipped_existing": "skip, esiste gia': {destination}",
        "failed_image": "errore su {source}: {detail}",
    },
    "en": {
        "language": "Language",
        "status_choose_folder": "Choose a photo folder.",
        "input_folder": "Photo folder",
        "choose": "Choose...",
        "default_output": "Save automatically in a 'corrected' folder",
        "output": "Output",
        "preset": "Preset",
        "intensity": "Intensity",
        "quality": "Quality",
        "include_subfolders": "Include subfolders",
        "overwrite": "Overwrite existing results",
        "sample_preview": "Sample preview",
        "previous_photo": "Previous photo",
        "next_photo": "Next photo",
        "no_sample": "No sample photo",
        "original": "Original",
        "corrected": "Corrected",
        "customize_photo": "Customize only this photo",
        "copy_globals": "Copy from global",
        "global_settings": "This photo uses the global settings",
        "custom_settings": "Custom: {preset}, {strength:.2f}",
        "start": "Start correction",
        "open_output": "Open output",
        "log": "Log",
        "choose_input_title": "Choose the photo folder",
        "choose_output_title": "Choose the output folder",
        "invalid_folder": "Invalid folder",
        "no_photos_found": "No photos found",
        "preview_unavailable": "Preview unavailable: {error}",
        "close": "Close",
        "corrected_large": "Corrected - {preset}, {strength:.2f}",
        "missing_folder_title": "Missing folder",
        "missing_folder_message": "Choose the photo folder first.",
        "invalid_folder_title": "Invalid folder",
        "invalid_folder_message": "The folder does not exist:\n{folder}",
        "missing_output_title": "Missing output",
        "missing_output_message": "Choose an output folder or use the automatic one.",
        "processing": "Processing...",
        "no_supported": "No supported images found.\n",
        "found_images": "Found {count} images.\n",
        "preset_log": "Preset: {preset}\n",
        "intensity_log": "Intensity: {strength:.2f}\n\n",
        "custom_photos_log": "Custom photos: {count}\n\n",
        "done_status": "Done. Processed: {processed}. Skipped: {skipped}. Failed: {failed}.",
        "completed_errors_title": "Completed with errors",
        "completed_errors_message": "Some images were not processed.",
        "completed_title": "Completed",
        "completed_message": "Correction completed.",
        "error": "Error",
        "error_status": "Error.",
        "output_missing_title": "Output not found",
        "output_missing_message": "The output folder does not exist yet.",
        "skipped_existing": "skipped, already exists: {destination}",
        "failed_image": "error on {source}: {detail}",
    },
}

PRESET_LABELS = {
    "it": {key: preset.label for key, preset in PRESETS.items()},
    "en": {
        "natural": "Natural",
        "professional": "Professional",
        "vivid": "Vivid",
        "warm": "Warm",
        "cool": "Cool",
        "portrait": "Portrait",
        "cinematic": "Cinematic",
        "spectacular": "Spectacular",
        "black_white": "Black and white",
    },
}


def text_for(language: str, key: str, **values: object) -> str:
    return TEXT[language][key].format(**values)


def preset_label_for_language(preset_key: str, language: str) -> str:
    return PRESET_LABELS[language].get(preset_key, get_preset(preset_key).label)


class PhotoCorrectorApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("Photos Color Correction")
        self.root.minsize(760, 580)

        self.lang_code = "it"
        self.language = StringVar(value=LANGUAGES[self.lang_code])
        self.translated_widgets: list[tuple[tk.Widget, str]] = []
        self.empty_preview_key = "no_sample"

        self.input_folder = StringVar()
        self.output_folder = StringVar()
        self.use_default_output = BooleanVar(value=True)
        self.recursive = BooleanVar(value=False)
        self.overwrite = BooleanVar(value=False)
        self.preset_names = self.build_preset_name_map()
        self.preset_labels = list(self.preset_names.keys())
        self.preset = StringVar(value=self.preset_label_for_key(DEFAULT_PRESET))
        self.strength = DoubleVar(value=1.0)
        self.global_preset = DEFAULT_PRESET
        self.global_strength = 1.0
        self.per_photo_settings: dict[str, tuple[str, float]] = {}
        self.customize_current_photo = BooleanVar(value=False)
        self.loading_controls = False
        self.quality = IntVar(value=95)
        self.status_key = "status_choose_folder"
        self.status_values: dict[str, object] = {}
        self.status = StringVar(value=self.tr(self.status_key))
        self.queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.last_output_folder: Path | None = None
        self.sample_images: list[Path] = []
        self.sample_index = 0
        self.preview_after_id: str | None = None
        self.original_preview_image: ImageTk.PhotoImage | None = None
        self.corrected_preview_image: ImageTk.PhotoImage | None = None
        self.large_overlay: tk.Frame | None = None
        self.large_image_label: tk.Label | None = None
        self.large_title = StringVar(value="")
        self.large_preview_kind = "corrected"
        self.large_preview_image: ImageTk.PhotoImage | None = None

        self._build_ui()
        self._poll_queue()

    def tr(self, key: str, **values: object) -> str:
        return text_for(self.lang_code, key, **values)

    def build_preset_name_map(self) -> dict[str, str]:
        return {preset_label_for_language(key, self.lang_code): key for key in PRESETS}

    def preset_label_for_key(self, preset_key: str) -> str:
        return preset_label_for_language(preset_key, self.lang_code)

    def set_status(self, key: str, **values: object) -> None:
        self.status_key = key
        self.status_values = values
        self.status.set(self.tr(key, **values))

    def remember_text(self, widget: tk.Widget, key: str) -> tk.Widget:
        self.translated_widgets.append((widget, key))
        return widget

    def t_label(self, parent: tk.Widget, key: str, **kwargs: object) -> ttk.Label:
        return self.remember_text(ttk.Label(parent, text=self.tr(key), **kwargs), key)  # type: ignore[return-value]

    def t_button(self, parent: tk.Widget, key: str, **kwargs: object) -> ttk.Button:
        return self.remember_text(ttk.Button(parent, text=self.tr(key), **kwargs), key)  # type: ignore[return-value]

    def t_checkbutton(self, parent: tk.Widget, key: str, **kwargs: object) -> ttk.Checkbutton:
        return self.remember_text(ttk.Checkbutton(parent, text=self.tr(key), **kwargs), key)  # type: ignore[return-value]

    def t_labelframe(self, parent: tk.Widget, key: str, **kwargs: object) -> ttk.LabelFrame:
        return self.remember_text(ttk.LabelFrame(parent, text=self.tr(key), **kwargs), key)  # type: ignore[return-value]

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=18)
        outer.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(9, weight=1)

        self.t_label(outer, "input_folder").grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(outer, textvariable=self.input_folder).grid(row=0, column=1, sticky="ew", padx=8, pady=(0, 6))
        self.t_button(outer, "choose", command=self.choose_input).grid(row=0, column=2, sticky="ew", pady=(0, 6))

        self.default_output_check = self.t_checkbutton(
            outer,
            "default_output",
            variable=self.use_default_output,
            command=self.toggle_output,
        )
        self.default_output_check.grid(row=1, column=1, columnspan=2, sticky="w", pady=(0, 8))

        self.t_label(outer, "output").grid(row=2, column=0, sticky="w", pady=(0, 6))
        self.output_entry = ttk.Entry(outer, textvariable=self.output_folder, state="disabled")
        self.output_entry.grid(row=2, column=1, sticky="ew", padx=8, pady=(0, 6))
        self.output_button = self.t_button(outer, "choose", command=self.choose_output, state="disabled")
        self.output_button.grid(row=2, column=2, sticky="ew", pady=(0, 6))

        options = ttk.Frame(outer)
        options.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(6, 10))
        options.columnconfigure(1, weight=1)

        self.t_label(options, "language").grid(row=0, column=0, sticky="w")
        self.language_combo = ttk.Combobox(
            options,
            textvariable=self.language,
            values=list(LANGUAGES.values()),
            state="readonly",
            width=18,
        )
        self.language_combo.grid(row=0, column=1, sticky="w", padx=10)
        self.language_combo.bind("<<ComboboxSelected>>", self.change_language)

        self.t_label(options, "preset").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.preset_combo = ttk.Combobox(
            options,
            textvariable=self.preset,
            values=self.preset_labels,
            state="readonly",
            width=18,
        )
        self.preset_combo.grid(row=1, column=1, sticky="w", padx=10, pady=(10, 0))
        self.preset_combo.bind("<<ComboboxSelected>>", self.update_preset_label)
        self.preset_label = ttk.Label(options, text=self.preset_label_for_key(DEFAULT_PRESET))
        self.preset_label.grid(row=1, column=2, sticky="e", pady=(10, 0))

        self.t_label(options, "intensity").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Scale(options, from_=0.0, to=2.0, variable=self.strength, command=self.update_strength_label).grid(
            row=2,
            column=1,
            sticky="ew",
            padx=10,
            pady=(10, 0),
        )
        self.strength_label = ttk.Label(options, text="1.00", width=5)
        self.strength_label.grid(row=2, column=2, sticky="e", pady=(10, 0))

        self.t_label(options, "quality").grid(row=3, column=0, sticky="w", pady=(10, 0))
        ttk.Spinbox(options, from_=1, to=100, textvariable=self.quality, width=8).grid(
            row=3,
            column=1,
            sticky="w",
            padx=10,
            pady=(10, 0),
        )

        checks = ttk.Frame(outer)
        checks.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        self.t_checkbutton(
            checks,
            "include_subfolders",
            variable=self.recursive,
            command=self.refresh_samples,
        ).grid(row=0, column=0, sticky="w")
        self.t_checkbutton(checks, "overwrite", variable=self.overwrite).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(24, 0),
        )

        preview = self.t_labelframe(outer, "sample_preview", padding=10)
        preview.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        preview.columnconfigure(0, weight=1)
        preview.columnconfigure(1, weight=1)

        preview_actions = ttk.Frame(preview)
        preview_actions.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        preview_actions.columnconfigure(2, weight=1)
        self.t_button(preview_actions, "previous_photo", command=lambda: self.change_sample(-1)).grid(
            row=0,
            column=0,
            sticky="w",
        )
        self.t_button(preview_actions, "next_photo", command=lambda: self.change_sample(1)).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(8, 0),
        )
        self.sample_label = ttk.Label(preview_actions, text=self.tr("no_sample"))
        self.sample_label.grid(row=0, column=2, sticky="e")

        self.original_label = self.t_label(preview, "original")
        self.original_label.grid(row=1, column=0, sticky="w")
        self.corrected_label = self.t_label(preview, "corrected")
        self.corrected_label.grid(row=1, column=1, sticky="w", padx=(10, 0))
        self.original_preview = ttk.Label(preview, anchor="center")
        self.original_preview.grid(row=2, column=0, sticky="nsew", pady=(4, 0))
        self.corrected_preview = ttk.Label(preview, anchor="center")
        self.corrected_preview.grid(row=2, column=1, sticky="nsew", padx=(10, 0), pady=(4, 0))
        self.original_preview.configure(cursor="hand2")
        self.corrected_preview.configure(cursor="hand2")
        self.original_preview.bind("<Button-1>", lambda _event: self.open_large_preview("original"))
        self.corrected_preview.bind("<Button-1>", lambda _event: self.open_large_preview("corrected"))

        photo_settings = ttk.Frame(preview)
        photo_settings.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        photo_settings.columnconfigure(2, weight=1)
        self.t_checkbutton(
            photo_settings,
            "customize_photo",
            variable=self.customize_current_photo,
            command=self.toggle_current_photo_customization,
        ).grid(row=0, column=0, sticky="w")
        self.t_button(photo_settings, "copy_globals", command=self.copy_global_settings_to_photo).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(10, 0),
        )
        self.photo_settings_label = ttk.Label(photo_settings, text=self.tr("global_settings"))
        self.photo_settings_label.grid(row=0, column=2, sticky="e")

        actions = ttk.Frame(outer)
        actions.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        actions.columnconfigure(2, weight=1)
        self.start_button = self.t_button(actions, "start", command=self.start)
        self.start_button.grid(row=0, column=0, sticky="w")
        self.t_button(actions, "open_output", command=self.open_output).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(8, 0),
        )
        ttk.Label(actions, textvariable=self.status).grid(row=0, column=2, sticky="e")

        self.progress = ttk.Progressbar(outer, mode="determinate")
        self.progress.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        self.t_label(outer, "log").grid(row=8, column=0, sticky="w")
        self.log = Text(outer, height=14, wrap="word")
        self.log.grid(row=9, column=0, columnspan=3, sticky="nsew")
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=self.log.yview)
        scrollbar.grid(row=9, column=3, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)

    def change_language(self, _event: object | None = None) -> None:
        current_preset_key = self.selected_preset_key()
        selected_language = self.language.get()
        self.lang_code = LANGUAGE_CODES.get(selected_language, "it")

        self.preset_names = self.build_preset_name_map()
        self.preset_labels = list(self.preset_names.keys())
        self.preset_combo.configure(values=self.preset_labels)
        self.preset.set(self.preset_label_for_key(current_preset_key))
        self.preset_label.configure(text=self.preset.get())

        for widget, key in self.translated_widgets:
            widget.configure(text=self.tr(key))

        if not self.sample_images and self.empty_preview_key:
            self.sample_label.configure(text=self.tr(self.empty_preview_key))

        self.status.set(self.tr(self.status_key, **self.status_values))
        self.update_photo_settings_label()
        if self.large_overlay and self.large_overlay.winfo_ismapped():
            self.render_large_preview()

    def choose_input(self) -> None:
        selected = filedialog.askdirectory(title=self.tr("choose_input_title"))
        if selected:
            self.input_folder.set(selected)
            if self.use_default_output.get():
                self.output_folder.set(str(Path(selected) / "corrected"))
            self.refresh_samples()

    def choose_output(self) -> None:
        selected = filedialog.askdirectory(title=self.tr("choose_output_title"))
        if selected:
            self.output_folder.set(selected)

    def toggle_output(self) -> None:
        use_default = self.use_default_output.get()
        state = "disabled" if use_default else "normal"
        self.output_entry.configure(state=state)
        self.output_button.configure(state=state)
        if use_default and self.input_folder.get():
            self.output_folder.set(str(Path(self.input_folder.get()) / "corrected"))
        self.refresh_samples()

    def update_strength_label(self, _value: str | None = None) -> None:
        self.strength_label.configure(text=f"{self.strength.get():.2f}")
        self.store_current_controls()
        self.schedule_preview_update()

    def update_preset_label(self, _event: object | None = None) -> None:
        self.preset_label.configure(text=self.preset.get())
        self.store_current_controls()
        self.schedule_preview_update()

    def selected_preset_key(self) -> str:
        return self.preset_names.get(self.preset.get(), DEFAULT_PRESET)

    def current_sample_key(self) -> str | None:
        if not self.sample_images:
            return None
        try:
            return str(self.sample_images[self.sample_index].resolve())
        except Exception:
            return str(self.sample_images[self.sample_index])

    def current_sample_settings(self) -> tuple[str, float]:
        sample_key = self.current_sample_key()
        if sample_key and sample_key in self.per_photo_settings:
            return self.per_photo_settings[sample_key]
        return self.global_preset, self.global_strength

    def set_controls_from_settings(self, preset_key: str, strength: float) -> None:
        self.loading_controls = True
        self.preset.set(self.preset_label_for_key(preset_key))
        self.strength.set(clamp(strength, 0.0, 2.0))
        self.preset_label.configure(text=self.preset.get())
        self.strength_label.configure(text=f"{self.strength.get():.2f}")
        self.loading_controls = False

    def load_controls_for_current_sample(self) -> None:
        sample_key = self.current_sample_key()
        is_custom = bool(sample_key and sample_key in self.per_photo_settings)
        self.customize_current_photo.set(is_custom)
        preset_key, strength = self.current_sample_settings()
        self.set_controls_from_settings(preset_key, strength)
        self.update_photo_settings_label()

    def store_current_controls(self) -> None:
        if self.loading_controls:
            return

        preset_key = self.selected_preset_key()
        strength = clamp(float(self.strength.get()), 0.0, 2.0)
        sample_key = self.current_sample_key()
        if sample_key and self.customize_current_photo.get():
            self.per_photo_settings[sample_key] = (preset_key, strength)
        else:
            self.global_preset = preset_key
            self.global_strength = strength
        self.update_photo_settings_label()

    def update_photo_settings_label(self) -> None:
        sample_key = self.current_sample_key()
        if sample_key and sample_key in self.per_photo_settings:
            preset_key, strength = self.per_photo_settings[sample_key]
            self.photo_settings_label.configure(
                text=self.tr("custom_settings", preset=self.preset_label_for_key(preset_key), strength=strength)
            )
        else:
            self.photo_settings_label.configure(text=self.tr("global_settings"))

    def toggle_current_photo_customization(self) -> None:
        sample_key = self.current_sample_key()
        if not sample_key:
            self.customize_current_photo.set(False)
            return

        if self.customize_current_photo.get():
            self.per_photo_settings[sample_key] = (
                self.selected_preset_key(),
                clamp(float(self.strength.get()), 0.0, 2.0),
            )
        else:
            self.per_photo_settings.pop(sample_key, None)
            self.set_controls_from_settings(self.global_preset, self.global_strength)

        self.update_photo_settings_label()
        self.schedule_preview_update()

    def copy_global_settings_to_photo(self) -> None:
        sample_key = self.current_sample_key()
        if not sample_key:
            return

        self.per_photo_settings[sample_key] = (self.global_preset, self.global_strength)
        self.customize_current_photo.set(True)
        self.set_controls_from_settings(self.global_preset, self.global_strength)
        self.update_photo_settings_label()
        self.schedule_preview_update()

    def refresh_samples(self) -> None:
        input_text = self.input_folder.get().strip()
        self.sample_images = []
        self.sample_index = 0

        if not input_text:
            self.clear_preview("no_sample")
            return

        input_folder = Path(input_text).expanduser().resolve()
        if not input_folder.exists() or not input_folder.is_dir():
            self.clear_preview("invalid_folder")
            return

        output_folder = self.current_output_folder(input_folder)
        images = discover_images(input_folder, self.recursive.get())
        if output_folder and output_folder.is_relative_to(input_folder):
            resolved_output = output_folder.resolve()
            images = [
                image
                for image in images
                if not image.resolve().is_relative_to(resolved_output)
            ]

        self.sample_images = images
        if not images:
            self.clear_preview("no_photos_found")
            return

        self.empty_preview_key = ""
        self.load_controls_for_current_sample()
        self.update_preview()

    def current_output_folder(self, input_folder: Path) -> Path | None:
        if self.use_default_output.get():
            output_folder = input_folder / "corrected"
            self.output_folder.set(str(output_folder))
            return output_folder

        output_text = self.output_folder.get().strip()
        if not output_text:
            return None
        return Path(output_text).expanduser().resolve()

    def clear_preview(self, text_key: str) -> None:
        self.empty_preview_key = text_key
        self.sample_label.configure(text=self.tr(text_key))
        self.original_preview.configure(image="", text="")
        self.corrected_preview.configure(image="", text="")
        self.original_preview_image = None
        self.corrected_preview_image = None
        self.customize_current_photo.set(False)
        self.update_photo_settings_label()

    def change_sample(self, direction: int) -> None:
        if not self.sample_images:
            self.refresh_samples()
            return
        self.sample_index = (self.sample_index + direction) % len(self.sample_images)
        self.load_controls_for_current_sample()
        self.update_preview()

    def schedule_preview_update(self) -> None:
        if self.preview_after_id:
            self.root.after_cancel(self.preview_after_id)
        self.preview_after_id = self.root.after(250, self.update_preview)

    def update_preview(self) -> None:
        self.preview_after_id = None
        if not self.sample_images:
            return

        sample = self.sample_images[self.sample_index]
        try:
            with Image.open(sample) as opened:
                original = ImageOps.exif_transpose(opened).convert("RGB")
                preset_key, strength = self.current_sample_settings()
                corrected = enhance(original.copy(), strength, preset_key)

            self.original_preview_image = ImageTk.PhotoImage(self.preview_image(original))
            self.corrected_preview_image = ImageTk.PhotoImage(self.preview_image(corrected))
            self.original_preview.configure(image=self.original_preview_image, text="")
            self.corrected_preview.configure(image=self.corrected_preview_image, text="")
            self.sample_label.configure(text=f"{self.sample_index + 1}/{len(self.sample_images)} - {sample.name}")
        except Exception as exc:  # noqa: BLE001 - keep the GUI responsive when one sample fails.
            self.empty_preview_key = ""
            self.sample_label.configure(text=self.tr("preview_unavailable", error=exc))

    def open_large_preview(self, kind: str) -> None:
        if not self.sample_images:
            return

        self.large_preview_kind = kind
        if self.large_overlay is None:
            self.large_overlay = tk.Frame(self.root, bg="#111111")
            self.large_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.large_overlay.columnconfigure(0, weight=1)
            self.large_overlay.rowconfigure(1, weight=1)

            topbar = tk.Frame(self.large_overlay, bg="#1c1c1c")
            topbar.grid(row=0, column=0, sticky="ew")
            topbar.columnconfigure(0, weight=1)
            tk.Label(
                topbar,
                textvariable=self.large_title,
                bg="#1c1c1c",
                fg="#ffffff",
                anchor="w",
                padx=12,
                pady=8,
            ).grid(row=0, column=0, sticky="ew")
            self.t_button(topbar, "close", command=self.close_large_preview).grid(
                row=0,
                column=1,
                sticky="e",
                padx=10,
                pady=6,
            )

            self.large_image_label = tk.Label(self.large_overlay, bg="#111111", cursor="hand2")
            self.large_image_label.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)
            self.large_image_label.bind("<Button-1>", lambda _event: self.close_large_preview())
            self.large_overlay.bind("<Configure>", lambda _event: self.render_large_preview())
            self.root.bind("<Escape>", lambda _event: self.close_large_preview())
        else:
            self.large_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.large_overlay.lift()

        self.render_large_preview()

    def close_large_preview(self) -> None:
        if self.large_overlay:
            self.large_overlay.place_forget()
        self.large_preview_image = None

    def render_large_preview(self) -> None:
        if not self.large_overlay or not self.large_image_label or not self.sample_images:
            return

        sample = self.sample_images[self.sample_index]
        try:
            with Image.open(sample) as opened:
                image = ImageOps.exif_transpose(opened).convert("RGB")
            title_prefix = self.tr("original")
            if self.large_preview_kind == "corrected":
                preset_key, strength = self.current_sample_settings()
                image = enhance(image, strength, preset_key)
                title_prefix = self.tr(
                    "corrected_large",
                    preset=self.preset_label_for_key(preset_key),
                    strength=strength,
                )

            self.large_title.set(f"{title_prefix} - {sample.name}")
            available_width = max(self.large_overlay.winfo_width() - 24, 320)
            available_height = max(self.large_overlay.winfo_height() - 76, 240)
            image.thumbnail((available_width, available_height), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (available_width, available_height), (17, 17, 17))
            x = (available_width - image.width) // 2
            y = (available_height - image.height) // 2
            canvas.paste(image, (x, y))
            self.large_preview_image = ImageTk.PhotoImage(canvas)
            self.large_image_label.configure(image=self.large_preview_image)
        except Exception as exc:  # noqa: BLE001 - preview should fail softly.
            self.large_title.set(self.tr("preview_unavailable", error=exc))

    def preview_image(self, image: Image.Image) -> Image.Image:
        canvas_size = (300, 210)
        image = image.copy()
        image.thumbnail(canvas_size, Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", canvas_size, (245, 245, 245))
        x = (canvas_size[0] - image.width) // 2
        y = (canvas_size[1] - image.height) // 2
        canvas.paste(image, (x, y))
        return canvas

    def start(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        input_text = self.input_folder.get().strip()
        if not input_text:
            messagebox.showerror(self.tr("missing_folder_title"), self.tr("missing_folder_message"))
            return

        input_folder = Path(input_text).expanduser().resolve()
        if not input_folder.exists() or not input_folder.is_dir():
            messagebox.showerror(
                self.tr("invalid_folder_title"),
                self.tr("invalid_folder_message", folder=input_folder),
            )
            return

        if self.use_default_output.get():
            output_folder = input_folder / "corrected"
            self.output_folder.set(str(output_folder))
        else:
            output_text = self.output_folder.get().strip()
            if not output_text:
                messagebox.showerror(self.tr("missing_output_title"), self.tr("missing_output_message"))
                return
            output_folder = Path(output_text).expanduser().resolve()

        self.last_output_folder = output_folder
        self.progress.configure(value=0, maximum=1)
        self.log.delete("1.0", "end")
        self.start_button.configure(state="disabled")
        self.set_status("processing")

        self.worker = threading.Thread(
            target=self._run_batch,
            args=(
                input_folder,
                output_folder,
                self.recursive.get(),
                self.global_strength,
                self.global_preset,
                dict(self.per_photo_settings),
                int(clamp(int(self.quality.get()), 1, 100)),
                self.overwrite.get(),
                self.lang_code,
            ),
            daemon=True,
        )
        self.worker.start()

    def localized_process_message(
        self,
        language: str,
        status: str,
        source: Path,
        destination: Path,
        message: str,
    ) -> str:
        if language == "it":
            return message

        if status == "processed":
            return f"ok: {source} -> {destination}"
        if status == "skipped":
            return text_for(language, "skipped_existing", destination=destination)

        detail = message.split(": ", 1)[1] if ": " in message else message
        return text_for(language, "failed_image", source=source, detail=detail)

    def _run_batch(
        self,
        input_folder: Path,
        output_folder: Path,
        recursive: bool,
        strength: float,
        preset_name: str,
        per_photo_settings: dict[str, tuple[str, float]],
        quality: int,
        overwrite: bool,
        language: str,
    ) -> None:
        try:
            images = discover_images(input_folder, recursive)
            if output_folder.is_relative_to(input_folder):
                resolved_output = output_folder.resolve()
                images = [
                    image
                    for image in images
                    if not image.resolve().is_relative_to(resolved_output)
                ]

            if not images:
                self.queue.put(("log", text_for(language, "no_supported")))
                self.queue.put(("done", (0, 0, 0)))
                return

            self.queue.put(("maximum", len(images)))
            self.queue.put(("log", text_for(language, "found_images", count=len(images))))
            self.queue.put(("log", f"Output: {output_folder}\n"))
            self.queue.put(
                (
                    "log",
                    text_for(
                        language,
                        "preset_log",
                        preset=preset_label_for_language(preset_name, language),
                    ),
                )
            )
            self.queue.put(("log", text_for(language, "intensity_log", strength=strength)))
            if per_photo_settings:
                self.queue.put(("log", text_for(language, "custom_photos_log", count=len(per_photo_settings))))

            processed = 0
            skipped = 0
            failed = 0
            for index, source in enumerate(images, start=1):
                source_settings = per_photo_settings.get(str(source.resolve()), (preset_name, strength))
                source_preset, source_strength = source_settings
                status, message = process_image(
                    source=source,
                    input_folder=input_folder,
                    output_folder=output_folder,
                    strength=source_strength,
                    preset_name=source_preset,
                    quality=quality,
                    overwrite=overwrite,
                    dry_run=False,
                )
                if status == "processed":
                    processed += 1
                elif status == "skipped":
                    skipped += 1
                else:
                    failed += 1

                destination = output_path_for(source, input_folder, output_folder)
                self.queue.put(("log", f"{self.localized_process_message(language, status, source, destination, message)}\n"))
                self.queue.put(("progress", index))

            self.queue.put(("done", (processed, skipped, failed)))
        except Exception as exc:  # noqa: BLE001 - show unexpected GUI errors to the user.
            self.queue.put(("error", str(exc)))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "log":
                    self.log.insert("end", str(payload))
                    self.log.see("end")
                elif kind == "maximum":
                    self.progress.configure(maximum=int(payload), value=0)
                elif kind == "progress":
                    self.progress.configure(value=int(payload))
                elif kind == "done":
                    processed, skipped, failed = payload
                    self.start_button.configure(state="normal")
                    self.set_status(
                        "done_status",
                        processed=processed,
                        skipped=skipped,
                        failed=failed,
                    )
                    done_message = self.status.get()
                    self.log.insert("end", f"\n{done_message}\n")
                    self.log.see("end")
                    if failed:
                        messagebox.showwarning(
                            self.tr("completed_errors_title"),
                            self.tr("completed_errors_message"),
                        )
                    else:
                        messagebox.showinfo(self.tr("completed_title"), self.tr("completed_message"))
                elif kind == "error":
                    self.start_button.configure(state="normal")
                    self.set_status("error_status")
                    messagebox.showerror(self.tr("error"), str(payload))
        except queue.Empty:
            pass

        self.root.after(100, self._poll_queue)

    def open_output(self) -> None:
        path = self.last_output_folder or Path(self.output_folder.get().strip() or ".")
        if not path.exists():
            messagebox.showinfo(self.tr("output_missing_title"), self.tr("output_missing_message"))
            return

        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)


def main() -> int:
    root = Tk()
    PhotoCorrectorApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
