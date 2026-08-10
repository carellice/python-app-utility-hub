"""Interfaccia desktop Tkinter per macOS."""

from __future__ import annotations

import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from .converter import ConversionSummary, ExistingFilePolicy, ImageFolderConverter


POLICY_LABELS = {
    "Sovrascrivi il PDF esistente": ExistingFilePolicy.OVERWRITE,
    "Salta la sottocartella": ExistingFilePolicy.SKIP,
    "Crea una copia numerata": ExistingFilePolicy.NUMBERED_COPY,
}


class ImagesToPdfApp:
    """Finestra principale dell'applicazione."""

    POLL_INTERVAL_MS = 80

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Immagini in PDF")
        self.root.minsize(760, 650)
        self.root.geometry("820x700")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.source_var = tk.StringVar()
        self.destination_mode_var = tk.StringVar(value="source")
        self.destination_var = tk.StringVar()
        self.policy_var = tk.StringVar(value=next(iter(POLICY_LABELS)))
        self.open_when_done_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Pronto")
        self.progress_var = tk.DoubleVar(value=0)

        self._events: queue.Queue[tuple[str, object]] = queue.Queue()
        self._worker: threading.Thread | None = None

        self._configure_style()
        self._build_ui()
        self._update_destination_controls()

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        available = style.theme_names()
        if "aqua" in available:
            style.theme_use("aqua")
        style.configure("Title.TLabel", font=("Helvetica Neue", 20, "bold"))
        style.configure("Subtitle.TLabel", foreground="#555555")
        style.configure("Status.TLabel", font=("Helvetica Neue", 12, "bold"))

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=20)
        outer.grid(row=0, column=0, sticky="nsew")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(6, weight=1)

        ttk.Label(outer, text="Immagini in PDF", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            outer,
            text="Converte la cartella selezionata oppure ogni sua sottocartella.",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 16))

        settings = ttk.LabelFrame(outer, text="Impostazioni", padding=14)
        settings.grid(row=2, column=0, sticky="ew")
        settings.columnconfigure(1, weight=1)

        ttk.Label(settings, text="Cartella principale:").grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=5
        )
        ttk.Entry(settings, textvariable=self.source_var).grid(
            row=0, column=1, sticky="ew", pady=5
        )
        self.source_button = ttk.Button(
            settings, text="Scegli…", command=self._choose_source
        )
        self.source_button.grid(row=0, column=2, padx=(8, 0), pady=5)

        ttk.Label(settings, text="Salva i PDF:").grid(
            row=1, column=0, sticky="nw", padx=(0, 10), pady=5
        )
        destination_options = ttk.Frame(settings)
        destination_options.grid(row=1, column=1, columnspan=2, sticky="ew")
        destination_options.columnconfigure(1, weight=1)

        ttk.Radiobutton(
            destination_options,
            text="Nella cartella principale",
            variable=self.destination_mode_var,
            value="source",
            command=self._update_destination_controls,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(3, 4))
        ttk.Radiobutton(
            destination_options,
            text="In un'altra cartella:",
            variable=self.destination_mode_var,
            value="custom",
            command=self._update_destination_controls,
        ).grid(row=1, column=0, sticky="w")
        self.destination_entry = ttk.Entry(
            destination_options, textvariable=self.destination_var
        )
        self.destination_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0))
        self.destination_button = ttk.Button(
            destination_options, text="Scegli…", command=self._choose_destination
        )
        self.destination_button.grid(row=1, column=2, padx=(8, 0))

        ttk.Label(settings, text="Se il PDF esiste:").grid(
            row=2, column=0, sticky="w", padx=(0, 10), pady=(10, 5)
        )
        self.policy_combo = ttk.Combobox(
            settings,
            textvariable=self.policy_var,
            values=list(POLICY_LABELS),
            state="readonly",
        )
        self.policy_combo.grid(
            row=2, column=1, columnspan=2, sticky="ew", pady=(10, 5)
        )

        ttk.Checkbutton(
            settings,
            text="Apri la cartella di destinazione al termine",
            variable=self.open_when_done_var,
        ).grid(row=3, column=1, columnspan=2, sticky="w", pady=(8, 0))

        actions = ttk.Frame(outer)
        actions.grid(row=3, column=0, sticky="ew", pady=(16, 8))
        actions.columnconfigure(0, weight=1)
        self.start_button = ttk.Button(
            actions, text="Avvia conversione", command=self._start_conversion
        )
        self.start_button.grid(row=0, column=1)

        progress_frame = ttk.Frame(outer)
        progress_frame.grid(row=4, column=0, sticky="ew", pady=(4, 12))
        progress_frame.columnconfigure(0, weight=1)
        ttk.Label(
            progress_frame, textvariable=self.status_var, style="Status.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.progress = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
        )
        self.progress.grid(row=1, column=0, sticky="ew")

        log_header = ttk.Frame(outer)
        log_header.grid(row=5, column=0, sticky="ew")
        log_header.columnconfigure(0, weight=1)
        ttk.Label(log_header, text="Log operazioni").grid(row=0, column=0, sticky="w")
        ttk.Button(log_header, text="Pulisci log", command=self._clear_log).grid(
            row=0, column=1
        )

        self.log_text = scrolledtext.ScrolledText(
            outer,
            wrap=tk.WORD,
            height=14,
            state=tk.DISABLED,
            font=("Menlo", 11),
        )
        self.log_text.grid(row=6, column=0, sticky="nsew", pady=(6, 0))

    def _choose_source(self) -> None:
        selected = filedialog.askdirectory(
            title="Scegli la cartella principale", mustexist=True
        )
        if selected:
            self.source_var.set(selected)

    def _choose_destination(self) -> None:
        selected = filedialog.askdirectory(
            title="Scegli la cartella di destinazione", mustexist=True
        )
        if selected:
            self.destination_var.set(selected)

    def _update_destination_controls(self) -> None:
        state = (
            tk.NORMAL if self.destination_mode_var.get() == "custom" else tk.DISABLED
        )
        self.destination_entry.configure(state=state)
        self.destination_button.configure(state=state)

    def _start_conversion(self) -> None:
        if self._worker and self._worker.is_alive():
            return

        source = Path(self.source_var.get().strip()).expanduser()
        if not self.source_var.get().strip() or not source.is_dir():
            messagebox.showerror(
                "Cartella non valida",
                "Seleziona una cartella principale esistente.",
                parent=self.root,
            )
            return

        if self.destination_mode_var.get() == "source":
            destination = source
        else:
            destination_text = self.destination_var.get().strip()
            if not destination_text:
                messagebox.showerror(
                    "Destinazione mancante",
                    "Scegli la cartella in cui salvare i PDF.",
                    parent=self.root,
                )
                return
            destination = Path(destination_text).expanduser()
            if destination.exists() and not destination.is_dir():
                messagebox.showerror(
                    "Destinazione non valida",
                    "La destinazione selezionata non è una cartella.",
                    parent=self.root,
                )
                return

        policy = POLICY_LABELS[self.policy_var.get()]
        self._set_running(True)
        self.progress_var.set(0)
        self.status_var.set("Preparazione…")
        self._append_log("\n[INIZIO] Conversione avviata")

        self._worker = threading.Thread(
            target=self._run_worker,
            args=(source, destination, policy),
            name="pdf-converter",
            daemon=True,
        )
        self._worker.start()
        self.root.after(self.POLL_INTERVAL_MS, self._process_events)

    def _run_worker(
        self,
        source: Path,
        destination: Path,
        policy: ExistingFilePolicy,
    ) -> None:
        try:
            converter = ImageFolderConverter(
                source,
                destination,
                policy,
                on_log=lambda message: self._events.put(("log", message)),
                on_progress=lambda done, total, folder: self._events.put(
                    ("progress", (done, total, folder))
                ),
            )
            summary = converter.run()
            self._events.put(("done", (summary, destination.resolve())))
        except Exception as exc:
            self._events.put(("fatal", str(exc)))

    def _process_events(self) -> None:
        while True:
            try:
                event_type, payload = self._events.get_nowait()
            except queue.Empty:
                break

            if event_type == "log":
                self._append_log(str(payload))
            elif event_type == "progress":
                done, total, folder = payload  # type: ignore[misc]
                self.progress_var.set(100 if total == 0 else done / total * 100)
                if done < total:
                    self.status_var.set(
                        f"Elaborazione: {folder} ({done + 1} di {total})"
                    )
                else:
                    self.status_var.set("Conversione completata")
            elif event_type == "done":
                summary, destination = payload  # type: ignore[misc]
                self._finish_success(summary, destination)
            elif event_type == "fatal":
                self._finish_failure(str(payload))

        if self._worker and self._worker.is_alive():
            self.root.after(self.POLL_INTERVAL_MS, self._process_events)

    def _finish_success(
        self, summary: ConversionSummary, destination: Path
    ) -> None:
        self._set_running(False)
        self.progress_var.set(100)
        self.status_var.set("Conversione completata")
        summary_text = (
            "Conversione completata.\n\n"
            f"Cartelle considerate: {summary.folders_found}\n"
            f"PDF creati: {summary.pdfs_created}\n"
            f"Cartelle ignorate: {summary.folders_skipped}\n"
            f"Immagini non elaborate: {summary.images_failed}\n"
            f"Errori registrati: {summary.error_count}"
        )
        self._append_log(
            "[FINE] "
            f"{summary.pdfs_created} PDF creati; "
            f"{summary.folders_skipped} cartelle ignorate; "
            f"{summary.images_failed} immagini non elaborate; "
            f"{summary.error_count} errori."
        )
        messagebox.showinfo("Riepilogo", summary_text, parent=self.root)
        if self.open_when_done_var.get():
            self._open_folder(destination)

    def _finish_failure(self, error: str) -> None:
        self._set_running(False)
        self.status_var.set("Conversione non completata")
        self._append_log(f"[ERRORE FATALE] {error}")
        messagebox.showerror(
            "Errore",
            f"Non è stato possibile completare la conversione:\n\n{error}",
            parent=self.root,
        )

    def _set_running(self, running: bool) -> None:
        state = tk.DISABLED if running else tk.NORMAL
        self.start_button.configure(state=state)
        self.source_button.configure(state=state)
        self.policy_combo.configure(state=tk.DISABLED if running else "readonly")
        if running:
            self.destination_button.configure(state=tk.DISABLED)
            self.destination_entry.configure(state=tk.DISABLED)
        else:
            self._update_destination_controls()

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message.rstrip() + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _clear_log(self) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _on_close(self) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showwarning(
                "Conversione in corso",
                "Attendi il completamento della conversione prima di chiudere.",
                parent=self.root,
            )
            return
        self.root.destroy()

    @staticmethod
    def _open_folder(path: Path) -> None:
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            elif sys.platform.startswith("win"):
                subprocess.Popen(["explorer", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError:
            # L'apertura della cartella è una comodità e non invalida i PDF creati.
            pass


def run_app() -> None:
    root = tk.Tk()
    ImagesToPdfApp(root)
    root.mainloop()
