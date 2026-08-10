<p align="center">
  <img src="assets/python-app-utility-hub-logo.png" width="132" alt="Logo Python App Utility Hub">
</p>

<h1 align="center">Python App Utility Hub</h1>

<p align="center"><strong>Le tue utility desktop, tutte nello stesso punto.</strong><br>
Un launcher pulito per i piccoli strumenti Python che usi davvero.</p>

---

## Cos'è

Python App Utility Hub raccoglie le utility desktop in un'unica finestra semplice da usare. Seleziona un programma, leggi una breve descrizione e aprilo senza dover ricordare dove si trova il suo file di avvio.

Ogni utility mantiene la propria cartella, le proprie risorse e la propria documentazione. Il launcher condivide invece un solo ambiente Python, così l'intera raccolta rimane ordinata e pronta all'uso.

## Utility incluse

| Utility | Per cosa usarla |
| --- | --- |
| **Comic Tag Editor** | Modificare i metadati di fumetti PDF, CBR e CBZ. |
| **MP3 Tag Editor** | Convertire file audio in MP3 e aggiornare i tag dei brani. |
| **Correzione colore foto** | Migliorare automaticamente colore, contrasto e nitidezza. |
| **Foto simili** | Individuare immagini duplicate o molto simili. |
| **Immagini in PDF** | Creare uno o più PDF a partire da una cartella di immagini. |
| **Estrai audio da video** | Estrarre una o più tracce audio da un filmato. |
| **Editor tracce e sottotitoli** | Aggiungere, rimuovere e riordinare tracce audio e sottotitoli. |

## Per iniziare

Su macOS fai doppio clic su `Avvia Python App Utility Hub.command`.

Su Windows fai doppio clic su `Avvia Python App Utility Hub.bat`.

Al primo avvio viene creato automaticamente l'ambiente `.venv` e vengono installate le dipendenze condivise. Dal menu scegli l'utility e premi **Apri**; puoi lasciare aperto il launcher e avviare più programmi quando ne hai bisogno.

L'interfaccia è disponibile sia in **Italiano** sia in **English**: puoi cambiare lingua direttamente dal selettore in alto.

## Nota per audio e video

Le utility che elaborano audio o video richiedono **FFmpeg** e, quando indicato, **FFprobe** disponibili nel `PATH` del sistema.

## Una raccolta ordinata

- Un unico launcher desktop per sette utility Python.
- Un ambiente virtuale condiviso, senza installazioni duplicate.
- Ogni app resta isolata nella propria sottocartella di `apps/`.

---

Creato con il ❤️ da F.C.
