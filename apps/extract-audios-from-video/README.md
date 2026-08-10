<p align="center">
  <img src="logo.png" alt="Extract Audio Tracks logo" width="180">
</p>

# Estrai tracce audio da video / Extract Audio Tracks

[Italiano](#italiano) | [English](#english)

## Italiano

Piccolo programma per macOS e Windows che estrae tutte le tracce audio presenti in un video, anche quando il file e multitraccia.

### Requisiti

- Python 3
- FFmpeg, con `ffmpeg` e `ffprobe` disponibili nel PATH

Installazione rapida di FFmpeg:

- macOS con Homebrew: `brew install ffmpeg`
- Windows con Winget: `winget install Gyan.FFmpeg`

In alternativa puoi mettere `ffmpeg` e `ffprobe` nella stessa cartella di `extract_audio_tracks.py`, oppure in `ffmpeg/bin`.

### Uso con interfaccia grafica

#### macOS

Apri `Avvia_Mac.command`.

Il launcher avvia la GUI e chiude automaticamente la finestra Terminale aperta da macOS.

Se macOS blocca il file perche scaricato da internet, apri Terminale nella cartella del progetto ed esegui:

```sh
chmod +x Avvia_Mac.command
./Avvia_Mac.command
```

#### Windows

Doppio click su `Avvia_Windows.bat`.

Il launcher usa `pyw`/`pythonw` quando disponibili, quindi la finestra del prompt non resta aperta.

### Lingua

Nella finestra principale puoi scegliere `it` oppure `en` dal menu lingua.

### Anteprima e nomi tracce

Quando premi `Estrai tracce audio`, il programma prima analizza il video e poi apre una finestra con tutte le tracce audio trovate.

Per ogni traccia puoi:

- usare il bottone `Play`/`Pausa` per ascoltare o fermare l'anteprima;
- spostare la barra della posizione per scegliere davvero da dove ascoltare;
- scrivere solo il nome della traccia, ad esempio `Microfono`, `Audio PC` o `Mix completo`;
- confermare con `Estrai con questi nomi`.

Il file finale mantiene come base il nome del video e aggiunge il nome scelto per la traccia. Per esempio, da `registrazione_OBS.mp4` e `Microfono` ottieni `registrazione_OBS_Microfono.m4a`.

### Uso da terminale

```sh
python3 extract_audio_tracks.py "video.mp4"
```

Scegliere la cartella di output:

```sh
python3 extract_audio_tracks.py "video.mp4" --output "tracce-audio"
```

Convertire tutte le tracce in WAV:

```sh
python3 extract_audio_tracks.py "video.mp4" --mode wav
```

Usare l'interfaccia da terminale in inglese:

```sh
python3 extract_audio_tracks.py "video.mp4" --lang en
```

Di default il programma prova a mantenere il codec originale, senza ricodificare l'audio. Se il contenitore scelto non e compatibile, riprova automaticamente con `.mka`.

## English

A small macOS and Windows program that extracts every audio track from a video, including multi-track videos.

### Requirements

- Python 3
- FFmpeg, with `ffmpeg` and `ffprobe` available in PATH

Quick FFmpeg install:

- macOS with Homebrew: `brew install ffmpeg`
- Windows with Winget: `winget install Gyan.FFmpeg`

Alternatively, place `ffmpeg` and `ffprobe` in the same folder as `extract_audio_tracks.py`, or inside `ffmpeg/bin`.

### GUI Usage

#### macOS

Open `Avvia_Mac.command`.

The launcher starts the GUI and automatically closes the Terminal window opened by macOS.

If macOS blocks the file because it was downloaded from the internet, open Terminal in the project folder and run:

```sh
chmod +x Avvia_Mac.command
./Avvia_Mac.command
```

#### Windows

Double-click `Avvia_Windows.bat`.

The launcher uses `pyw`/`pythonw` when available, so the command prompt window does not stay open.

### Language

In the main window you can choose `it` or `en` from the language menu.

### Preview and Track Names

When you click `Extract audio tracks`, the program first analyzes the video and then opens a window with every audio track it found.

For each track you can:

- use the `Play`/`Pause` button to preview or stop playback;
- move the position slider to choose exactly where to listen from;
- type only the track name, for example `Microphone`, `PC Audio`, or `Full Mix`;
- confirm with `Extract with these names`.

The final file keeps the video name as its base and appends the track name you chose. For example, from `OBS_recording.mp4` and `Microphone`, you get `OBS_recording_Microphone.m4a`.

### Terminal Usage

```sh
python3 extract_audio_tracks.py "video.mp4"
```

Choose the output folder:

```sh
python3 extract_audio_tracks.py "video.mp4" --output "audio-tracks"
```

Convert every track to WAV:

```sh
python3 extract_audio_tracks.py "video.mp4" --mode wav
```

Use the terminal interface in English:

```sh
python3 extract_audio_tracks.py "video.mp4" --lang en
```

By default, the program tries to keep the original audio codec without re-encoding. If the selected container is not compatible, it automatically retries with `.mka`.
