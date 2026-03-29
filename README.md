# EBM Strategy Converter & Parametric Toolpath Generator

**Hochschule München (HM) – Studienarbeit im Fachbereich Additive Manufacturing**

Dieses Projekt wurde im Rahmen einer **Studienarbeit** an der **Hochschule München** entwickelt. Das Hauptziel der bereitgestellten Software ist die wissenschaftliche Untersuchung, Anpassung und Optimierung von thermischen Belichtungsstrategien (Scan-Strategien) für den **Arcam A2X** Elektronenstrahlschmelz-Baudrucker (E-PBF: Electron Beam Powder Bed Fusion).

Die Software ist als interaktives Python `Streamlit`-Web-Interface konzipiert und bietet zwei primäre Lösungsansätze:

1. **Parametric Toolpath Generator**  
   Anstatt sich auf klassisches Slicing von 3D-Geometrien (z.B. STL-Dateien) zu stützen, nutzt der Generator eine parametrische Engine (basierend auf `Shapely`), um einfache Probekörper direkt als Serie von 2.5D-Querschnitten zu berechnen und hochpräzise zu belichten (z.B. für Parameter-Studien).

2. **.B99 Strategy Converter (Parser & Exporter)**  
   Ermöglicht das Einlesen bestehender Arcam `.B99` Dateien. Das Tool liest die physikalischen Bahnen ein und nutzt komplexe geometrische Hüllkurven-Berechnungen (Convex Hull), um die ursprüngliche Schichtkontur zu rekonstruieren. Diese Konturen können dann mit völlig neuartigen thermischen Belichtungsstrategien (Sub-Passes) gefüllt und abermals als Maschinen-Code exportiert werden.

---

## Funktionsumfang der Strategien

Das System verfügt über eine Pipeline, welche das *Composite Design Pattern* implementiert. Das bedeutet, dass pro Schicht auch mehrere der folgenden Strategien direkt übereinander gelegt werden können (Kombinationsstrategien).

- **Raster Infill:** Zeilenweiser Aufbau mit einer definierbaren Rotation (z.B. $67^\circ$) pro Schicht zum Ausgleichen von mechanischen Anisotropien.
- **Contour Mode:** Mathematisches Abfahren der Außenkanten (zur deutlichen Verbesserung der Oberflächenqualität).
- **Spot Consecutive:** Wie das klassische Raster-Hatching, jedoch als forcierte physikalische Jump-Matrix konzipiert, welche Spot-Melting abbildet, bei dem der Strahl permanent ein/ausschaltet.
- **Spot Ordered:** Im Gegensatz zur sequentiellen Abarbeitung überspringt diese Strategie bewusst Positionen (+Offset) innerhalb der Schicht, um die Punkte im nächsten Unter-Durchlauf erst zu füllen. **Forschungs-Kontext**: Dient aktiv der Optimierung lokaler Temperaturgradienten und Erstarrungsraten ($G$ und $R$).
- **Ghost Beam Tracking:** Simuliert die Hochfrequenz-Strahlteilung von zwei zeitgleich agierenden Belichtungsquellen (einem Primary-Beam und einem sekundären Ghost-Beam). Über die konfigurierbare Strahldauer ($Spot \ On \ Time$) und die zeitliche Verzögerung ($Time \ Delay$) errechnet der Algorithmus den räumlichen Offset (Lagging) des zweiten Beams.

---

## Installation & Ausführung

Stellen Sie sicher, dass Python (3.10+) installiert ist.

1. Installieren der benötigten wissenschaftlichen Bibliotheken:
   ```bash
   pip install -r requirements.txt
   ```
2. Starten der Streamlit-Anwendung (öffnet sich automatisch auf `localhost` im Webbrowser):
   ```bash
   python -m streamlit run app.py
   ```

## Technologie-Stack

* **Frontend / UI Layer**: `Streamlit` für schnelle, web-basierte Prototyping-Interfaces.
* **Geometrie Layer**: `Shapely` für Hüllkurven-Interpolation, Polygon-Mathe und Schnitte.
* **Math Layer**: C-basierte `NumPy` Listen-Operationen zur Gewährleistung von Performance in großen Punkte-Wolken (bis zu 400 Schichten gleichzeitig).
* **Render / View Layer**: `Plotly` für das Layer-by-Layer "Lazy Rendering", weshalb die Anwendung nicht bei massiven Punktewolken an RAM-Limits stößt.

## Danksagung / Kontext
Das Tool dient im akademischen Raum als Werkzeug zur Visualisierung und Manipulation der zugrundeliegenden `.B99` Schmelzlogik ohne proprietäre Slicer-Nutzung. Erstellt für die Module des Studiengangs rund um **Additive Manufacturing** an der HM.
