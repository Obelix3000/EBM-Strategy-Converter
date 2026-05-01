# EBM Strategy Converter

**Hochschule München (HM) – Studienarbeit im Fachbereich Additive Manufacturing**

Werkzeug zur Neuanordnung von Elektronenstrahl-Belichtungsstrategien für den **Arcam S12 Pro-Beam Retrofit** (E-PBF). Die Software liest Baujob-ZIP-Archive ein, identifiziert Infill-Schichten, sortiert deren Schmelzpunkte nach einer frei konfigurierbaren Zwei-Stufen-Strategie neu und exportiert ein druckfertiges ZIP – ohne dabei eine einzige Koordinate zu verändern.

---

## 🚀 Installation & Start

### Schritt 1 – Python installieren (einmalig)

1. Gehe auf **https://www.python.org/downloads/** und lade die neueste Python-Version herunter.
2. Starte den Installer.
3. **Wichtig:** Setze ganz unten im Installer-Fenster das Häkchen bei **„Add Python to PATH"**, bevor du auf „Install Now" klickst.

   ![Python PATH Häkchen](https://docs.python.org/3/_images/win_installer.png)

4. Installation abschließen.

> **Einmal reicht:** Wenn Python bereits installiert ist, diesen Schritt überspringen.

---

### Schritt 2 – App starten (jetzt und in Zukunft)

**Doppelklick auf `Start App.bat`** im Projektordner.

Das Skript erledigt beim **ersten Start** automatisch alles Weitere:
1. Erstellt eine isolierte Python-Umgebung (`.venv`) im Projektordner
2. Lädt alle benötigten Bibliotheken herunter und installiert sie
3. Prüft, ob eine neuere Programmversion verfügbar ist (erfordert Internetzugang)
4. Startet die App und öffnet sie im Browser unter `http://localhost:8501`

Der erste Start dauert ein paar Minuten (Bibliotheken werden heruntergeladen). Alle weiteren Starts sind deutlich schneller.

> **Das schwarze Terminal-Fenster** muss geöffnet bleiben, solange die App läuft – es kann aber minimiert werden. Beim Schließen des Fensters wird die App beendet.

> **Windows-Sicherheitswarnung:** Beim ersten Start fragt Windows möglicherweise nach Bestätigung → „Weitere Informationen" → „Trotzdem ausführen" klicken.

---

### Desktop-App starten (neu)

Die Desktop-Version nutzt PySide6 und eine 3D-Vorschau. Sie startet lokal ohne Browser.

**Option A (empfohlen):** Doppelklick auf `Start Desktop.bat`

**Option B (manuell):**

```bash
python desktop_app.py
```

> Hinweis: Beim ersten Start werden die zusätzlichen Abhängigkeiten (PySide6, VisPy, PyOpenGL) installiert.

---

### Problemlösung

| Problem | Lösung |
|---|---|
| „Python nicht gefunden" | Schritt 1 wiederholen und darauf achten, dass **„Add Python to PATH"** aktiviert ist |
| Browser öffnet sich nicht | Manuell `http://localhost:8501` in die Adressleiste eingeben |
| App startet nicht | Terminal-Fenster nach Fehlermeldungen durchsuchen und ggf. Internetzugang prüfen |

---

## Verwendung

### 1. ZIP-Archiv hochladen

Lade ein Baujob-ZIP-Archiv hoch, das einen `Figure Files/`-Ordner mit `.B99`-Dateien enthält (wie von der Arcam-Software exportiert).

Die App analysiert die Dateien automatisch und zeigt:
- Gesamtanzahl der B99-Dateien
- Anzahl erkannter Infill-Schichten (ab der ersten Schicht mit gerader vorletzter Ziffer im Dateinamen)
- Anzahl Kontur- und Stützstruktur-Dateien (werden unverändert durchgereicht)

### 2. Strategie konfigurieren (linke Seitenleiste)

Die Strategie besteht aus zwei unabhängigen Stufen:

**Stufe 1 – Segmentierung (Makro)**
Teilt die Punktwolke einer Schicht in Bereiche auf, bevor die Mikro-Strategie angewendet wird:

| Option | Beschreibung |
|---|---|
| Keine Segmentierung | Alle Punkte werden als ein Block behandelt |
| Schachbrett (Island) | Quadratische Segmente, alternierend Phase A → Phase B |
| Streifen (Stripe) | Parallele Bänder, senkrecht zur Hatch-Richtung |
| Hexagonal | Versetztes Waben-Gitter, alternierend Phase A → Phase B |
| Spiralzonen | Konzentrische Ringe um den Schwerpunkt (außen → innen oder umgekehrt) |

Für alle Segmentierungstypen (außer „Keine") lassen sich **Segmentgröße (mm)** und **Segment-Overlap (µm)** einstellen.

**Stufe 2 – Mikro-Strategie (innerhalb der Segmente)**

| Strategie | Beschreibung |
|---|---|
| Raster (Zick-Zack) | Punkte werden zeilenweise in Hatch-Abstand sortiert, jede zweite Zeile umgekehrt |
| Spot Consecutive | Identisch zu Raster (gleiche Sortierung, diskrete Einzelpunkte) |
| Spot Ordered | Raster + Multipass: erst jeden (Skip+1)-ten Punkt, dann die Lücken |
| Ghost Beam | Raster + Interleave: Primärpunkt → nachlaufender Geistpunkt (P1→S1→P2→S2…) |
| Hilbert-Kurve | Punkte nach Hilbert-Index auf einem 2ⁿ × 2ⁿ Grid sortiert |
| Spiral | Ringweise nach Abstand zum Schwerpunkt, innerhalb des Rings nach Winkel |
| Peano-Kurve | Schlangenlinien-Sortierung auf feinem quantisierten Grid (Boustrophedon) |

Gemeinsame Parameter:
- **Linien-Abstand / Hatch (µm):** Abstand zwischen Hatch-Zeilen (für Raster-Sortierung)
- **Rotationswinkel pro Schicht (°):** Das Sortiersystem wird pro Schicht gedreht (Standard: 67°)

> **Hinweis:** Der Punktabstand (100 µm) ist fix – er kommt aus dem Slicer und wird nicht verändert.

### 3. Vorschau prüfen

Wähle eine Infill-Datei aus dem Dropdown und betrachte die originale Punktverteilung im interaktiven Plotly-Diagramm. Optional: Wärmeakkumulation als Farbkodierung einblenden (Material und Punkthaltezeit wählbar).

Die Schema-Diagramme (aufklappbar) zeigen eine schematische Darstellung der gewählten Stufe-1- und Stufe-2-Strategie.

### 4. Strategie anwenden und exportieren

Klicke **„Strategie anwenden & neues ZIP erstellen"**. Die App:
1. Verarbeitet alle erkannten Infill-Schichten (Fortschrittsbalken)
2. Schreibt jede Infill-Datei mit neu geordneten Punkten zurück (Header unverändert)
3. Packt alle Dateien (inklusive unveränderter Kontur- und Stützstruktur-Dateien) in ein neues ZIP
4. Speichert das ZIP im konfigurierten **Ausgabe-Ordner** (Standard: `~/EBM_Output/`)
5. Bietet einen **Download-Button** für das neue ZIP

---

## Datei-Klassifikation (Arcam-Namenskonvention)

Die Software erkennt Infill-Dateien anhand der **vorletzten Ziffer** vor `.B99` im Dateinamen:

| Vorletzte Ziffer | Typ | Behandlung |
|---|---|---|
| Gerade (0, 2, 4, 6, 8) | Infill | Punkte werden neu sortiert |
| 9 | Infill (ab Cutoff-Schicht) | Punkte werden neu sortiert |
| Ungerade (1, 3, 5, 7) | Kontur | Unverändert durchgereicht |
| Alle Schichten vor der ersten geraden Ziffer | Stützstruktur | Unverändert durchgereicht |

---

## B99-Format

- Koordinatensystem: Plattform 120 × 120 mm, Ursprung in der Mitte
- Normierung: `ABS`-Werte in [-1, +1], wobei `x_mm = ABS_wert × 60`
- Befehlsformat: `ABS <x_rel> <y_rel>` pro Punkt
- Ausgabe: 17 signifikante Stellen, `\r\n`-Zeilenenden (wie im Original)
- Zwischen Segmenten: impliziter Beam-off-Jump (kein explizites Kommando nötig)

---

## Projektstruktur

```
EBM-Strategy-Software/
├── Start App.bat          # ▶ Schnellstart per Doppelklick
├── Start Desktop.bat      # ▶ Desktop-Version (PySide6)
├── app.py                 # Haupt-Streamlit-Anwendung
├── desktop_app.py         # Desktop-UI mit 3D-Vorschau
├── requirements.txt       # Python-Abhängigkeiten
├── src/
│   ├── parser.py          # B99-Datei-Parser
│   ├── exporter.py        # B99-Datei-Export
│   ├── reorder.py         # Punkt-Neuanordnungslogik
│   ├── visualization.py   # Plotly-Visualisierung
│   ├── schema_diagrams.py # Schematische SVG-Diagramme
│   └── thermal.py         # Wärmeakkumulationsmodell
└── .venv/                 # Virtuelles Python-Environment
```

---

## Technologie-Stack

| Bibliothek | Verwendung |
|---|---|
| **Streamlit** | Web-UI, Interaktion, Dateiupload |
| **NumPy** | Vektorisierte Punkt-Sortierung (tausende Punkte pro Schicht) |
| **Shapely** | Konvexe Hülle für Segmentierungsalgorithmen |
| **Plotly** | Interaktive 2D-Visualisierung mit Zoom und Hover |
| **PySide6 + VisPy** | Desktop-UI und 3D-Vorschau |

---

## EXE Build (Windows)

```bash
pyinstaller --noconfirm --onefile --name EBM-Strategy-Desktop --collect-all vispy desktop_app.py
```

Der erzeugte Build liegt danach unter `dist/EBM-Strategy-Desktop.exe`.
