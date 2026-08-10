# Similar Photos

![Similar Photos logo](logo.png)

**Lingua / Language:** [Italiano](#italiano) | [English](#english)

## Italiano

Una piccola app desktop per trovare foto uguali o simili dentro una cartella, rivederle un gruppo alla volta e conservare solo quelle scelte.

### Lingua

Nel programma puoi cambiare lingua dal menu in alto a destra scegliendo `Italiano` o `English`. Il cambio aggiorna pulsanti, messaggi, gruppi, anteprima e report.

### Avvio

Su macOS, fai doppio clic su:

```text
MacOS.command
```

Su Windows, fai doppio clic su:

```text
Windows.bat
```

Questi script avviano l'interfaccia con il nome del sistema operativo.

Avvio manuale da terminale:

```bash
python3 app.py
```

Se Pillow non fosse installato:

```bash
python3 -m pip install -r requirements.txt
```

### Come funziona

- I duplicati esatti vengono riconosciuti confrontando l'hash SHA-256 dei file.
- Prima dell'analisi, i formati non-JPEG supportati vengono convertiti in copie `.jpg` accanto agli originali.
- Le foto simili vengono raggruppate con un hash percettivo e un controllo colore.
- L'app suggerisce la foto da tenere usando risoluzione, nitidezza e esposizione.
- Dopo l'analisi l'app ti guida gruppo per gruppo e ti chiede quali foto conservare.
- Durante la scelta puoi cliccare sull'anteprima di una foto per vederla a tutto schermo.
- Alla fine, le foto non selezionate nei gruppi vengono spostate nel Cestino del sistema.

### Slider Somiglianza

Lo slider decide quanto l'app deve essere permissiva nel raggruppare foto simili.

- Valori bassi: più prudente, trova quasi solo copie o scatti praticamente identici.
- Valori medi: consigliato, utile per duplicati e raffiche molto simili.
- Valori alti: più permissivo, può trovare più gruppi ma anche includere foto meno simili.

### Formati

L'app prova a convertire e leggere `jpg`, `jpeg`, `png`, `webp`, `bmp`, `gif`, `tif`, `tiff`, `heic` e `heif`. Su macOS gli HEIC possono essere convertiti anche tramite `sips`; sugli altri sistemi il supporto dipende dai formati disponibili nella tua installazione di Pillow.

## English

A small desktop app that finds identical or similar photos inside a folder, lets you review them one group at a time, and keeps only the photos you choose.

### Language

In the app you can switch language from the menu in the top-right corner by choosing `Italiano` or `English`. The switch updates buttons, messages, groups, preview, and report.

### Launch

On macOS, double-click:

```text
MacOS.command
```

On Windows, double-click:

```text
Windows.bat
```

These scripts start the interface with the operating-system name.

Manual launch from the terminal:

```bash
python3 app.py
```

If Pillow is not installed:

```bash
python3 -m pip install -r requirements.txt
```

### How It Works

- Exact duplicates are detected by comparing the SHA-256 hash of each file.
- Before scanning, supported non-JPEG formats are converted into `.jpg` copies next to the originals.
- Similar photos are grouped with a perceptual hash and a color check.
- The app suggests the photo to keep using resolution, sharpness, and exposure.
- After scanning, the app guides you through one group at a time and asks which photos to keep.
- While choosing, you can click a photo preview to view it fullscreen inside the app.
- At the end, unselected photos in the reviewed groups are moved to the system Trash.

### Similarity Slider

The slider controls how permissive the app should be when grouping similar photos.

- Low values: more cautious, finds almost only copies or practically identical shots.
- Medium values: recommended, useful for duplicates and very similar burst shots.
- High values: more permissive, can find more groups but may also include less similar photos.

### Formats

The app tries to convert and read `jpg`, `jpeg`, `png`, `webp`, `bmp`, `gif`, `tif`, `tiff`, `heic`, and `heif`. On macOS, HEIC files can also be converted through `sips`; on other systems support depends on the formats available in your Pillow installation.
