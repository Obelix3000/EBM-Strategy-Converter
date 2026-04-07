# EBM Strategy Converter & Parametric Toolpath Generator

**Hochschule München (HM) – Studienarbeit im Fachbereich Additive Manufacturing**

Dieses Softwareprojekt ermöglicht die Erforschung und Manipulation von Laser- bzw. Elektronenstrahl-Belichtungsstrategien für den additiven **Arcam S12 Pro-Beam Retrofit 3D-Metalldrucker** (E-PBF = Electron Beam Powder Bed Fusion). 

Anstatt mühsam manuelle Maschinencodes zu schreiben oder herstellergebundene (proprietäre) Slicer zu verwenden, bietet dieses Programm eine moderne Weboberfläche, in der sich Schmelz-Trajektorien visuell erstellen, analysieren und kombinieren lassen. Die Software generiert dabei rein koordinatenbasierte `.B99`-Daten, welche aus einer simplen Liste von abzufahrenden Wegpunkten (`ABS X Y`) bestehen.

---

## 🚀 Was macht das Programm?

Die App operiert in zwei wählbaren Haupt-Modi:

1. **Parametric Toolpath Generator**  
   Mit diesem Modus kannst du rein künstlich einfache 2.5D Rechteck-Volumina (Probekörper) erzeugen, ohne eine fremde .STL-Datei hochladen zu müssen. Du gibst einfach Länge, Breite, Höhe und die gewünschte Schichtdicke ein, und der Generator baut das Bauteil virtuell Schicht für Schicht auf.
   
2. **.B99 Converter (Reverse-Engineering)**  
   Besitzt du bereits eine alte `.B99` Datei der Arcam-Maschine, kannst du sie hier hochladen. Die Software liest die alten Schmelzlinien ein, hüllt die äußersten Punkte wie ein Gummiband ein (Convex Hull Methode) und ermittelt so die exakte Bauteilform. Anschließend wird die alte Strategie gelöscht und mit deinen neuen Werten völlig überschrieben!

---

## ⚙️ Wie wird konfiguriert? (UI Parameter)

In der linken Seitenleiste lassen sich die physikalischen Parameter des Elektronenstrahls exakt einstellen. Da die `.B99`-Maschinendatei selbst jedoch keinerlei Zeit-, Geschwindigkeits- oder Leistungswerte abspeichert, werden im UI ausschließlich **räumliche Geometriewerte (Abstände)** eingestellt.

*   **Punkt-Abstand (µm):** Gibt an, wie weit zwei aufeinanderfolgende Schmelzpunkte auf einer durchgehenden Linie voneinander entfernt liegen. Typischerweise 100 µm.
*   **Linien-Abstand / Hatch (µm):** Der horizontale Abstand zwischen zwei parallelen Linien (Raupen). Bei dicken Raupen wird dieser höher gewählt (z.B. 200 µm).
*   **Rotationswinkel pro Schicht (°):** Damit das Bauteil nicht in sich zusammenbricht oder Risse bekommt (mechanische Anisotropie), wird das Infill-Muster nach jeder Schicht gedreht – der Standard liegt bei $67^\circ$.
*   **Strategie-Auswahl:** Eine Auswahlliste. Du kannst (und solltest) mehrere Strategien übereinanderlegen (z.B. erst eine randglättende `Contour` und direkt darauf ein flächenfüllendes `Raster`).
*   **Secondary Beam Lag:** (Spezial-Setting für Ghost Beam). Zieht den zweiten Strahl exakt um den spezifizierten µm Abstand hinter dem ersten Strahl her.
*   **Verpass-Abstand (Skip Offset):** (Spezial-Setting für Spot Ordered). Um wie viele Punkte der Strahl absichtlich weiter springen soll, bevor er den Zwischenraum ausfüllt.

---

## 🧬 Erklärung der 5 Scan-Strategien

Die folgenden Scan-Modi bestimmen, in welcher Aufteilung der Elektronenstrahl die berechneten Schichten (Layer) des Bauteiles abfährt. Jede Strategie hat andere Vor- und Nachteile in Bezug auf Hitze-Stau und Erstarrungszeitpunkt:

1. **Contour (Kontur-Modus):** 
   Fährt exakt die äußere Linie (den Rahmen) des Polygons ab. Das Prinzip ist ähnlich wie das Nachzeichnen eines Bildes mit einem Filzstift am Rand, bevor man das Innere ausmalt. Sorgt für glatte äußere Flanken am Bauteil.

2. **Raster (Schlangenlinien-Modus):** 
   Das Standard-Füllmuster (Infill). Der Strahl pflügt in langen, parallelen Linien durch die Fläche und wendet am Ende, um in die Gegenrichtung weiterzulaufen. Das bringt schnell Material ein, aber die langen Linien können extrem viel Hitze lokal anstauen.

3. **Spot Consecutive (Punktuelle Perforation):** 
   Der Infill wird *nicht* als durchgehende, langgezogene Linie gedruckt. Stattdessen schießt der Strahl eine dichte Perlenkette aus einzelnen Punkten in das Material. Da der Strahl zwischen jedem Punkt winzige Bruchteile von Millisekunden ausgetastet wird (Jump), sinkt die Gefahr großflächiger Materialüberhitzung massiv ab.

4. **Spot Ordered (Geteilter Punkt-Aufbau):** 
   Eine hochentwickelte Strategie gegen schädliche punktuelle Hitzestaus (Hotspots). Der Strahl schießt einen Punkt, **überspringt absichtlich N Punkte** (z.B. 2) und schießt wieder. Wenn die Reihe fertig ist, springt der Strahl nach vorne zurück und beginnt die "freigelassenen Lücken" zu füllen. Der thermische Gradient wird dadurch großflächig aufgebrochen und Erstarrungsraten ($R$) reguliert sich harmonisch.

5. **Ghost Beam (Strahlteilungs-Simulation):**
   EBM-Anlagen können Koordinaten derart rasend schnell anvisieren, dass für das menschliche Auge (und das geschmolzene Titanpulver) der Eindruck entsteht, als ob **zwei gebündelte Strahlen gleichzeitig** über das Glas gleiten. Diese Strategie sortiert die Koordinaten so um, dass der Strahl permament zwischen dem vorderen Primärpunkt und einem kurz dahinter liegenden Geisterpunkt ("Secondary Beam") hin- und herzittert. Dies zieht einen beruhigenden Hitzeschweif hinter der Schmelzfront her, der das Metall geschmeidiger erstarren lässt.

---

## 🖥️ Technologie-Stack: Warum nutzen wir das?

Dieses Tool wurde vollständig in Python entwickelt. Die Bibliotheken wurden dabei nach sehr strikten Performance-Metriken (tausende Mikropunkte in hunderten Layern) ausgewählt:

*   **GUI mit `Streamlit`:**  
    Streamlit ist ein Framework für Daten-Apps. Anstatt Wochen in HTML/CSS und Frontend-Server-Verbindungen zu stecken, liefert Streamlit einen Server, der bei Schieberegler-Änderungen sofort den Python-Prozess neu startet. Das ist perfekt für Ingenieure und Wissenschaftler, um extrem schnell Parameter in Echtzeit zu studieren.
*   **Mathematik mit `NumPy`:**  
    Ein Layer im 3D-Druck kann aus 100.000 einzelnen Koordinatenpunkten bestehen. Würde man diese einzeln in regulären Python-For-Schleifen ausrechnen, würde der PC Minuten pro Schicht benötigen. `NumPy` lagert all diese Vektormathematik in maschinen-nahen C-Code aus, was den Algorithmus tausendfach beschleunigt.
*   **Geometrie mit `Shapely`:**  
    Echte Schmelztrajektorien müssen die Bauteilränder kennen. `Shapely` ist der Industrie-Standard, um festzustellen: *"Schneidet diese Linie den Rand?"* oder *"Passe das Füllmuster exakt in dieses Rechteck ein und schneide es ab"*.
*   **Visualisierung mit `Plotly`:**  
    Die Darstellung im UI basiert auf Plotly. Normale Charting-Libraries wie `Matplotlib` rendern statische Bilder. Plotly hingegen rendert interaktives Web-GL und SVG. Ein Experte kann in das Modell hineinzoomen, hovern (um Punkt-Indizes auszulesen) und durch das Schmelzbad streifen. Kombiniert mit dem "Lazy-Loading"-Slider (nur eine Schicht wird je berechnet) schützt dies den Arbeitsspeicher des Nutzers vor Abstürzen.
