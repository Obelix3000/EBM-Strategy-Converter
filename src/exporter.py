import io
from typing import List
from src.strategies.base_strategy import ScanPath

class B99Exporter:
    """
    Formatierungs-Manager für die eigentliche Arcam .B99 Datei-Erstellung.
    Fasst alle abstrakten ScanPath-Datenklassen der Schichten zusammen und erzeugt
    den finalen maschinen-lesbaren String, der direkt in Control Software der
    EBM-Anlagen eingespielt werden kann.
    """
    
    @staticmethod
    def generate_b99_content(layers_paths: List[ScanPath]) -> str:
        """
        Nimmt die kompilierte Liste an Schichten samt Strategien entgegen 
        und mapt sie in Zeilen ("Strings") des .B99-Formates.
        """
        content = []
        
        # Standard Arcam-Header für den Kontext der Anlage (A2X)
        # Enthält die physische Plattformdimension
        content.append("# platform dimension=120.0x120.0x200.0 mm")
        content.append("# vector")
        content.append("# double")
        
        for layer_idx, scan_path in enumerate(layers_paths):
            if not scan_path or not scan_path.segments:
                continue
                
            # Schichtmarker: Jedes Mal, wenn die Z-Achse gesenkt wird
            content.append(f"# figure Grp01_Layer{layer_idx:04d}_Infill")
            
            # Zähle die Gesamtheit aller Koordinaten für die Header-Metadaten.
            # Hilft beim Verifizieren von Dateigrößen / Punktemengen.
            num_points = sum(len(seg) for seg in scan_path.segments)
            content.append(f"# Generic Infill: Point Index=0  Number Points={num_points}")
            
            # Der Tag 'data' gibt dem Arcam das Zeichen, dass als nächstes 
            # rohe Befehle an die Beam-Deflexions-Engine versendet werden.
            content.append("data")
            
            for segment in scan_path.segments:
                for x, y in segment:
                    # Das Zentrum der Plattform in Metrik ist bei Arcam immer (0,0)
                    # Relativ bedeutet hier: Der Rand +/- 60mm in echt ist 1.0 / -1.0 in der Datei.
                    # Daher wird alles durch die Referenz 60.0 skaliert!
                    rx = x / 60.0
                    ry = y / 60.0
                    
                    # Das 'ABS' Kommando ist das absolute Repositions- & Schmelzkommando.
                    # WIRD EIN GROSSER KOORDINATENABSTAND ODER EIN NEUES SEGMENT GESTARTET,
                    # WIRD DER STRAHL IMPLIZIT MASCHINENSEITIG AUSGESCHALTET! (Beam-off Jump).
                    content.append(f"ABS {rx:.6f} {ry:.6f}")
                    
        return "\n".join(content) + "\n"

    @staticmethod
    def generate_b99_single_layer(scan_path: ScanPath, layer_idx: int) -> str:
        """
        Generiert den B99-Inhalt für exakt eine Schicht und übernimmt die 
        globale Schichtnummer (layer_idx). Wird für Einzeldatei-Exporte benötigt.
        """
        content = []
        content.append("# platform dimension=120.0x120.0x200.0 mm")
        content.append("# vector")
        content.append("# double")
        
        if not scan_path or not scan_path.segments:
            return ""
            
        content.append(f"# figure Grp01_Layer{layer_idx:04d}_Infill")
        num_points = sum(len(seg) for seg in scan_path.segments)
        content.append(f"# Generic Infill: Point Index=0  Number Points={num_points}")
        content.append("data")
        
        for segment in scan_path.segments:
            for x, y in segment:
                rx = x / 60.0
                ry = y / 60.0
                content.append(f"ABS {rx:.6f} {ry:.6f}")
                
        return "\n".join(content) + "\n"
