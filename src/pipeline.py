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
        work_infill = [
            replace(info, path=os.path.join(work_dir, os.path.relpath(info.path, session.extract_dir)))
            for info in session.infill_files
        ]
        errors = process_infill_files(
            work_infill,
            params,
            progress_cb=progress_cb,
            layer_seq_map=session.layer_seq_map,
        )
        base_name = os.path.splitext(os.path.basename(session.zip_path))[0]
        out_zip = export_zip(work_dir, output_dir, base_name)
        return errors, out_zip
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def export_zip(extract_dir: str, output_dir: str, base_name: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    out_zip_name = f"{base_name}_NEW.zip"
    out_zip_path = os.path.join(output_dir, out_zip_name)

    with zipfile.ZipFile(out_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(extract_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                arc_name = os.path.relpath(abs_path, extract_dir)
                zf.write(abs_path, arc_name)

    return out_zip_path
