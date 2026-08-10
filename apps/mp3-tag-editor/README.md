# MP3 Tag Editor

![MP3 Tag Editor](logo.png)

Programma Python con interfaccia grafica per convertire file audio in MP3 e modificare i tag dei brani, anche in gruppo, con caricamento tramite drag-and-drop.

## Requisiti

- Python 3.10 o superiore
- FFmpeg installato e disponibile nel `PATH`
- Dipendenze Python in `requirements.txt`

Su macOS puoi installare FFmpeg con Homebrew:

```bash
brew install ffmpeg
```

Su Windows puoi installare FFmpeg da https://ffmpeg.org/ e aggiungere la cartella `bin` al `PATH`.

## Prima configurazione

### Windows

Doppio clic su:

```text
setup_windows.bat
```

### macOS

Non serve una configurazione manuale: al primo doppio clic su `Avvia_Mac.command`, lo script crea da solo l'ambiente Python e installa le dipendenze.

Se macOS impedisce l'apertura dello script, nel Terminale esegui una sola volta:

```bash
chmod +x setup_mac.command Avvia_Mac.command
```

## Avvio senza console lasciata aperta

### Windows

Doppio clic su:

```text
Avvia_Windows.vbs
```

Lo script usa `pythonw.exe`, quindi non lascia aperta la console.

### macOS

Doppio clic su:

```text
Avvia_Mac.command
```

macOS apre per un attimo Terminale per eseguire lo script, poi lo script avvia il programma in background e chiude quella finestra senza chiedere di terminare il processo.

## Uso rapido

- Trascina file audio o cartelle dentro la finestra, quando il drag-and-drop e disponibile.
- Puoi trascinare un'immagine JPG/PNG nella finestra per usarla come nuova copertina, poi premere `Applica ai selezionati`.
- Su macOS il programma usa `tkinterdnd2-universal` per provare il drag-and-drop dentro la finestra; se non e disponibile, puoi trascinare file o cartelle direttamente su `Avvia_Mac.command`.
- Seleziona uno o piu brani dalla tabella.
- Usa `Cmd+A` su macOS o `Ctrl+A` su Windows per selezionare tutti i brani caricati.
- Cambia i campi a destra e premi `Applica tag`: con piu brani selezionati vengono salvati solo i campi che modifichi davvero.
- Per cancellare un tag, svuota quel campo e premi `Applica tag`.
- Usa `Scegli copertina` per assegnare una cover ai brani selezionati e vedere l'anteprima nel pannello a destra.
- Usa `Cartelle per artista` per spostare i brani caricati in sottocartelle basate su artista album o artista brano, dentro la cartella caricata.
- Usa `Rinomina file` per rinominare i file usando solo il titolo del brano.
- Usa `Converti selezionati in MP3` o `Converti tutti in MP3` per creare versioni MP3 accanto ai file originali: i file gia MP3 vengono saltati.

La conversione richiede FFmpeg.
