from __future__ import annotations

import glob
import os
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, replace
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from src.exporter import B99Exporter
from src.parser import B99Parser
from src.reorder import reorder_points


@dataclass(frozen=True)
class B99FileInfo:
    path: str
    filename: str
    layer: int
    classification: str
    layer_key: int = 0
    object_id: int = -1


class ZipSession:
    def __init__(
        self,
        zip_path: str,
        temp_dir: tempfile.TemporaryDirectory,
        extract_dir: str,
        figure_dir: str,
        b99_files: List[B99FileInfo],
        infill_files: List[B99FileInfo],
        contour_files: List[B99FileInfo],
        support_files: List[B99FileInfo],
        cutoff_layer: int,
        layer_seq_map: Optional[Dict[int, int]] = None,
    ) -> None:
        self.zip_path = zip_path
        self.temp_dir = temp_dir
        self.extract_dir = extract_dir
        self.figure_dir = figure_dir
        self.b99_files = b99_files
        self.infill_files = infill_files
        self.contour_files = contour_files
        self.support_files = support_files
        self.cutoff_layer = cutoff_layer
        self.layer_seq_map = layer_seq_map if layer_seq_map is not None else build_layer_seq_map(b99_files)

    def cleanup(self) -> None:
        self.temp_dir.cleanup()

    @classmethod
    def from_zip(cls, zip_path: str) -> "ZipSession":
        temp_dir = tempfile.TemporaryDirectory()
        extract_dir = os.path.join(temp_dir.name, "extracted")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        figure_dir = find_figure_dir(extract_dir)
        if figure_dir is None:
            temp_dir.cleanup()
            raise FileNotFoundError("Kein 'Figure Files' Ordner im ZIP gefunden.")

        b99_files = collect_b99_files(figure_dir)
        cutoff_layer = find_infill_cutoff(b99_files)

        infill_files: List[B99FileInfo] = []
        contour_files: List[B99FileInfo] = []
        support_files: List[B99FileInfo] = []

        for info in b99_files:
            if info.layer < cutoff_layer:
                support_files.append(info)
                continue
            if info.classification in ("infill_even", "infill_9"):
                infill_files.append(info)
            else:
                contour_files.append(info)

        return cls(
            zip_path=zip_path,
            temp_dir=temp_dir,
            extract_dir=extract_dir,
            figure_dir=figure_dir,
            b99_files=b99_files,
            infill_files=infill_files,
            contour_files=contour_files,
            support_files=support_files,
            cutoff_layer=cutoff_layer,
        )


def classify_b99(filename: str) -> str:
    name = os.path.splitext(filename)[0]
    if len(name) < 2:
        return "other"
    second_last = name[-2]
    if not second_last.isdigit():
        return "other"
    digit = int(second_last)
    if digit % 2 == 0:
        return "infill_even"
    if digit == 9:
        return "infill_9"
    return "contour"


def extract_layer_number(filename: str) -> int:
    name = os.path.splitext(filename)[0]
    match = re.match(r"^(\d+)", name)
    return int(match.group(1)) if match else 0


def extract_layer_key(filename: str) -> int:
    """Physische Schichtnummer: führende Ziffern ohne die letzten beiden Stellen
    (Objekt-Ziffer + Suffix). Beispiel: '21020.B99' → Schicht 210."""
    name = os.path.splitext(filename)[0]
    match = re.match(r"^(\d+)", name)
    if not match:
        return 0
    digits = match.group(1)
    if len(digits) <= 2:
        return int(digits)
    return int(digits[:-2])


def extract_object_id(filename: str) -> int:
    """Objekt-Ziffer (vorletzte Stelle vor .B99) – dieselbe Ziffer, die classify_b99 auswertet."""
    name = os.path.splitext(filename)[0]
    if len(name) >= 2 and name[-2].isdigit():
        return int(name[-2])
    return -1


def build_layer_seq_map(b99_files: List[B99FileInfo]) -> Dict[int, int]:
    """Sequentieller Schichtindex (0, 1, 2 …) pro physischer Schichtnummer.
    Grundlage für die schichtweise Rotation: Schicht N → N × rotation_angle_deg."""
    layer_keys = sorted({info.layer_key for info in b99_files})
    return {key: idx for idx, key in enumerate(layer_keys)}


def find_infill_cutoff(b99_files: List[B99FileInfo]) -> int:
    for info in sorted(b99_files, key=lambda x: x.layer):
        if info.classification == "infill_even":
            return info.layer
    return 2**31


def find_figure_dir(extract_dir: str) -> Optional[str]:
    for root, dirs, _files in os.walk(extract_dir):
        if "Figure Files" in dirs:
            return os.path.join(root, "Figure Files")
        if os.path.basename(root) == "Figure Files":
            return root
    return None


def collect_b99_files(figure_dir: str) -> List[B99FileInfo]:
    paths = sorted(
        glob.glob(os.path.join(figure_dir, "*.[Bb]99")),
        key=lambda x: extract_layer_number(os.path.basename(x)),
    )
    infos: List[B99FileInfo] = []
    for path in paths:
        filename = os.path.basename(path)
        infos.append(
            B99FileInfo(
                path=path,
                filename=filename,
                layer=extract_layer_number(filename),
                classification=classify_b99(filename),
                layer_key=extract_layer_key(filename),
                object_id=extract_object_id(filename),
            )
        )
    return infos


def read_points_mm(filepath: str) -> np.ndarray:
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    _header, points_mm = B99Parser.extract_points_and_header(content)
    return points_mm


def process_single_infill(filepath: str, params: dict, layer_idx: int) -> None:
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    header_lines, points_mm = B99Parser.extract_points_and_header(content)

    if len(points_mm) == 0:
        return

    reordered = reorder_points(points_mm, params, layer_idx)
    new_content = B99Exporter.write_reordered_b99(header_lines, reordered)

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        f.write(new_content)


def process_infill_files(
    infill_files: List[B99FileInfo],
    params: dict,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    layer_seq_map: Optional[Dict[int, int]] = None,
) -> List[str]:
    if layer_seq_map is None:
        layer_seq_map = build_layer_seq_map(infill_files)
    errors: List[str] = []
    total = len(infill_files)
    for idx, info in enumerate(infill_files):
        try:
            layer_idx = layer_seq_map.get(info.layer_key, 0)
            process_single_infill(info.path, params, layer_idx)
        except Exception as exc:
            errors.append(f"{info.filename}: {exc}")
        if progress_cb:
            progress_cb(idx + 1, total)
    return errors


def _build_contour_params(params: dict) -> dict:
    """Leitet aus dem Haupt-Parametersatz einen Parametersatz für die optionale
    Kontur-Neuanordnung ab.

    Konturen sind dünne Ränder (kein gefülltes Gebiet) – eine 2D-Flächen-
    Segmentierung (Schachbrett/Hexagonal/Spiralzonen) entartet darauf. Deshalb
    wird die Kontur ohne Segmentierung verarbeitet; nur die Spot-Reihenfolge des
    Rings wird über eine punktbasierte Mikro-Strategie neu sortiert. Alle übrigen
    Schlüssel werden vom Haupt-Parametersatz geerbt, damit reorder_points keine
    fehlenden Keys sieht."""
    cp = dict(params)
    cp["segmentation"] = "Keine Segmentierung"
    cp["seg_overlap"] = 0.0  # kein Overlap → keine Punktverdopplung auf der Kontur
    cp["micro_strategy"] = params.get("contour_micro_strategy", "Spot Ordered")
    cp["spot_skip"] = int(params.get("contour_spot_skip", params.get("spot_skip", 2)))
    cp["greedy_memory"] = int(params.get("contour_greedy_memory", params.get("greedy_memory", 4)))
    cp["greedy_w2"] = float(params.get("contour_greedy_w2", params.get("greedy_w2", 0.5)))
    return cp


def build_strategy_tag(params: dict) -> str:
    """Kompakter, dateinamentauglicher Strategie-Kürzel aus den params.

    Beispiel: 'Schach2.0mm-ov0.1_SpotOrd-s1_rot0' – beschreibt die gewählte
    Segmentierung, Mikro-Strategie und (falls ≠ 0) die Schichtrotation, damit
    man der Export-ZIP ansieht, womit sie erzeugt wurde.
    """
    seg_codes = {
        "Keine Segmentierung": "",
        "Schachbrett (Island)": "Schach",
        "Streifen (Stripe)": "Streifen",
        "Hexagonal": "Hexa",
        "Spiralzonen (Konzentrisch)": "Spiralz",
    }
    micro_codes = {
        "Raster (Zick-Zack)": "Raster",
        "Spot Consecutive": "SpotCons",
        "Spot Ordered": "SpotOrd",
        "Ghost Beam": "Ghost",
        "Hilbert-Kurve": "Hilbert",
        "Spiral": "Spiral",
        "Peano-Kurve": "Peano",
        "Greedy (Nächster Nachbar)": "Greedy",
        "Dispersions-Maximum": "DispMax",
        "Gitter-Dispersion (deterministisch)": "GitDispDet",
        "Gitter-Dispersion (stochastisch)": "GitDispStoch",
        "Dichte-adaptiv": "DichteAdapt",
        "Verschachtelte Streifen": "VStreifen",
    }

    parts: List[str] = []

    seg = params.get("segmentation", "Keine Segmentierung")
    seg_code = seg_codes.get(seg, "")
    if seg_code:
        seg_part = f"{seg_code}{float(params.get('seg_size', 5.0)):g}mm"
        overlap_um = float(params.get("seg_overlap", 0.0))
        if overlap_um > 0:
            seg_part += f"-ov{overlap_um / 1000.0:g}"
        parts.append(seg_part)

    micro = params.get("micro_strategy", "Raster (Zick-Zack)")
    micro_code = micro_codes.get(micro, "Micro")
    if micro == "Spot Ordered":
        micro_code += f"-s{int(params.get('spot_skip', 2))}"
    elif micro == "Ghost Beam":
        micro_code += f"-lag{float(params.get('ghost_lag', 1000.0)) / 1000.0:g}"
    parts.append(micro_code)

    rot = float(params.get("rotation_angle_deg", 0.0))
    parts.append(f"rot{rot:g}")

    if params.get("contour_reorder"):
        cmicro = micro_codes.get(params.get("contour_micro_strategy", ""), "Kontur")
        parts.append(f"Kont{cmicro}")

    tag = "_".join(parts)
    # Nur dateinamen-sichere Zeichen behalten
    return re.sub(r"[^0-9A-Za-z._-]", "", tag)


def run_export(
    session: "ZipSession",
    params: dict,
    output_dir: str,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> Tuple[List[str], str]:
    """Wendet die Strategie auf eine Arbeitskopie an und erstellt das Ausgabe-ZIP.

    Die extrahierten Originaldateien bleiben unverändert – dadurch liefert jeder
    Export dieselbe Ausgangsbasis (kein Doppel-Reorder bei erneutem Export) und
    die Vorschau liest nie halbgeschriebene Dateien.
    """
    work_dir = tempfile.mkdtemp(prefix="ebm_export_")
    try:
        shutil.copytree(session.extract_dir, work_dir, dirs_exist_ok=True)

        def to_work(info: B99FileInfo) -> B99FileInfo:
            return replace(info, path=os.path.join(work_dir, os.path.relpath(info.path, session.extract_dir)))

        work_infill = [to_work(info) for info in session.infill_files]
        do_contour = bool(params.get("contour_reorder"))
        work_contour = [to_work(info) for info in session.contour_files] if do_contour else []

        # Gemeinsamer Fortschritt über Infill- und (optional) Kontur-Dateien.
        total = len(work_infill) + len(work_contour)

        def rebased_cb(offset: int):
            if progress_cb is None:
                return None
            return lambda current, _total: progress_cb(offset + current, total)

        errors = process_infill_files(
            work_infill,
            params,
            progress_cb=rebased_cb(0),
            layer_seq_map=session.layer_seq_map,
        )
        if do_contour:
            errors += process_infill_files(
                work_contour,
                _build_contour_params(params),
                progress_cb=rebased_cb(len(work_infill)),
                layer_seq_map=session.layer_seq_map,
            )

        base_name = os.path.splitext(os.path.basename(session.zip_path))[0]
        out_zip = export_zip(work_dir, output_dir, base_name, build_strategy_tag(params))
        return errors, out_zip
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def export_zip(extract_dir: str, output_dir: str, base_name: str, strategy_tag: str = "") -> str:
    os.makedirs(output_dir, exist_ok=True)
    suffix = f"_{strategy_tag}" if strategy_tag else ""
    out_zip_name = f"{base_name}{suffix}_NEW.zip"
    out_zip_path = os.path.join(output_dir, out_zip_name)

    with zipfile.ZipFile(out_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(extract_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                arc_name = os.path.relpath(abs_path, extract_dir)
                zf.write(abs_path, arc_name)

    return out_zip_path
