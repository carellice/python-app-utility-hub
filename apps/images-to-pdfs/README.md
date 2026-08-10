<p align="center">
  <img src="logo.png" alt="Logo Immagini in PDF" width="320">
</p>

# Immagini in PDF per macOS

Applicazione desktop in Python che converte le immagini della cartella
selezionata oppure analizza le sue sottocartelle dirette e crea un PDF separato
per ciascuna di esse.

## Funzioni

- supporta JPG, JPEG, PNG, WebP, BMP, TIF e TIFF, anche con estensioni maiuscole;
- ordina i nomi in modo naturale (`2.png` prima di `10.png`);
- applica l'orientamento EXIF e mantiene le proporzioni originali;
- converte la trasparenza in uno sfondo bianco;
- continua se una singola immagine è danneggiata;
- consente di sovrascrivere, saltare o numerare i PDF già esistenti;
- mostra avanzamento, cartella corrente, log e riepilogo finale;
- può aprire automaticamente la cartella di destinazione.

La modalità viene scelta automaticamente:

- se la cartella selezionata contiene immagini supportate, quelle immagini
  vengono convertite in un unico PDF con lo stesso nome della cartella e le
  eventuali sottocartelle non vengono analizzate;
- se non contiene immagini dirette, vengono esaminate esclusivamente le
  sottocartelle immediate e viene creato un PDF per ognuna di esse.

Le directory più profonde vengono sempre ignorate. Se la cartella di output è
una sottocartella diretta della sorgente, viene esclusa automaticamente dalla
scansione.

## Requisiti

- macOS 12 o successivo;
- Python 3.10 o successivo, con Tkinter;
- Pillow.

Il Python scaricato da [python.org](https://www.python.org/downloads/macos/)
include normalmente Tkinter. La versione fornita da alcuni package manager
potrebbe richiedere il relativo pacchetto Tk separato.

## Avvio

### Con doppio clic

Fare doppio clic su **Avvia Immagini in PDF.command**. Lo script avvia
l'interfaccia in background e chiude automaticamente la finestra Terminale
utilizzata per l'avvio. Eventuali messaggi tecnici vengono salvati nel file
temporaneo `immagini-in-pdf-avvio.log` della sessione macOS.

Al primo avvio macOS potrebbe chiedere conferma perché il file proviene da uno
sviluppatore non identificato: fare clic destro sul file, scegliere **Apri** e
confermare una sola volta.

### Dal Terminale

Aprire Terminale nella cartella del progetto ed eseguire:

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

Nell'interfaccia:

1. scegliere la cartella principale;
2. scegliere se salvare i PDF lì o in un'altra cartella;
3. impostare la gestione dei file già esistenti;
4. premere **Avvia conversione**.

## Creazione dell'app macOS

Lo script seguente prepara un ambiente virtuale di build isolato, installa
PyInstaller e crea un bundle `.app` autonomo:

```bash
./build_macos.sh
```

Il risultato si trova in `dist/Immagini in PDF.app`. Il bundle non è firmato:
per distribuirlo ad altri Mac è consigliabile applicare firma Developer ID e
notarizzazione Apple. Questi passaggi richiedono un account Apple Developer e
certificati personali, quindi non possono essere incorporati nel progetto.

## Test

```bash
python3 -m unittest discover -s tests -v
```

I test creano cartelle e immagini temporanee, senza modificare file personali.
