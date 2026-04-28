# EBM Scan-Strategien – Übersicht

## Warum eine zweistufige Verschachtelung?

Die Punktwolke einer EBM-Schicht enthält typischerweise mehrere Tausend Punkte, die der Elektronenstrahl der Reihe nach anfahren muss. Die Reihenfolge bestimmt maßgeblich, wie sich Wärme in der Schmelzbahn ansammelt und abkühlt. Zwei orthogonale Fragen lassen sich dabei getrennt beantworten:

1. **Wo** werden Teilbereiche der Fläche zuerst bearbeitet? → *Primärstrategie (Makro-Segmentierung)*
2. **Wie** werden die Punkte innerhalb eines Teilbereichs traversiert? → *Sekundärstrategie (Mikro-Sortierung)*

Die Trennung ermöglicht es, beide Ebenen unabhängig zu kombinieren. Eine Schachbrett-Segmentierung mit Hilbert-Sortierung ist so genauso einfach konfigurierbar wie Streifen mit Dispersionsstrategie. Ohne diese Abstraktion müsste für jede Kombination ein eigener Algorithmus implementiert werden.

Ein weiterer Grund ist thermophysikalisch: Die Makro-Ebene steuert, *welche Zonen* der Strahl als nächstes betritt und damit die großräumige Wärmediffusion. Die Mikro-Ebene steuert die lokale Abkühlzeit zwischen benachbarten Schmelzpunkten innerhalb eines Segments.

---

## Stufe 1 – Primärstrategien (Makro-Segmentierung)

Die Segmentierungsfunktionen teilen die N×2-Punktwolke in eine geordnete Liste von Teilmengen auf. Jede Teilmenge (Segment) wird dann separat durch die Sekundärstrategie sortiert. **Koordinaten werden dabei nie verändert.**

---

### Keine Segmentierung

**Funktionsweise:** Die gesamte Punktwolke wird als ein einziges Segment behandelt. Die Mikrostrategie operiert direkt auf allen Punkten.

| Vorteile | Nachteile |
|---|---|
| Kein Overhead durch Segmentzuordnung | Kein Schutz vor großräumiger Wärmeakkumulation |
| Einfachste Konfiguration | Mikrostrategie trägt die alleinige Verantwortung für Wärmeverteilung |
| Deterministisch und vorhersagbar | Ungünstig bei großen Schichten |

---

### Schachbrett (`_segment_chessboard`)

**Funktionsweise:** Das Bounding-Box-Raster der Punktwolke wird in gleichgroße quadratische Zellen (`seg_size × seg_size` mm) aufgeteilt. Zellen mit geradem `(Zeile + Spalte)`-Index bilden **Phase A**, Zellen mit ungeradem Index **Phase B**. Erst werden alle A-Zellen in der gewählten Reihenfolge abgearbeitet, anschließend alle B-Zellen. Die Reihenfolge innerhalb jeder Phase kann konfiguriert werden: sequentiell (Zeilen-Spalten), Spirale innen→außen, Spirale außen→innen oder zufällig.

Die Zweiphasen-Struktur bewirkt, dass direkt benachbarte Zellen immer unterschiedlichen Phasen angehören – der Strahl springt also nach jeder Zelle mindestens eine Zellbreite weit weg, bevor er in die benachbarte Zelle zurückkehrt. Das lässt bereits bearbeitete Bereiche abkühlen.

| Vorteile | Nachteile |
|---|---|
| Gute räumliche Verteilung durch Zweiphasen-Schema | Lange Sprünge zwischen den Phasen (Totzeit) |
| Kompatibel mit allen Mikro-Strategien | Zellgrenzen sind achsenparallel – bei gedrehten Hatch-Linien kann die Aufteilung suboptimal sein |
| Sehr etablierte Methode im EBM-Bereich (Island Scanning) | Zellgröße muss manuell auf Schichtgeometrie abgestimmt werden |

---

### Streifen (`_segment_stripes`)

**Funktionsweise:** Die Punktwolke wird senkrecht zum aktuellen Hatch-Vektor in parallele Bänder der Breite `seg_size` mm projiziert. Die Projektionsachse rotiert mit dem `rotation_angle_deg`-Parameter (standardmäßig 67° pro Schicht), sodass die Streifen stets orthogonal zu den Scan-Linien verlaufen. Die Streifen werden sequentiell oder in zufälliger Reihenfolge abgearbeitet.

| Vorteile | Nachteile |
|---|---|
| Passt sich automatisch an die Hatch-Rotation an | Kein räumliches Abstandshalten wie beim Schachbrett |
| Einfache Geometrie, geringer Berechnungsaufwand | Benachbarte Streifen werden nacheinander bearbeitet → lokal erhöhte Wärme möglich |
| Gut kombinierbar mit Raster- und Interlaced-Mikrosortierung | Zufälliger Modus bricht die thermische Lokalität, ist aber weniger deterministisch |

---

### Hexagonal (`_segment_hexagonal`)

**Funktionsweise:** Analog zum Schachbrett, jedoch auf einem versetzten Wabengitter (Hexagonalmuster). Jede zweite Zeile ist um `h/2` (halber horizontaler Zellabstand) verschoben. Die Zellen werden ebenfalls in Phase A und Phase B aufgeteilt und in dieser Reihenfolge verarbeitet.

Das hexagonale Gitter hat bei gleicher Zellgröße eine gleichmäßigere Nachbarschaftsstruktur als ein quadratisches – jede Zelle hat idealerweise sechs statt vier Nachbarn, was die räumliche Streuung verbessert.

| Vorteile | Nachteile |
|---|---|
| Gleichmäßigere Raumabdeckung als quadratisches Gitter | Komplexere Indexberechnung, Randbereiche können unvollständig sein |
| Näher an der natürlichen Wärmediffusionsgeometrie (isotrop) | Randpunkte können falschen Zellen zugeordnet werden bei nicht-rechteckigen Schichten |
| Gute Kombination mit Raster- oder Hilbert-Mikrosortierung | Weniger verbreitet, schwerer zu visualisieren und zu erklären |

---

### Spiralzonen / Konzentrisch (`_segment_spiral_zones`)

**Funktionsweise:** Jedem Punkt wird anhand seines euklidischen Abstands vom Polygon-Schwerpunkt ein Ringindex zugewiesen: `ring_idx = floor(dist / seg_size)`. Die Ringe werden entweder von innen nach außen oder von außen nach innen abgearbeitet. Die Richtung ist über `seg_order` konfigurierbar.

| Vorteile | Nachteile |
|---|---|
| Natürliche Abbildung auf konzentrischen Wärmefluss | Ringe sind keine echten geometrischen Kreise, sondern Quantisierungsartefakte |
| Außen→Innen ermöglicht ein "Einsperren" der Wärme im Kern | Bei stark nicht-kreisförmigen Geometrien ungleichmäßige Ringbreiten |
| Innen→Außen schützt den Kern vor Überhitzung | Kein Abstandshalten zwischen benachbarten Ringen |

---

## Stufe 2 – Sekundärstrategien (Mikro-Sortierung)

Jede Sekundärstrategie erhält ein `np.ndarray (N, 2)` – die Punkte eines einzelnen Segments – und gibt dieselben Punkte in neuer Reihenfolge zurück. Ghost Beam ist eine Ausnahme: er verdoppelt die Punktanzahl und wird nach der Zusammenführung aller Segmente angewandt.

---

### Raster (Zick-Zack) / Spot Consecutive

**Funktionsweise:** Die Punkte werden anhand ihrer Y-Koordinate auf ein 50-µm-Raster gerundet, sodass natürliche Scan-Linien des Slicers erkannt werden. Innerhalb jeder Zeile wird nach X sortiert; jede zweite Zeile wird umgekehrt (Boustrophedon/Zick-Zack). `Spot Consecutive` ist intern identisch mit `Raster` – beide rufen `sort_raster` auf.

Die Rotation und der Hatch-Spacing-Parameter werden bewusst ignoriert: Der Slicer legt die Linienstruktur und -ausrichtung bereits fest.

| Vorteile | Nachteile |
|---|---|
| Sehr einfach, deterministisch, schnell | Benachbarte Punkte werden nacheinander bearbeitet → lokal hohe Wärmedichte |
| Respektiert die native Slicer-Linienstruktur | Kein Mechanismus zur Wärmeverteilung innerhalb des Segments |
| Kurze Sprünge, hohe Effizienz (wenig Totzeit) | Schlechte Bauteilqualität bei großen Segmenten ohne übergeordnete Makrostrategie |

---

### Spot Ordered (Multipass)

**Funktionsweise:** Aufbauend auf `sort_raster` wird der rastergeordnete Pfad in `(skip + 1)` Pässe aufgeteilt. Pass 1 enthält jeden `(skip+1)`-ten Punkt beginnend bei Index 0, Pass 2 beginnt bei Index 1 usw. Die Pässe werden aneinandergehängt. Mit `skip = 2` ergibt sich: Pass 1 → Punkte 0, 3, 6, …; Pass 2 → 1, 4, 7, …; Pass 3 → 2, 5, 8, …

Zwischen zwei aufeinanderfolgenden Punkten liegt immer der Abstand von `skip + 1` Originalpunkten – der Strahl springt also über mehrere Punkte hinweg und kehrt erst in einem späteren Pass zurück. Das gibt jedem besuchten Punkt Zeit zum Abkühlen.

| Vorteile | Nachteile |
|---|---|
| Reduziert lokale Wärmeakkumulation deutlich | Lange Sprünge = erhöhter Heatup beim Strahltransport |
| Einfach parametrierbar über `skip` | Reihenfolge wirkt willkürlich auf Makroebene |
| Kompatibel mit Segmentierung | Deterministisch, aber nur bedingt optimal |

---

### Ghost Beam

**Funktionsweise:** Nach der vollständigen Raster-Vorsortierung aller Segmente und deren Zusammenführung in einen einzigen Pfad wird für jeden primären Punkt `P_i` ein nachlaufender Geistpunkt `S_i = P_{i - lag_count}` eingefügt. Das Ergebnis ist ein interleaved Pfad: `P_0, S_0, P_1, S_1, …`. Der Geistpunkt entspricht einem bereits bestrahlten Punkt, der mit reduzierter Energie nochmals angefahren wird – er wirkt als thermische Nachbehandlung (Tempern).

Der Lag-Count ergibt sich aus `ghost_lag_mm / point_spacing_mm`. Bei sehr kleinen Segmenten wird der Lag-Count auf `max(1, N // 4)` begrenzt.

**Besonderheit:** Ghost Beam wird *nach* der Segmentzusammenführung auf den Gesamtpfad angewandt, da per-Segment-Anwendung bei kleinen Segmenten entartet (zu wenige Punkte für einen sinnvollen Lag).

| Vorteile | Nachteile |
|---|---|
| Simuliert thermisches Tempern durch Doppelbelichtung | Verdoppelt die Punktanzahl → längere Bearbeitungszeit |
| Kontrollierte thermische Nachbehandlung ohne Koordinatenänderung | Erhöhter Speicherbedarf im Ausgabepfad |
| Kombination mit Makrostrategie möglich | Nur sinnvoll, wenn die Maschinensteuerung den Geist-Energiemodus unterstützt |

---

### Hilbert-Kurve

**Funktionsweise:** Jedem Punkt wird ein Index auf einer Hilbert-Kurve der Ordnung `order` (Standard: 4) zugewiesen. Das Bounding-Box-Gebiet wird auf ein `2^order × 2^order`-Gitter projiziert. Die Hilbert-Kurve garantiert räumliche Lokalität: nahe beieinanderliegende Punkte im Gitter haben ähnliche Kurvenindizes und werden daher nacheinander bearbeitet.

| Vorteile | Nachteile |
|---|---|
| Sehr gute räumliche Lokalität (cache-freundlich) | Keine Wärmedispersion: nahegelegene Punkte folgen aufeinander |
| Deterministisch und reproduzierbar | Kurvenordnung bestimmt Granularität – bei falscher Wahl clustern Punkte |
| Gleichmäßige Raumabdeckung ohne Lücken | Effizienz O(N log N) durch Sortierung, aber Index-Berechnung ist O(N·order) |

---

### Spiral

**Funktionsweise:** Jedem Punkt werden Polarkoordinaten `(dist, angle)` bezüglich des Segment-Schwerpunkts zugewiesen. Punkte werden auf `hatch_spacing`-breite Ringe quantisiert und dann nach `(±ring_idx, angle)` sortiert. Einwärts-Spirale: äußere Ringe zuerst, einwärts nach innen.

| Vorteile | Nachteile |
|---|---|
| Natürliche kreisförmige Traversierung | Abhängig von `hatch_spacing` – falscher Wert erzeugt ungleichmäßige Ringe |
| Keine 180°-Kehrtwendungen im Mittelpunkt | Stark nicht-kreisförmige Segmente führen zu ungleichmäßigen Ringen |
| Kombination mit konzentrischer Makrostrategie naheliegend | Kein Mechanismus zur Wärmedispersion |

---

### Peano-Kurve (Boustrophedon-Näherung)

**Funktionsweise:** Das Bounding-Box-Gebiet wird auf ein `3^order × 3^order`-Gitter projiziert (max. 243×243). Punkte werden in Zeilen-Boustrophedon-Reihenfolge auf dem Gitter sortiert: gerade Zeilen von links nach rechts, ungerade von rechts nach links. Dies entspricht einer Schlangenlinie auf feinem Gitter – eine Annäherung an die echte Peano-Kurve ohne den vollen rekursiven Aufwand.

| Vorteile | Nachteile |
|---|---|
| Füllt die Fläche gleichmäßig und lückenlos | Nur eine Näherung der echten Peano-Kurve |
| Einfach zu implementieren und zu verstehen | Keine bessere räumliche Lokalität als einfaches Raster |
| Deterministisch | Benachbarte Zeilen werden immer nacheinander bearbeitet |

---

### Greedy (Nächster Nachbar)

**Funktionsweise:** Startet bei Punkt 0 und wählt in jedem Schritt den nächsten unbesuchten Punkt nach einer Score-Funktion: `score = dist_zum_aktuellen - w2 × Σ(dist_zu_letzten_N_Punkten)`. Der Repulsionsterm `w2 × Σ(...)` bestraft Kandidaten, die in der Nähe kürzlich besuchter Punkte liegen. KDTree (scipy) wird für effiziente Kandidatensuche verwendet.

| Vorteile | Nachteile |
|---|---|
| Kurze Sprünge → hohe Strahleffizienz | O(N²) im schlechtesten Fall, nur durch KDTree auf O(N log N) approximiert |
| Rückstoß-Gedächtnis verhindert lokale Wärmekonzentration | Nicht optimal global – greedy-Entscheidungen können in lokalen Minima enden |
| Konfigurierbar über `memory` und `w2` | Startpunkt (Index 0) beeinflusst das Ergebnis |

---

### Dispersions-Maximum

**Funktionsweise:** Inversion des Greedy-Ansatzes: Statt dem nächsten Punkt wird der *weiteste* bevorzugt. Score: `score = dist_zum_aktuellen + w2 × Σ(dist_zu_letzten_N_Punkten)`. Kandidatenpool sind die K weitesten unbesuchten Punkte. Der Strahl springt bewusst weit, um Wärme über die Fläche zu verteilen.

| Vorteile | Nachteile |
|---|---|
| Maximale räumliche Wärmeverteilung | Lange Sprünge → hohe Totzeit, ineffizient für Strahlleistung |
| Direkt anti-korreliert zu lokaler Wärmeakkumulation | Ergebnis stark abhängig von `memory` und `w2` |
| Gut geeignet für Materialien mit schlechter Wärmeleitfähigkeit | Nicht reproduzierbar ohne festen Startpunkt |

---

### Gitter-Dispersion (deterministisch / stochastisch)

**Funktionsweise:** Punkte werden Gitterzellen der Größe `grid_cell_size` zugewiesen. Zellen werden in Boustrophedon-Reihenfolge abgearbeitet. Innerhalb jeder Zelle wird der Punkt gewählt, der den höchsten gewichteten Abstand zur Verlaufshistorie hat (age_decay = 0,9 über die letzten 20 Punkte).

Im **deterministischen** Modus werden Kandidaten sequentiell ausgewählt. Im **stochastischen** Modus wird der Kandidatenpool zufällig abgetastet (`candidate_limit = 64`).

| Vorteile | Nachteile |
|---|---|
| Kombination aus räumlicher Struktur (Gitter) und Wärmedispersion | Deterministischer Modus kann suboptimal sein, wenn Zellen ungleichmäßig besetzt sind |
| Deterministischer Modus reproduzierbar | Zellgröße muss mit Geometrie abgestimmt werden |
| Stochastischer Modus erzeugt Variation ohne Chaos | Stochastischer Modus: nicht reproduzierbar |

---

### Dichte-adaptiv (stochastisch)

**Funktionsweise:** Bei jedem Schritt wird eine Zelle stochastisch gewichtet nach zwei Kriterien ausgewählt: (1) lokale Nachbarschaftsdichte (wie viele unverarbeitete Punkte befinden sich in benachbarten Zellen?) und (2) Abstand der Zellmitte vom letzten bearbeiteten Punkt. Das Gewicht steigt mit dem Abstand und sinkt mit der Dichte (`weight ~ spacing² / sqrt(density)`). Innerhalb der gewählten Zelle wird der Punkt nach gewichtetem Abstand zur Verlaufshistorie ausgewählt. Bewusst nicht deterministisch (`rng = np.random.default_rng(None)`).

| Vorteile | Nachteile |
|---|---|
| Adaptiert sich an die lokale Geometrie der Schicht | Nicht reproduzierbar – jeder Lauf erzeugt eine andere Reihenfolge |
| Verhindert sowohl lokale Überhitzung als auch unnötig lange Sprünge | Schlechteste Performance aller Strategien (O(N²) naiv) |
| Komplexeste thermische Streuungsstrategie | Schwer zu debuggen und zu validieren |

---

### Verschachtelte Streifen (Interlaced Stripes)

**Funktionsweise:** Zunächst werden natürliche Scan-Streifen aus dem Input erkannt: große Rückwärtssprünge in der dominanten Achse (Schwellwert: `max(5 × medianer Vorwärtsschritt, 2 % Achsenspanne)`) markieren Streifengrenzen. Innerhalb jedes Streifens wird die Besuchsreihenfolge durch ein modulares Sprungmuster umgeordnet: Blöcke der Größe `forward + backward` werden so traversiert, dass erst jeder `forward`-te Punkt besucht wird, dann die Lücken gefüllt.

Beispiel mit `forward=3, backward=2` (Blockgröße 5):
```
Originalblock: [0, 1, 2, 3, 4]
Reihenfolge:   [0, 3, 1, 4, 2]
```

| Vorteile | Nachteile |
|---|---|
| Nutzt die native Slicer-Linienstruktur ohne Neuordnung | Erkennungsalgorithmus kann bei unregelmäßigen Inputs versagen |
| Reduziert lokale Wärmedichte durch Punkt-Überspringen | Parameter `forward` und `backward` wirken nicht intuitiv |
| Deterministisch und erklärbar | Nur sinnvoll, wenn der Input bereits Zeilenstruktur aufweist |

---

## Kombinationslogik

```
reorder_points()
├── Makro: segment_points()        → Liste von Segmenten
│   ├── Keine / Schachbrett / Streifen / Hexagonal / Spiralzonen
│   └── Jedes Segment = np.ndarray (M, 2)
│
├── Mikro: sort_within_segment()   → pro Segment (außer Ghost Beam: nur Raster-Vorsortierung)
│   ├── Raster / Spot Consecutive / Spot Ordered
│   ├── Hilbert / Spiral / Peano
│   └── Greedy / Dispersions-Max / Gitter-Dispersion / Dichte-adaptiv / Verschachtelte Streifen
│
└── Ghost Beam (falls gewählt):    → auf zusammengeführten Gesamtpfad, verdoppelt Punktanzahl
    sort_ghost_beam(combined, ...)
```

Ghost Beam ist die einzige Sekundärstrategie, die nach der Zusammenführung aller Segmente arbeitet. Alle anderen Sekundärstrategien sind vollständig lokal und segmentagnostisch.
