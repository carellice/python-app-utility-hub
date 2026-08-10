<p align="center">
  <img src="logo.png" alt="Comic Tag Editor logo" width="220">
</p>

# Comic Tag Editor

**Comic Tag Editor** e' una piccola applicazione desktop in Python per
aggiornare i metadati dei fumetti digitali in PDF usando le informazioni
contenute nel nome del file.

L'obiettivo e' semplice: scegli una cartella, controlli l'anteprima dei dati
riconosciuti e scrivi i metadati nei PDF con un click.

## Funzioni

- Interfaccia grafica leggera basata su `tkinter`.
- Selezione di una cartella dalla finestra di sistema.
- Lettura automatica dei PDF, CBR e CBZ presenti nella cartella scelta.
- Anteprima di titolo, autore, anno, serie e numero.
- Impostazione di una serie comune per tutti i fumetti della cartella.
- Impostazione di autori comuni per tutti i fumetti della cartella.
- Conversione dei fumetti `.cbr` e `.cbz` in PDF.
- Scrittura dei metadati PDF con `pypdf`.
- Backup opzionale dei file originali in formato `.bak`.
- Avvio su macOS e Windows con doppio click.

## Avvio Rapido

Su macOS puoi aprire l'app con un doppio click su:

```text
Avvia Comic Tag Editor.command
```

Su Windows puoi aprire l'app con un doppio click su:

```text
Avvia Comic Tag Editor.bat
```

Al primo avvio il lanciatore crea automaticamente un ambiente Python locale
nella cartella `.venv` e installa le dipendenze necessarie. Su macOS, dopo
l'avvio dell'interfaccia grafica, la finestra del Terminale viene chiusa
automaticamente.

## Uso

1. Apri `Avvia Comic Tag Editor.command` su macOS oppure `Avvia Comic Tag Editor.bat` su Windows.
2. Premi **Scegli cartella**.
3. Seleziona la cartella che contiene i tuoi fumetti in PDF, CBR o CBZ.
4. Controlla o modifica il campo **Serie per Kobo**.
5. Scrivi nel campo **Autori per Kobo** gli autori da applicare a tutta la cartella.
6. Se vuoi cambiare serie o autore di un singolo PDF, selezionalo nella tabella
   e usa il pannello **PDF selezionato**.
7. Se nella cartella ci sono file `.cbr` o `.cbz`, usa il pulsante di conversione relativo.
8. Lascia attivo il backup `.bak` se vuoi conservare gli originali.
9. Premi **Scrivi metadati**.

## Conversione CBR E CBZ In PDF

I pulsanti **Converti CBR in PDF** e **Converti CBZ in PDF** convertono tutti i
file del formato relativo presenti nella cartella selezionata. Ogni PDF viene
creato accanto all'archivio originale con lo stesso nome:

```text
Fumetto.cbr -> Fumetto.pdf
Fumetto.cbz -> Fumetto.pdf
```

Se il PDF esiste gia', la conversione di quell'archivio viene saltata per
evitare di sovrascrivere file esistenti.

I CBR e i CBZ vengono mostrati nella tabella insieme ai PDF, nella colonna
**Tipo**. Il pulsante **Scrivi metadati** modifica solo i PDF; dopo la
conversione puoi scrivere i metadati sui nuovi PDF creati.

I file `.cbr` sono archivi RAR: per estrarli l'app cerca automaticamente uno di
questi strumenti nel sistema:

- `unar`
- `bsdtar`
- `7z`
- `7zz`

Su macOS, se la conversione segnala che manca un estrattore RAR, installa `unar`
con Homebrew:

```bash
brew install unar
```

I file `.cbz` sono archivi ZIP e non richiedono strumenti esterni oltre a
Python.

## Serie Per Kobo

Quando scegli una cartella, il campo **Serie per Kobo** viene compilato con il
nome della cartella. Puoi cambiarlo prima di scrivere i metadati e l'anteprima
si aggiorna automaticamente.

La serie viene applicata a tutti i PDF della cartella selezionata. Se il numero
del volume e' presente nel nome file, viene mantenuto e scritto nei metadati
insieme alla serie.

Per i PDF l'app salva la serie nei campi metadati disponibili, inclusi
`Subject`, `Keywords`, `Series` e `SeriesIndex`. Se il Kobo aveva gia' importato
i file, puo' essere necessario rimuoverli dal dispositivo e copiarli di nuovo
per fargli rileggere i metadati aggiornati.

## Autori Per Kobo

Il campo **Autori per Kobo** e' libero: puoi scrivere uno o piu' autori, per
esempio:

```text
Alan Moore, Dave Gibbons
```

Se lo lasci vuoto, l'app mantiene gli autori ricavati dai nomi file, quando
presenti. Se lo compili, quel valore viene applicato a tutti i PDF della
cartella selezionata e scritto nel campo `Author` del PDF.

## Modifiche Singole

Puoi modificare **Serie** e **Autore** anche per un singolo PDF:

1. Seleziona una riga `PDF` nella tabella.
2. Modifica i campi nel pannello **PDF selezionato**.
3. Premi **Salva su questo PDF**.

La modifica singola ha precedenza sui campi globali **Serie per Kobo** e
**Autori per Kobo**. Con **Usa valori globali** puoi rimuovere la modifica
singola e tornare ai valori generali della cartella.

Il pulsante **Serie/Autore = Titolo** imposta automaticamente, per il PDF
selezionato, sia **Serie** sia **Autore** uguali al titolo mostrato in tabella.

## Formati Riconosciuti

L'app imposta sempre il titolo usando il nome del file cosi' com'e', togliendo
solo l'estensione.

Per esempio:

```text
Batman 001 - Anno Uno.pdf -> titolo: Batman 001 - Anno Uno
```

Per gli altri metadati riconosce anche questi formati:

| Nome file | Altri metadati riconosciuti |
| --- | --- |
| `Autore - Titolo (2024).pdf` | autore, anno |
| `Titolo (2024).pdf` | anno |
| `Serie 001 - Titolo.pdf` | serie, numero |
| `Serie.001.Titolo.pdf` | serie, numero |

## Installazione Manuale

Se preferisci avviare l'app da Terminale:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 comic_tag_editor.py
```

Su Windows, da Prompt dei comandi:

```bat
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python comic_tag_editor.py
```

## Requisiti

- macOS, Windows o Linux con Python 3.
- `pypdf`, installato tramite `requirements.txt`.
- `Pillow`, installato tramite `requirements.txt`.
- `unar`, `bsdtar`, `7z` o `7zz` per convertire i file `.cbr`.
- Nessuno strumento esterno per convertire i file `.cbz`.
- `tkinter`, normalmente incluso con Python.

## Sicurezza Dei File

Quando l'opzione backup e' attiva, prima di modificare un PDF l'app crea una
copia accanto al file originale:

```text
NomeFumetto.pdf.bak
```

Il backup viene creato solo se non esiste gia', cosi' non viene sovrascritto
un backup precedente.

## Struttura Del Progetto

```text
comic-tag-editor/
|-- Avvia Comic Tag Editor.command
|-- Avvia Comic Tag Editor.bat
|-- comic_tag_editor.py
|-- logo.png
|-- README.md
`-- requirements.txt
```
