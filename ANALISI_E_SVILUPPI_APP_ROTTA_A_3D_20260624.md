# App "Rotta A 3D" — Analisi tecnica, miglioramenti e sviluppi futuri

**Data:** 2026-06-24 · **Autore analisi:** sessione Claude (sola lettura del codice + verifiche)
**App:** `ROTTA_A_3D.html` (repo `CampoGara3D`) · **Contesto:** 62° Campionato Italiano Traina d'Altura, Ostia 26-27/6/2026, squadra ASD IschiaFishing.

> Documento di **analisi**, non di modifica: la scena non e' stata toccata. Le criticita' qui sotto sono proposte, da validare prima di applicarle.

---

## 1. COS'E' L'APP

Scena **3D interattiva** (Plotly.js) che mostra la **Rotta A** della gara su un **modello batimetrico del fondale** ricavato da dati EMODnet, con la **barca animata** che percorre la rotta dalle 08:00 alle 15:30. Pensata per l'uso **a bordo da telefono/iPad**, anche **offline** (versione PWA in `offline/`), con **posizione GPS reale** e indicazioni di correzione rotta.

E' il ponte fra le guide HTML (dossier, briefing) e lo strumento operativo in mare.

---

## 2. ARCHITETTURA (com'e' fatta oggi)

- **Stack:** Plotly.js (incluso inline → file autoportante), generato da Python con `_build_rotta3d.py`.
- **Pipeline dati batimetria:**
  - `index.html` (scena "madre" CampoGara3D) contiene la superficie 3D del fondale.
  - `_extract_fig.py` estrae `data`/`layout` di quella figura e li salva in `_fig_extracted.json`.
  - `_build_rotta3d.py` ricarica il JSON, vi sovrappone rotta + animazione + GPS + UI e scrive `ROTTA_A_3D.html`.
- **Rotta A:** 8 waypoint (lat/lon + minuto) definiti nel generatore, interpolati nel tempo; start NE (tonni) → discesa SW → banco 717 m → drop-off 924 m → ultima passata.
- **Animazione:** frame ogni 15 min (slider 08:00→15:30): scia in superficie, barca, **beam ecoscandaglio** (cyan), **eco fondo** (profondita'), **rotta tracciata progressivamente sul fondale** (arancione).
- **GPS reale:** `watchPosition` → conversione lat/lon→km locali → cross-track dalla rotta (in/fuori rotta, tolleranza 10-300 m regolabile), bearing al waypoint successivo, "vira a dritta/sinistra di X°", spot piu' vicino.
- **UI mobile:** pulsanti a scomparsa (Legenda/Guida/Vista/GPS/Zoom), meta iOS, `100dvh`, `touch-action:none`; legenda nascosta di default su touch.
- **PWA offline:** `offline/` con `manifest.webmanifest` + `sw.js` (cache-first, pre-cache) → installabile e usabile senza segnale. `.nojekyll` presente nel repo.

---

## 3. VERIFICHE FATTE IN QUESTA SESSIONE (evidenze)

- **Rendering OK:** la scena rende correttamente su **WebKit (Safari)** e **Chromium** in Playwright — 1 canvas WebGL, **0 errori di pagina**. Visibili: batimetria 3D, rotta dorata coi waypoint, barca, beam, scala profondita', UI completa.
- **Waypoint dentro il campo:** test punto-nel-poligono di **tutti gli 8 waypoint** della Rotta A contro il **quadrilatero ufficiale A/B/C/D** (Ord. Capitaneria Roma 67/2026) → **tutti DENTRO**. Nessun rischio "ferrata fuori campo" sulla rotta tracciata.
- **NON verificato:** rendering su iPhone/iPad **fisici** (solo motori desktop); contenuto numerico interno di `_fig_extracted.json` (3 MB); comportamento reale del GPS in mare.

---

## 4. PUNTI DI FORZA

- Idea forte: la **rotta che si "spalma" sul fondale** mentre la barca avanza rende leggibile la relazione rotta-batimetria.
- **GPS + correzioni** gia' funzionanti (cross-track, bearing, vira dx/sx, tolleranza regolabile): e' gia' uno strumento operativo, non solo una visualizzazione.
- **Offline-first** con PWA: la cosa giusta per il mare senza segnale.
- **Autoportante** (plotly inline): nessuna dipendenza di rete a runtime.
- UI **touch-friendly** con pannelli a scomparsa, adatta a iPhone/iPad.

---

## 5. CRITICITA' / FRAGILITA' RILEVATE (dal codice)

| # | Criticita' | Impatto | Dove |
|---|---|---|---|
| C1 | Estrazione batimetria con **offset di byte hardcoded** (`s[4845666:...]`) | ALTO — si rompe in silenzio se `index.html` cambia | pipeline `_extract_fig.py` |
| C2 | Batimetria **ereditata** da `index.html`, non da una sorgente dati canonica | MEDIO — duplicazione/accoppiamento tra le due scene | pipeline |
| C3 | File **8,3 MB** (plotly inline + superficie densa) | MEDIO — primo caricamento lento su 4G; rischio memoria WebGL su iOS | output |
| C4 | SW con **nome cache statico** (`rotta3d-v1`), strategia cache-first | MEDIO — dopo un aggiornamento il telefono puo' servire la versione vecchia | `offline/sw.js` |
| C5 | **Heading GPS** spesso `null` da fermo → manca "vira dx/sx" | BASSO — gia' gestito con messaggio, ma migliorabile | modulo GPS |
| C6 | **Accuratezza GPS** (`coords.accuracy`) non mostrata | BASSO — l'utente non sa se il fix e' affidabile | modulo GPS |
| C7 | Scena 3D **ruotabile senza indicatore Nord persistente** | BASSO — disorientamento dopo rotazioni | scena |
| C8 | Profondita' verticale **non in scala 1:1** (superficie a z piccolo, fondo a ~-900) | BASSO — va spiegato per non ingannare l'occhio | scena |

---

## 6. CONSIGLI DI MIGLIORAMENTO (prioritizzati)

**Priorita' ALTA**
- **Eliminare l'offset hardcoded (C1):** estrarre la figura cercando `Plotly.newPlot(` e bilanciando le parentesi (la logica di matching gia' esiste in `_extract_fig.py`), senza indici di byte fissi. Cosi' la pipeline regge se `index.html` cambia.
- **Sorgente dati batimetrica unica (C2):** salvare il grid EMODnet (x/y/z) in un file dati condiviso (es. `.npz`/`.json`) e far generare *entrambe* le scene da quello, invece di estrarre da un HTML gia' renderizzato.

**Priorita' MEDIA**
- **Versioning automatico della cache PWA (C4):** generare il nome cache dal contenuto/data al build (es. `rotta3d-<hash>`), cosi' l'aggiornamento arriva al telefono. In alternativa strategia *stale-while-revalidate* per gli asset.
- **Alleggerire il primo caricamento (C3):** valutare risoluzione della griglia (decimazione della superficie) e, per la sola versione online, plotly via CDN; mantenere inline solo nella build offline. Misurare il peso prima/dopo.
- **COG calcolato dai fix (C5):** quando `heading` e' nullo, derivare la prua dai due ultimi fix GPS (bearing tra posizioni) per dare comunque "vira dx/sx".

**Priorita' BASSA**
- **Mostrare accuratezza GPS (C6):** stampare `accuracy` e avvisare quando supera la tolleranza impostata.
- **Indicatore Nord persistente (C7)** nella scena 3D.
- **Nota "scala verticale esagerata" (C8)** in legenda/guida.
- **Test su iPhone/iPad fisici** (iOS Safari): WebGL e limiti di memoria su file da 8 MB.

---

## 7. SVILUPPI FUTURI

- **Multi-rotta A/B/C:** ✅ **IMPLEMENTATO** il 2026-06-26 — vedi §9.
- **Registrazione track reale (breadcrumb GPS) + export GPX:** durante l'uscita salva il percorso e i punti di cattura → alimenta la **validazione delle soglie "forti"** del motore decisionale di OstiaSeraPrima (oggi tarate su un solo giorno).
- **Allarmi:** segnale acustico/vibrazione su "fuori rotta" o "vicino a spot".
- **Profilo batimetrico 2D in tempo reale** sotto la barca (sezione del fondo lungo la rotta).
- **Overlay condizioni live** (vento/corrente/CHL) coerente con sera-prima.
- **Modalita' "ora reale":** confronto barca prevista (piano) vs barca reale (GPS) sullo stesso asse temporale.
- **Hub unico** che colleghi questa app, il dossier, le mappe mobile e la guida di bordo.

---

## 8. RIFERIMENTI

- Generatore: `_build_rotta3d.py` · estrazione figura: `_extract_fig.py` · PWA: `_make_pwa.py`, `offline/`.
- Scena madre batimetria: `index.html` (CampoGara3D).
- Dossier rotta (repo GaraOstia2026): `ROTTA_A_LA_MIGLIORE.html`.
- Handover/doc tecnica rotta-3D (repo GaraOstia2026): `HANDOVER_SESSIONE_rotta_a_dossier_3d_20260624.md`, `DOCUMENTAZIONE_TECNICA_rotta_a_dossier_3d_20260624.md`.
- Campo ufficiale A/B/C/D: Ord. Capitaneria di Porto di Roma 67/2026.

---

## 9. VERSIONE MULTI-ROTTA (implementata 2026-06-26)

- **Nuovo generatore** `_build_multirotta.py` (non tocca `_build_rotta3d.py`, rimasto come fallback) → produce **`ROTTA_A_3D.html`**, **`ROTTA_B_3D.html`**, **`ROTTA_C_3D.html`**.
- **Selettore A/B/C** in alto al centro di ogni scena + link **Guida** (apre `GUIDA_RAPIDA_BARCA.html` su GitHub Pages). Il selettore evidenzia la rotta corrente e naviga tra i tre file (stesso layout/codice, animazione e GPS propri di ciascuna rotta).
- **Definizione delle 3 rotte dalla `GUIDA_RAPIDA_BARCA.html`** (sezione "Le tre rotte"): A = NE tonni + SW profondo (consigliata); B = tutto profondo SW (alalunga/spada); C = tutto bordo NE (tonni).
- **Onesta' sui dati:** B e C sono composte **riusando solo waypoint reali gia' presenti** (punti NE/SW della rotta A + spot verificati) — *nessuna coordinata inventata*; **non esiste un GPX** dedicato. Gli **orari** dei waypoint di B/C sono solo **timing dell'animazione**, non tempi di pesca pianificati.
- **Verifiche:** tutti i waypoint di A, B e C risultano **dentro il quadrilatero ufficiale A/B/C/D** (test punto-nel-poligono); rendering confermato con screenshot **WebKit** per B e C (1 canvas WebGL, 0 errori, selettore attivo corretto).
- **Migliorie GPS incluse** (da §6): COG calcolato dai due ultimi fix quando l'heading hardware e' nullo (C5); **accuratezza GPS** mostrata con avviso se supera la tolleranza (C6).
- **LIMITE noto:** la **PWA offline** in `offline/` **non e' stata rigenerata** per il multi-rotta (resta sulla sola Rotta A). Per l'uso offline a bordo del selettore serve un secondo passo (pre-cache dei 3 file nel service worker). Restano aperti C1-C4 della §5 (offset hardcoded, sorgente dati, peso, versioning cache).
