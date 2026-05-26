# EBM Strategy Converter – Desktop Edition

**Hochschule München (HM) – Studienarbeit im Fachbereich Additive Manufacturing**

Werkzeug zur Neuanordnung von Elektronenstrahl-Belichtungsstrategien für den **Arcam S12 Pro-Beam Retrofit** (E-PBF). Die Software liest Baujob-ZIP-Archive ein, identifiziert Infill-Schichten, sortiert deren Schmelzpunkte nach einer frei konfigurierbaren Zwei-Stufen-Strategie neu und exportiert ein druckfertiges ZIP – ohne dabei eine einzige Koordinate zu verändern.

---

## 🚀 Schnellstart

### Option A – Standalone-EXE (kein Python erforderlich)

Lade die aktuelle `EBM-Strategy.exe` aus dem `dist/`-Ordner herunter und starte sie per Doppelklick.

> **Windows-Sicherheitswarnung:** Beim ersten Start fragt Windows möglicherweise nach Bestätigung → „Weitere Informationen" → „Trotzdem ausführen".

---

### Option B – Aus dem Quellcode starten

#### Schritt 1 – Python installieren (einmalig)

1. Gehe auf **https://www.python.org/downloads/** und lade die neueste Python-Version herunter.
2. **Wichtig:** Setze im Installer das Häkchen bei **„Add Python to PATH"**.

#### Schritt 2 – App starten

**Doppelklick auf `Start Desktop.bat`** im Projektordner.

Das Skript erledigt beim ersten Start automatisch:
1. Erstellt eine isolierte Python-Umgebung (`.venv`)
2. Lädt alle benötigten Bibliotheken herunter
3. Startet die Desktop-App

Oder manuell:
```bash
pip install -r requirements.txt
python desktop_app.py
```

---

## Verwendung

### 1. ZIP laden

Lade ein Baujob-ZIP-Archiv, das einen `Figure Files/`-Ordner mit `.B99`-Dateien enthält (wie von der Arcam-Software exportiert). Die App erkennt und klassifiziert alle Infill-, Kontur- und Stützstruktur-Dateien automatisch.

### 2. Strategie konfigurieren

Die Strategie besteht aus zwei unabhängigen Stufen:

**Stufe 1 – Segmentierung (Makro)**

| Option | Beschreibung |
|---|---|
| Keine Segmentierung | Alle Punkte als ein Block |
| Schachbrett (Island) | Quadratische Segmente, Phase A → Phase B |
| Streifen (Stripe) | Parallele Bänder |
| Hexagonal | Versetztes Waben-Gitter |
| Spiralzonen | Konzentrische Ringe um den Schwerpunkt |

**Stufe 2 – Mikro-Strategie (innerhalb der Segmente)**

| Strategie | Beschreibung |
|---|---|
| Raster (Zick-Zack) | Zeilenweise Sortierung, jede zweite Zeile umgekehrt |
| Spot Consecutive | Identisch zu Raster |
| Spot Ordered | Raster + Multipass (Spot-Skip) |
| Ghost Beam | Raster + Interleave: Primärpunkt → Geistpunkt |
| Hilbert-Kurve | Hilbert-Index auf 2ⁿ × 2ⁿ Grid |
| Spiral | Ringweise nach Abstand, dann Winkel |
| Peano-Kurve | Boustrophedon auf 3ⁿ Grid |
| Greedy / Dispersion | KDTree-basierte Nachbarschaftsstrategien |
| Verschachtelte Streifen | Modulare Neuordnung erkannter Streifen |

**Gemeinsame Parameter:** Segmentgröße, Overlap, Rotationswinkel pro Schicht, Ghost-Lag, Spot-Skip, u. a.

### 3. Vorschau prüfen

3D-Vorschau (VisPy) zeigt Punkte und Scan-Pfad für die gewählte Infill-Schicht. Die Simulation animiert die Reihenfolge schrittweise.

### 4. ZIP exportieren

„Strategie anwenden & ZIP erstellen" verarbeitet alle Infill-Schichten und erstellt ein druckfertiges ZIP im konfigurierten Ausgabeordner.

---

## Datei-Klassifikation (Arcam-Namenskonvention)

| Vorletzte Ziffer vor `.B99` | Typ | Behandlung |
|---|---|---|
| Gerade (0, 2, 4, 6, 8) | Infill | Punkte werden neu sortiert |
| 9 | Infill (ab Cutoff-Schicht) | Punkte werden neu sortiert |
| Ungerade (1, 3, 5, 7) | Kontur | Unverändert durchgereicht |
| Alle Schichten vor erster gerader Ziffer | Stützstruktur | Unverändert durchgereicht |

---

## B99-Format

- Koordinatensystem: Plattform 120 × 120 mm, Ursprung in der Mitte
- Normierung: `ABS`-Werte in [-1, +1], wobei `x_mm = ABS_wert × 60`
- Ausgabe: 17 signifikante Stellen, `\r\n`-Zeilenenden (Arcam-Anforderung)

---

## Projektstruktur

```
EBM-Strategy-Software/
├── Start Desktop.bat      # ▶ Schnellstart per Doppelklick
├── desktop_app.py         # Haupt-Anwendung (PySide6 + VisPy)
├── EBM-Strategy.spec      # PyInstaller-Konfiguration
├── requirements.txt       # Python-Abhängigkeiten
├── src/
│   ├── pipeline.py        # ZIP-Verarbeitung und Workflow
│   ├── parser.py          # B99-Datei-Parser
│   ├── exporter.py        # B99-Datei-Export
│   └── reorder.py         # Punkt-Neuanordnungslogik (alle Algorithmen)
├── docs/
│   └── scan-strategien.md # Hintergrunddokumentation
└── dist/
    └── EBM-Strategy.exe   # Fertige Windows-EXE
```

---

## Technologie-Stack

| Bibliothek | Verwendung |
|---|---|
| **PySide6** | Desktop-UI (Qt-Framework) |
| **VisPy** | 3D-Vorschau und Simulation |
| **NumPy** | Vektorisierte Punkt-Sortierung |
| **Shapely** | Konvexe Hülle für Segmentierungsalgorithmen |
| **SciPy** | KDTree für Greedy/Dispersion-Strategien |
| **PyInstaller** | EXE-Build |

---

## EXE Build (Windows)

```bash
pyinstaller EBM-Strategy.spec
```

Oder manuell:
```bash
pyinstaller --noconfirm --onefile --collect-all vispy --collect-all shapely --collect-all scipy desktop_app.py
```

Die fertige EXE liegt unter `dist/EBM-Strategy.exe`.
