from __future__ import annotations

import glob
import os
import re
import tempfile
import zipfile
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

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
) -> List[str]:
    errors: List[str] = []
    total = len(infill_files)
    for idx, info in enumerate(infill_files):
        try:
            process_single_infill(info.path, params, info.layer)
        except Exception as exc:
            errors.append(f"{info.filename}: {exc}")
        if progress_cb:
            progress_cb(idx + 1, total)
    return errors


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
