# Video Track & Subtitle Editor

<p align="center">
  <img src="logo.png" alt="Logo di Video Track & Subtitle Editor" width="180">
</p>

Una piccola applicazione grafica per aggiungere, rimuovere e riordinare tracce
audio e sottotitoli in un filmato. Il video non viene mai ricodificato: FFmpeg
esegue una **copia diretta dei flussi** (`-c copy`), quindi qualità e codec del
video restano identici all'originale.

## Funzioni

- visualizza tutte le tracce audio e sottotitoli già presenti;
- include o esclude singole tracce dal file esportato;
- aggiunge audio (`AAC`, `FLAC`, `MP3`, `AC3`, `DTS`, ecc.) e sottotitoli
  (`SRT`, `ASS`, `VTT`, `SUP`, ecc.) da file esterni;
- modifica lingua, titolo e flag “predefinita”/“forzata”;
- riordina le tracce dello stesso tipo;
- mostra avanzamento e permette di annullare l'esportazione;
- usa un tema chiaro ad alto contrasto anche quando macOS è in modalità scura;
- anima subito la barra di lavoro e disabilita i controlli durante l'esportazione;
- può spostare l'originale nel Cestino o eliminarlo definitivamente, ma soltanto
  dopo che il nuovo file è stato completato e verificato;
- non modifica mai il file originale e prepara l'output in un file temporaneo
  prima di finalizzarlo.

## Requisiti

- Python 3.10 o successivo con Tkinter;
- [FFmpeg](https://ffmpeg.org/) (`ffmpeg` e `ffprobe`).

Su macOS con Homebrew:

```bash
brew install ffmpeg
```

## Avvio

Dal Terminale, dentro questa cartella:

```bash
python3 main.py
```

Su macOS puoi anche fare doppio clic su `Avvia applicazione.command`. Il launcher
avvia l'interfaccia in modo indipendente e richiude automaticamente Terminale.
Alla prima apertura potrebbe essere necessario usare clic destro → **Apri**.

## Uso rapido

1. Premi **Apri filmato…**.
2. Seleziona una traccia e usa **Includi / escludi** o **Rimuovi**.
3. Usa **＋ Audio** o **＋ Sottotitoli** per aggiungere file esterni.
4. Con **Modifica dettagli…** puoi impostare lingua, titolo e flag.
5. Facoltativamente, seleziona **Rimuovi il file originale dopo un'esportazione
   riuscita** e scegli tra Cestino ed eliminazione definitiva.
6. Scegli il file di destinazione e premi **Esporta senza ricodifica**.

La modalità **Cestino** è quella predefinita e consigliata. L'eliminazione
definitiva richiede sempre una conferma esplicita. Se l'esportazione viene
annullata o fallisce, l'originale non viene toccato. Se la rimozione non riesce,
il nuovo filmato viene comunque conservato e l'app segnala che l'originale è
ancora presente.

Il formato `.mkv` è quello consigliato perché accetta quasi tutti i codec audio
e sottotitoli senza conversione. MP4, MOV e WebM sono disponibili, ma possono
rifiutare alcuni codec: in questo caso l'app mostra l'errore e suggerisce MKV.

## Nota sulla sincronizzazione

Le tracce esterne devono essere già sincronizzate con il filmato. L'app cambia
solo il contenitore e i metadati, non il contenuto né la temporizzazione dei
flussi.

## Test

```bash
python3 -m unittest discover -s tests -v
```
