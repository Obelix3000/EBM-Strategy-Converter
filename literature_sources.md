# Wissenschaftliche Quellen — EBM Strategy Converter Review (v3)

## Kontext

Projekt: Entwicklung und Validierung einer optimierten Scanstrategie für eine PBF-EB/M-Anlage (Arcam S12 Pro-Beam Retrofit). Hochschule München, SS2026, Smart Manufacturing Lab, Prof. Dr.-Ing. Christian M. Seidel.

Werkstoff: CarTech® Micro-Melt® 23 Alloy. Einziger Freiheitsgrad: Reihenfolge und Position der ABS-Koordinaten in `.B99`-Dateien. Punkthaltezeit 13 µs, Strahlstrom 10,8 mA, Leistung 648 W (fix). Keine Kontur — nur Infill.

---

## [1] Lee, Y.S. et al. (2018) — PRIMÄRQUELLE

**"Role of scan strategies on thermal gradient and solidification rate in electron beam powder bed fusion"**
*Additive Manufacturing* 22 (2018) 516–527
DOI: https://doi.org/10.1016/j.addma.2018.04.038

| Verwendung | Stelle im Paper |
|---|---|
| Definition aller 4 Basis-Strategien (Raster, Spot-Consecutive, Spot-Ordered, Ghost Beam) | Fig. 2 (a–d), S. 517–518 |
| Spot-Ordered: Skip-Logik "Punkt 1, überspringe 2, Punkt 2" | Fig. 2(d) |
| Ghost Beam: Skip-Spacing = Time-Delay × Velocity → räumlich modellierbar | Abschnitt 2.1 |
| Hatch-Spacing 200 µm, Spot-Spacing 400 µm als Referenzwerte | S. 518 |
| G vs. R: Spot-Ordered senkt G, Ghost Beam senkt G und R | Fig. 11, S. 526 |
| Scan-Speed 490 mm/s, Beam-Power 240–300 W, Preheat 1273 K (IN718) | Table 1, S. 519 |
| **Hilbert, Oxen, Spiral** als weitere Scan-Muster erwähnt (Referenz [1] im Paper = Babu et al. 2015) | S. 517, Introduction |
| Materialdaten IN718 für Vergleich mit MicroMelt 23 | Table 2, S. 519 |

---

## [2] Karimi, P. et al. (2020)

**"Contour design to improve topographical and microstructural characteristics of Alloy 718 manufactured by EB-PBF"**
*Additive Manufacturing* 35 (2020) 101360

| Verwendung | Relevanz |
|---|---|
| Contour/Hatch-Interface erzeugt Porosität ohne Offset | Historisch relevant — Contour entfällt im neuen Workflow, aber Wissen bleibt für Dokumentation |
| 2 Konturen verbessern Oberfläche | Nicht mehr relevant für dieses Projekt (Doktorand macht Kontur separat) |

---

## [3] Zaeh, M.F. & Kahnert, M. (2009)

**"The effect of scanning strategies on electron beam sintering"**
*Production Engineering* 3 (2009) 217–224
DOI: https://doi.org/10.1007/s11740-009-0178-0

| Verwendung | Relevanz |
|---|---|
| Chessboard/Island-Strategie: Risse an Überlappungszonen der Felder | → Island-Overlap-Parameter essenziell |
| "Continuous scanning is necessary" — unterbrochene Strategien riskant | → Warnung bei Island-Implementierung |
| Layer-Rotation minimiert Verzug | → Bestätigt 67°-Rotation im Code |

---

## [4] Babu, S.S. et al. (2015) — Hilbert, Oxen, Spiral

**"Additive manufacturing of materials: opportunities and challenges"**
*MRS Bulletin* 40 (2015) 1154–1161

| Verwendung | Relevanz |
|---|---|
| Hilbert-Pfad → ovales Schmelzbad, gleichmäßige Erwärmung, minimale Temperaturgradienten | → Wissenschaftliche Grundlage für Hilbert-Strategie |
| Oxen-Pfad (=bidirektionales Raster) → elongiertes Schmelzbad, hoher Temperaturgradient | → Bestätigt Schwäche der Raster-Strategie |
| Spiral-Pfad → komplexe Schmelzbadform | → Grundlage für Spiral-Strategie |

---

## [5] Frey, M. et al. (2024) — Hilbert, Peano, Gosper, Spiral

**"Influence of Novel Space Filling PBF-LB Scanning Strategies on Part Distortion and Density"**
KIT Karlsruhe, SFF Symposium Proceedings (2024)

| Verwendung | Relevanz |
|---|---|
| Fraktale Strategien reduzieren Verzug bis 56% | → Starkes Argument für Hilbert/Peano |
| Hilbert: 96.70% Dichte — kurze Scanvektoren problematisch | → Warnung bei Implementierung |
| Peano: 99.35% Dichte — beste unter fraktalen Strategien | → Peano bevorzugen falls Dichte kritisch |
| Spiral: minimale Porosität, aber erhöhter Verzug | → Trade-off dokumentieren |
| Segmentierung der Pfade reduziert Verzug bei allen Strategien | → Bestätigt Island-Ansatz |

---

## [6] Sebastian, R. et al. (2020) — Hilbert Unit Cell

**"'Unit cell' type scan strategies for powder bed fusion: The Hilbert fractal"**
*Additive Manufacturing* 36 (2020) 101588

| Verwendung | Relevanz |
|---|---|
| Unit-Cell-Methodik für Hilbert: Definiere Basiszelle, skaliere hoch | → Implementierungsansatz für Hilbert-Strategie |
| Koaleszenz der Schmelzbäder bei kurzen Vektoren demonstriert | → Mindest-Vektorlänge beachten |

---

## [7] Frigola et al. / Springer (2024) — Cumulative Heating

**"A Scan Strategy Based Compensation of Cumulative Heating Effects in Electron Beam Powder Bed Fusion"**
*Progress in Additive Manufacturing* 10 (2025) 3455–3473

| Verwendung | Relevanz |
|---|---|
| Kumulative Aufheizung durch benachbarte Hatch-Linien | → Physikalische Grundlage der Heat Accumulation Map |
| Hatch-Spacing-Adaptation zur thermischen Kompensation | → Alternative zu fixem Spacing: variable Abstände |
| Thermisches Modell mit vereinfachter Wärmeleitung | → Basis für den Heat-Map-Algorithmus |

---

## [8] Tammas-Williams, S. et al. (2015)

**"XCT analysis of the influence of melt strategies on defect population in Ti-6Al-4V by SEBM"**
*Materials Characterization* 102 (2015) 47–61

| Verwendung | Relevanz |
|---|---|
| 180°-Wendepunkte an Rasterlinien-Enden → Defekte | → Motivation für Spiral/Hilbert (keine Wendepunkte) |

---

## [9] Li, Z. et al. (2024) — Dashed-Scan Contouring

**"A surface quality optimization strategy via dashed-scan contouring in EB-PBF"**
*Journal of Materials Processing Technology* 329 (2024) 118454

| Verwendung | Relevanz |
|---|---|
| Segmentierte Kontur statt durchgehender Linie | → Nicht direkt relevant (Kontur entfällt), aber Konzept der Segmentierung übertragbar auf Infill |

---

## [10] CarTech® Micro-Melt® 23 Alloy Datenblatt

**Carpenter Technology Corporation** (2014/2020)

| Verwendung | Relevanz |
|---|---|
| Dichte: 0.2952 lb/in³ (8170 kg/m³) | → Heat Map Berechnung |
| Spez. Wärme: 0.1004 Btu/lb/°F (420 J/kg·K) | → Heat Map Berechnung |
| CTE: 6.70–7.70 × 10⁻⁶ in/in/°F | → Verzugsabschätzung |
| Arbeitshärte HRC 62–66 | → Zielwert für Validierung |
| Zusammensetzung: 1.30%C, 4.20%Cr, 5.00%Mo, 6.30%W, 3.10%V | → Legierungsklasse HSS |

---

## Zuordnung: Quelle → Review-Punkt

| Review-Punkt | Quellen |
|---|---|
| 2. Batch-Ordner-Modus | [Poster] — Workflow-Anforderung |
| 5. Zick-Zack bei MultiLineString | [8] Tammas-Williams |
| 6a. Island/Chessboard | [3] Zaeh & Kahnert |
| 6b. Hilbert-Kurve | [4] Babu, [5] Frey, [6] Sebastian |
| 6c. Spiral-Scan | [4] Babu, [5] Frey |
| 7. Heat Accumulation Map | [7] Frigola, [1] Lee (Table 2), [10] Datenblatt |