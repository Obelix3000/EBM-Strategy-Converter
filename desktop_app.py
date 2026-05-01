import os
import sys
from typing import Optional

import numpy as np
from PySide6 import QtCore, QtWidgets
from shapely.geometry import MultiPoint
from vispy import color, scene

from src.pipeline import ZipSession, export_zip, process_infill_files, read_points_mm
from src.reorder import reorder_points


BUILD_PLATE_HALF_MM = 60.0
LAYER_HEIGHT_MM = 0.08


class WorkerSignals(QtCore.QObject):
    finished = QtCore.Signal()
    error = QtCore.Signal(str)
    result = QtCore.Signal(object)
    progress = QtCore.Signal(int)


class Worker(QtCore.QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.progress_callback = None

    @QtCore.Slot()
    def run(self):
        try:
            if self.progress_callback is not None:
                self.kwargs["progress_callback"] = self.progress_callback
            result = self.fn(*self.args, **self.kwargs)
        except Exception as exc:
            self.signals.error.emit(str(exc))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


class PreviewCanvas(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.canvas = scene.SceneCanvas(keys="interactive", bgcolor="#0e0f12", show=False)
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = "turntable"
        self.view.camera.fov = 45
        self.view.camera.distance = 220

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas.native)

        self.colormap = color.get_colormap("viridis")

        self.grid_visual = scene.visuals.Line(parent=self.view.scene, method="gl")
        self.plate_visual = scene.visuals.Line(parent=self.view.scene, method="gl")
        self.boundary_visual = scene.visuals.Line(parent=self.view.scene, method="gl")
        self.points_visual = scene.visuals.Markers(parent=self.view.scene)
        self.path_visual = scene.visuals.Line(parent=self.view.scene, method="gl")

        self._init_build_plate()

    def _init_build_plate(self) -> None:
        half = BUILD_PLATE_HALF_MM
        grid_step = 10.0
        grid_lines = []
        for x in np.arange(-half, half + grid_step, grid_step):
            grid_lines.extend([[x, -half, 0.0], [x, half, 0.0], [np.nan, np.nan, np.nan]])
        for y in np.arange(-half, half + grid_step, grid_step):
            grid_lines.extend([[-half, y, 0.0], [half, y, 0.0], [np.nan, np.nan, np.nan]])
        grid_pos = np.array(grid_lines, dtype=np.float32)
        self.grid_visual.set_data(pos=grid_pos, color=(0.25, 0.27, 0.3, 0.35))

        plate = np.array(
            [
                [-half, -half, 0.0],
                [half, -half, 0.0],
                [half, half, 0.0],
                [-half, half, 0.0],
                [-half, -half, 0.0],
            ],
            dtype=np.float32,
        )
        self.plate_visual.set_data(pos=plate, color=(0.9, 0.6, 0.2, 0.7), width=2)

    def update_preview(
        self,
        points_xyz: np.ndarray,
        point_colors: np.ndarray,
        path_xyz: Optional[np.ndarray],
        path_colors: Optional[np.ndarray],
        boundary_xyz: Optional[np.ndarray],
        show_points: bool,
        show_path: bool,
    ) -> None:
        if points_xyz.size == 0:
            self.points_visual.set_data(pos=np.zeros((0, 3), dtype=np.float32))
        else:
            self.points_visual.set_data(pos=points_xyz, face_color=point_colors, size=3)

        self.points_visual.visible = show_points

        if path_xyz is None or path_xyz.size == 0:
            self.path_visual.set_data(pos=np.zeros((0, 3), dtype=np.float32))
        else:
            self.path_visual.set_data(pos=path_xyz, color=path_colors, width=1)

        self.path_visual.visible = show_path

        if boundary_xyz is None or boundary_xyz.size == 0:
            self.boundary_visual.set_data(pos=np.zeros((0, 3), dtype=np.float32))
        else:
            self.boundary_visual.set_data(pos=boundary_xyz, color=(0.95, 0.6, 0.2, 0.9), width=2)

        self.canvas.update()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("EBM Strategy Desktop")
        self.resize(1400, 900)

        self.thread_pool = QtCore.QThreadPool.globalInstance()
        self.session: Optional[ZipSession] = None
        self.current_preview_index = 0
        self.updating_selection = False
        self.preview_worker_active = False
        self.preview_pending = False
        self.layer_order = []
        self.layer_index_map = {}

        self.preview_canvas = PreviewCanvas()

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(self.preview_canvas)

        control_panel = QtWidgets.QWidget()
        panel_layout = QtWidgets.QVBoxLayout(control_panel)
        panel_layout.setContentsMargins(12, 12, 12, 12)
        panel_layout.setSpacing(12)

        panel_layout.addWidget(self._build_file_group())
        panel_layout.addWidget(self._build_preview_group())
        panel_layout.addWidget(self._build_strategy_group())
        panel_layout.addWidget(self._build_export_group())
        panel_layout.addStretch(1)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(control_panel)

        splitter.addWidget(scroll)
        splitter.setSizes([950, 450])
        self.setCentralWidget(splitter)

        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)

    def _build_file_group(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("Projekt")
        layout = QtWidgets.QVBoxLayout(group)

        self.load_button = QtWidgets.QPushButton("ZIP laden")
        self.zip_path_label = QtWidgets.QLabel("Kein ZIP geladen")
        self.zip_path_label.setWordWrap(True)

        output_row = QtWidgets.QHBoxLayout()
        self.output_dir_edit = QtWidgets.QLineEdit()
        self.output_dir_edit.setText(os.path.join(os.path.expanduser("~"), "EBM_Output"))
        self.output_dir_button = QtWidgets.QPushButton("Durchsuchen")
        output_row.addWidget(self.output_dir_edit, 1)
        output_row.addWidget(self.output_dir_button)

        stats_row = QtWidgets.QHBoxLayout()
        self.stats_label = QtWidgets.QLabel("B99: 0 | Infill: 0 | Kontur: 0 | Support: 0")
        stats_row.addWidget(self.stats_label)

        layer_row = QtWidgets.QHBoxLayout()
        self.layer_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.layer_slider.setMinimum(0)
        self.layer_slider.setMaximum(0)
        self.layer_label = QtWidgets.QLabel("Layer: -")
        layer_row.addWidget(self.layer_slider, 1)
        layer_row.addWidget(self.layer_label)

        self.infill_combo = QtWidgets.QComboBox()

        layout.addWidget(self.load_button)
        layout.addWidget(self.zip_path_label)
        layout.addWidget(QtWidgets.QLabel("Ausgabeordner:"))
        layout.addLayout(output_row)
        layout.addLayout(stats_row)
        layout.addWidget(QtWidgets.QLabel("Infill-Datei fuer Vorschau:"))
        layout.addWidget(self.infill_combo)
        layout.addLayout(layer_row)
        return group

    def _build_preview_group(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("Vorschau")
        layout = QtWidgets.QVBoxLayout(group)

        self.preview_mode_combo = QtWidgets.QComboBox()
        self.preview_mode_combo.addItems(["Punkte", "Linien", "Beides"])
        self.preview_mode_combo.setCurrentText("Beides")

        self.preview_hint = QtWidgets.QLabel("Rotation sichtbar in Linien/Beides")
        self.preview_hint.setWordWrap(True)

        self.reordered_check = QtWidgets.QCheckBox("Strategie anwenden (reorder)")
        self.reordered_check.setChecked(True)

        max_row = QtWidgets.QHBoxLayout()
        self.max_points_spin = QtWidgets.QSpinBox()
        self.max_points_spin.setRange(500, 20000)
        self.max_points_spin.setSingleStep(500)
        self.max_points_spin.setValue(2000)
        max_row.addWidget(QtWidgets.QLabel("Max Punkte pro Layer:"))
        max_row.addWidget(self.max_points_spin)

        self.preview_progress = QtWidgets.QProgressBar()
        self.preview_progress.setRange(0, 100)
        self.preview_progress.setValue(0)
        self.preview_progress.setTextVisible(False)
        self.preview_status = QtWidgets.QLabel("Vorschau: bereit")
        self.preview_status.setWordWrap(True)

        layout.addWidget(QtWidgets.QLabel("Darstellung:"))
        layout.addWidget(self.preview_mode_combo)
        layout.addWidget(self.preview_hint)
        layout.addWidget(self.reordered_check)
        layout.addLayout(max_row)
        layout.addWidget(self.preview_progress)
        layout.addWidget(self.preview_status)
        return group

    def _build_strategy_group(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("Strategie")
        layout = QtWidgets.QFormLayout(group)

        self.segmentation_combo = QtWidgets.QComboBox()
        self.segmentation_combo.addItems(
            [
                "Keine Segmentierung",
                "Schachbrett (Island)",
                "Streifen (Stripe)",
                "Hexagonal",
                "Spiralzonen (Konzentrisch)",
            ]
        )

        self.seg_size_spin = QtWidgets.QDoubleSpinBox()
        self.seg_size_spin.setRange(1.0, 100.0)
        self.seg_size_spin.setValue(5.0)
        self.seg_size_spin.setSingleStep(0.5)

        self.seg_overlap_spin = QtWidgets.QDoubleSpinBox()
        self.seg_overlap_spin.setRange(0.0, 2000.0)
        self.seg_overlap_spin.setValue(100.0)
        self.seg_overlap_spin.setSingleStep(10.0)

        self.seg_order_combo = QtWidgets.QComboBox()
        self.seg_order_combo.addItems(
            [
                "Schachbrett (schwarz→weiß)",
                "Spirale (außen→innen)",
                "Spirale (innen→außen)",
                "Zufällig",
                "Sequentiell (links→rechts)",
            ]
        )

        self.micro_combo = QtWidgets.QComboBox()
        self.micro_combo.addItems(
            [
                "Raster (Zick-Zack)",
                "Spot Consecutive",
                "Spot Ordered",
                "Ghost Beam",
                "Hilbert-Kurve",
                "Spiral",
                "Peano-Kurve",
            ]
        )
        self.micro_combo.insertSeparator(7)
        self.micro_combo.addItems(
            [
                "Greedy (Nächster Nachbar)",
                "Dispersions-Maximum",
                "Gitter-Dispersion (deterministisch)",
                "Gitter-Dispersion (stochastisch)",
                "Dichte-adaptiv",
                "Verschachtelte Streifen",
            ]
        )

        self.hatch_spacing_spin = QtWidgets.QDoubleSpinBox()
        self.hatch_spacing_spin.setRange(10.0, 1000.0)
        self.hatch_spacing_spin.setValue(200.0)
        self.hatch_spacing_spin.setSingleStep(10.0)

        self.rotation_spin = QtWidgets.QDoubleSpinBox()
        self.rotation_spin.setRange(0.0, 360.0)
        self.rotation_spin.setValue(67.0)
        self.rotation_spin.setSingleStep(1.0)

        self.ghost_lag_spin = QtWidgets.QDoubleSpinBox()
        self.ghost_lag_spin.setRange(10.0, 10000.0)
        self.ghost_lag_spin.setValue(1000.0)
        self.ghost_lag_spin.setSingleStep(100.0)

        self.spot_skip_spin = QtWidgets.QSpinBox()
        self.spot_skip_spin.setRange(1, 20)
        self.spot_skip_spin.setValue(2)

        self.hilbert_order_spin = QtWidgets.QSpinBox()
        self.hilbert_order_spin.setRange(2, 7)
        self.hilbert_order_spin.setValue(4)

        self.spiral_dir_combo = QtWidgets.QComboBox()
        self.spiral_dir_combo.addItems(["inward", "outward"])

        self.greedy_memory_spin = QtWidgets.QSpinBox()
        self.greedy_memory_spin.setRange(1, 10)
        self.greedy_memory_spin.setValue(4)

        self.greedy_w2_spin = QtWidgets.QDoubleSpinBox()
        self.greedy_w2_spin.setRange(0.0, 2.0)
        self.greedy_w2_spin.setSingleStep(0.1)
        self.greedy_w2_spin.setValue(0.5)

        self.grid_cell_spin = QtWidgets.QDoubleSpinBox()
        self.grid_cell_spin.setRange(0.5, 20.0)
        self.grid_cell_spin.setSingleStep(0.5)
        self.grid_cell_spin.setValue(3.0)

        self.interlace_forward_spin = QtWidgets.QSpinBox()
        self.interlace_forward_spin.setRange(1, 20)
        self.interlace_forward_spin.setValue(3)

        self.interlace_backward_spin = QtWidgets.QSpinBox()
        self.interlace_backward_spin.setRange(1, 20)
        self.interlace_backward_spin.setValue(2)

        layout.addRow("Segmentierung", self.segmentation_combo)
        self.seg_size_label = QtWidgets.QLabel("Segmentgroesse (mm)")
        self.seg_overlap_label = QtWidgets.QLabel("Segment-Overlap (um)")
        self.seg_order_label = QtWidgets.QLabel("Segment-Reihenfolge")
        layout.addRow(self.seg_size_label, self.seg_size_spin)
        layout.addRow(self.seg_overlap_label, self.seg_overlap_spin)
        layout.addRow(self.seg_order_label, self.seg_order_combo)
        layout.addRow("Mikro-Strategie", self.micro_combo)
        layout.addRow("Linien-Abstand (um)", self.hatch_spacing_spin)
        layout.addRow("Rotation pro Layer (grad)", self.rotation_spin)
        self.ghost_lag_label = QtWidgets.QLabel("Ghost Beam Lag (um)")
        self.spot_skip_label = QtWidgets.QLabel("Spot Skip")
        self.hilbert_order_label = QtWidgets.QLabel("Hilbert/Peano Ordnung")
        self.spiral_dir_label = QtWidgets.QLabel("Spiral Richtung")
        self.greedy_memory_label = QtWidgets.QLabel("Greedy Gedaechtnis")
        self.greedy_w2_label = QtWidgets.QLabel("Greedy Gewicht")
        self.grid_cell_label = QtWidgets.QLabel("Gitter-Zellgroesse (mm)")
        self.interlace_forward_label = QtWidgets.QLabel("Verschachtelt Vorwaerts")
        self.interlace_backward_label = QtWidgets.QLabel("Verschachtelt Rueckwaerts")
        layout.addRow(self.ghost_lag_label, self.ghost_lag_spin)
        layout.addRow(self.spot_skip_label, self.spot_skip_spin)
        layout.addRow(self.hilbert_order_label, self.hilbert_order_spin)
        layout.addRow(self.spiral_dir_label, self.spiral_dir_combo)
        layout.addRow(self.greedy_memory_label, self.greedy_memory_spin)
        layout.addRow(self.greedy_w2_label, self.greedy_w2_spin)
        layout.addRow(self.grid_cell_label, self.grid_cell_spin)
        layout.addRow(self.interlace_forward_label, self.interlace_forward_spin)
        layout.addRow(self.interlace_backward_label, self.interlace_backward_spin)

        self._update_strategy_controls()
        return group

    def _build_export_group(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("Export")
        layout = QtWidgets.QVBoxLayout(group)

        self.export_button = QtWidgets.QPushButton("Strategie anwenden & ZIP erstellen")
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.export_status = QtWidgets.QLabel("Noch kein Export gestartet")
        self.export_status.setWordWrap(True)

        layout.addWidget(self.export_button)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.export_status)
        return group

    def _connect_signals(self) -> None:
        self.load_button.clicked.connect(self._load_zip)
        self.output_dir_button.clicked.connect(self._choose_output_dir)
        self.layer_slider.valueChanged.connect(self._layer_slider_changed)
        self.infill_combo.currentIndexChanged.connect(self._combo_changed)
        self.preview_mode_combo.currentIndexChanged.connect(self._request_preview)
        self.reordered_check.stateChanged.connect(self._request_preview)
        self.max_points_spin.valueChanged.connect(self._request_preview)
        self.segmentation_combo.currentIndexChanged.connect(self._update_strategy_controls)
        self.micro_combo.currentIndexChanged.connect(self._update_strategy_controls)
        self.segmentation_combo.currentIndexChanged.connect(self._request_preview)
        self.micro_combo.currentIndexChanged.connect(self._request_preview)
        self.seg_size_spin.valueChanged.connect(self._request_preview)
        self.seg_overlap_spin.valueChanged.connect(self._request_preview)
        self.seg_order_combo.currentIndexChanged.connect(self._request_preview)
        self.hatch_spacing_spin.valueChanged.connect(self._request_preview)
        self.rotation_spin.valueChanged.connect(self._request_preview)
        self.ghost_lag_spin.valueChanged.connect(self._request_preview)
        self.spot_skip_spin.valueChanged.connect(self._request_preview)
        self.hilbert_order_spin.valueChanged.connect(self._request_preview)
        self.spiral_dir_combo.currentIndexChanged.connect(self._request_preview)
        self.greedy_memory_spin.valueChanged.connect(self._request_preview)
        self.greedy_w2_spin.valueChanged.connect(self._request_preview)
        self.grid_cell_spin.valueChanged.connect(self._request_preview)
        self.interlace_forward_spin.valueChanged.connect(self._request_preview)
        self.interlace_backward_spin.valueChanged.connect(self._request_preview)
        self.export_button.clicked.connect(self._run_export)

    def _choose_output_dir(self) -> None:
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Ausgabeordner waehlen")
        if directory:
            self.output_dir_edit.setText(directory)

    def _load_zip(self) -> None:
        zip_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "ZIP laden", "", "ZIP Files (*.zip)"
        )
        if not zip_path:
            return

        if self.session:
            self.session.cleanup()
            self.session = None

        try:
            self.session = ZipSession.from_zip(zip_path)
        except Exception as exc:
            self.status_bar.showMessage(f"Fehler: {exc}")
            return

        self.zip_path_label.setText(zip_path)
        self._populate_infill_list()
        self._update_stats()
        self.status_bar.showMessage("ZIP geladen")
        self._request_preview()

    def _populate_infill_list(self) -> None:
        self.updating_selection = True
        self.infill_combo.clear()
        self.current_preview_index = 0
        self.layer_order = []
        self.layer_index_map = {}

        if not self.session or not self.session.infill_files:
            self.layer_slider.setMaximum(0)
            self.layer_label.setText("Layer: -")
            self.updating_selection = False
            return

        for info in self.session.infill_files:
            preview_layer = self._preview_layer_key(info.filename)
            label = f"{info.filename} (Layer {preview_layer})"
            self.infill_combo.addItem(label)

        self.layer_order = sorted(
            {self._preview_layer_key(info.filename) for info in self.session.b99_files}
        )
        self.layer_index_map = {layer: idx for idx, layer in enumerate(self.layer_order)}

        self.layer_slider.setMaximum(max(0, len(self.session.infill_files) - 1))
        self.layer_slider.setValue(0)
        self.infill_combo.setCurrentIndex(0)
        self._update_layer_label(0)
        self.updating_selection = False

    def _update_stats(self) -> None:
        if not self.session:
            self.stats_label.setText("B99: 0 | Infill: 0 | Kontur: 0 | Support: 0")
            return
        total = len(self.session.b99_files)
        infill = len(self.session.infill_files)
        contour = len(self.session.contour_files)
        support = len(self.session.support_files)
        self.stats_label.setText(
            f"B99: {total} | Infill: {infill} | Kontur: {contour} | Support: {support}"
        )

    def _layer_slider_changed(self, value: int) -> None:
        if self.updating_selection:
            return
        self._set_selected_index(value)

    def _combo_changed(self, index: int) -> None:
        if self.updating_selection:
            return
        self._set_selected_index(index)

    def _set_selected_index(self, index: int) -> None:
        if not self.session or not self.session.infill_files:
            return
        index = max(0, min(index, len(self.session.infill_files) - 1))
        self.updating_selection = True
        self.current_preview_index = index
        self.layer_slider.setValue(index)
        self.infill_combo.setCurrentIndex(index)
        self._update_layer_label(index)
        self.updating_selection = False
        self._request_preview()

    def _update_layer_label(self, index: int) -> None:
        if not self.session or not self.session.infill_files:
            self.layer_label.setText("Layer: -")
            return
        info = self.session.infill_files[index]
        preview_layer = self._preview_layer_key(info.filename)
        self.layer_label.setText(f"Layer: {preview_layer}")

    def _set_row_visible(
        self,
        label: QtWidgets.QWidget,
        field: QtWidgets.QWidget,
        visible: bool,
    ) -> None:
        label.setVisible(visible)
        field.setVisible(visible)

    def _preview_layer_key(self, filename: str) -> int:
        stem = os.path.splitext(filename)[0]
        digits = "".join(ch for ch in stem if ch.isdigit())
        if len(digits) <= 2:
            return int(digits) if digits else 0
        return int(digits[:-2])

    def _object_id_from_filename(self, filename: str) -> int:
        stem = os.path.splitext(filename)[0]
        digits = "".join(ch for ch in stem if ch.isdigit())
        if not digits:
            return -1
        if len(digits) < 2:
            return int(digits)
        return int(digits[-2])

    def _update_strategy_controls(self) -> None:
        micro = self.micro_combo.currentText()
        self._set_row_visible(self.ghost_lag_label, self.ghost_lag_spin, micro == "Ghost Beam")
        self._set_row_visible(self.spot_skip_label, self.spot_skip_spin, micro == "Spot Ordered")
        self._set_row_visible(
            self.hilbert_order_label,
            self.hilbert_order_spin,
            micro in ("Hilbert-Kurve", "Peano-Kurve"),
        )
        self._set_row_visible(self.spiral_dir_label, self.spiral_dir_combo, micro == "Spiral")
        self._set_row_visible(
            self.greedy_memory_label,
            self.greedy_memory_spin,
            micro in ("Greedy (Nächster Nachbar)", "Dispersions-Maximum"),
        )
        self._set_row_visible(
            self.greedy_w2_label,
            self.greedy_w2_spin,
            micro in ("Greedy (Nächster Nachbar)", "Dispersions-Maximum"),
        )
        self._set_row_visible(
            self.grid_cell_label,
            self.grid_cell_spin,
            micro
            in (
                "Gitter-Dispersion (deterministisch)",
                "Gitter-Dispersion (stochastisch)",
                "Dichte-adaptiv",
            ),
        )
        self._set_row_visible(
            self.interlace_forward_label,
            self.interlace_forward_spin,
            micro == "Verschachtelte Streifen",
        )
        self._set_row_visible(
            self.interlace_backward_label,
            self.interlace_backward_spin,
            micro == "Verschachtelte Streifen",
        )

        seg = self.segmentation_combo.currentText()
        enable_seg = seg != "Keine Segmentierung"
        self._set_row_visible(self.seg_size_label, self.seg_size_spin, enable_seg)
        self._set_row_visible(self.seg_overlap_label, self.seg_overlap_spin, enable_seg)
        self._set_row_visible(self.seg_order_label, self.seg_order_combo, enable_seg)

    def _collect_params(self) -> dict:
        return {
            "segmentation": self.segmentation_combo.currentText(),
            "seg_size": float(self.seg_size_spin.value()),
            "seg_overlap": float(self.seg_overlap_spin.value()),
            "seg_order": self.seg_order_combo.currentText(),
            "micro_strategy": self.micro_combo.currentText(),
            "hatch_spacing": float(self.hatch_spacing_spin.value()),
            "rotation_angle_deg": float(self.rotation_spin.value()),
            "ghost_lag": float(self.ghost_lag_spin.value()),
            "spot_skip": int(self.spot_skip_spin.value()),
            "hilbert_order": int(self.hilbert_order_spin.value()),
            "spiral_direction": self.spiral_dir_combo.currentText(),
            "greedy_memory": int(self.greedy_memory_spin.value()),
            "greedy_w2": float(self.greedy_w2_spin.value()),
            "grid_cell_size": float(self.grid_cell_spin.value()),
            "interlace_forward": int(self.interlace_forward_spin.value()),
            "interlace_backward": int(self.interlace_backward_spin.value()),
            "point_spacing": 100.0,
        }

    def _request_preview(self) -> None:
        if self.preview_worker_active:
            self.preview_pending = True
            return
        if not self.session or not self.session.infill_files:
            return

        self.preview_status.setText("Vorschau wird berechnet...")
        self.preview_progress.setRange(0, 0)
        self.preview_progress.setValue(0)

        info = self.session.infill_files[self.current_preview_index]
        if not self.layer_index_map:
            self.layer_order = sorted(
                {self._preview_layer_key(item.filename) for item in self.session.b99_files}
            )
            self.layer_index_map = {layer: idx for idx, layer in enumerate(self.layer_order)}
        selected_preview_layer = self._preview_layer_key(info.filename)
        selected_layer_index = self.layer_index_map.get(selected_preview_layer, 0)
        preview_infos = [
            item
            for item in self.session.b99_files
            if self.layer_index_map.get(self._preview_layer_key(item.filename), 0)
            <= selected_layer_index
        ]
        params = self._collect_params()
        max_points = int(self.max_points_spin.value())
        mode = self.preview_mode_combo.currentText()
        use_reordered = self.reordered_check.isChecked()

        self.preview_worker_active = True
        worker = Worker(
            self._compute_preview_data,
            preview_infos,
            selected_preview_layer,
            self.layer_index_map,
            self.session.cutoff_layer,
            params,
            max_points,
            mode,
            use_reordered,
        )
        worker.signals.result.connect(self._apply_preview_data)
        worker.signals.error.connect(self._preview_error)
        worker.signals.finished.connect(self._preview_finished)
        self.thread_pool.start(worker)

    def _compute_preview_data(
        self,
        preview_infos,
        selected_preview_layer: int,
        layer_index_map: dict,
        cutoff_layer: int,
        params,
        max_points: int,
        mode: str,
        use_reordered: bool,
    ) -> dict:
        if not preview_infos:
            return {
                "points_xyz": np.zeros((0, 3), dtype=np.float32),
                "color_values": np.zeros((0,), dtype=np.float32),
                "alpha_values": np.zeros((0,), dtype=np.float32),
                "path_xyz": None,
                "path_color_values": None,
                "boundary_xyz": None,
                "display_points": 0,
                "total_points": 0,
                "layer_count": 0,
                "mode": mode,
            }

        points_xyz_list = []
        color_values_list = []
        alpha_values_list = []
        path_xyz = None
        path_color_values = None
        boundary_xyz = None
        total_points = 0

        layer_groups = {}
        for info in preview_infos:
            layer_key = self._preview_layer_key(info.filename)
            layer_groups.setdefault(layer_key, []).append(info)

        layer_count = len(layer_groups)
        per_layer_max = max(50, max_points)

        for layer_key in sorted(layer_groups):
            layer_infos = layer_groups[layer_key]
            layer_points_list = []
            path_points_list = []

            for info in layer_infos:
                points_mm = read_points_mm(info.path)
                if points_mm.size == 0:
                    continue

                should_reorder = (
                    use_reordered
                    and info.classification in ("infill_even", "infill_9")
                    and info.layer >= cutoff_layer
                )
                if should_reorder:
                    points_mm = reorder_points(points_mm, params, info.layer)

                layer_points_list.append(points_mm)

                if info.classification in ("infill_even", "infill_9"):
                    path_points_list.append(points_mm)

            if not layer_points_list:
                continue

            layer_points = np.vstack(layer_points_list)
            total_points += len(layer_points)
            if len(layer_points) <= per_layer_max:
                display_pts = layer_points.astype(np.float32)
            else:
                rng = np.random.default_rng(layer_key)
                indices = rng.choice(len(layer_points), size=per_layer_max, replace=False)
                display_pts = layer_points[indices].astype(np.float32)
            layer_idx = layer_index_map.get(layer_key, 0)
            z_val = layer_idx * LAYER_HEIGHT_MM
            z_col = np.full((display_pts.shape[0], 1), z_val, dtype=np.float32)
            points_xyz = np.hstack([display_pts, z_col])

            color_values = np.linspace(0.0, 1.0, len(points_xyz), dtype=np.float32)
            alpha = 0.9 if layer_key == selected_preview_layer else 0.25
            alpha_values = np.full(len(points_xyz), alpha, dtype=np.float32)

            points_xyz_list.append(points_xyz)
            color_values_list.append(color_values)
            alpha_values_list.append(alpha_values)

            if layer_key == selected_preview_layer and mode in ("Linien", "Beides"):
                if path_points_list:
                    path_points = np.vstack(path_points_list)
                    path_step = max(1, len(path_points) // per_layer_max)
                    path_display = path_points[::path_step].astype(np.float32)
                    path_z = np.full((path_display.shape[0], 1), z_val, dtype=np.float32)
                    path_xyz = np.hstack([path_display, path_z])
                    path_color_values = np.linspace(0.0, 1.0, len(path_xyz), dtype=np.float32)

            if layer_key == selected_preview_layer:
                contour_groups = {}
                for info in layer_infos:
                    if info.classification != "contour":
                        continue
                    obj_id = self._object_id_from_filename(info.filename)
                    contour_groups.setdefault(obj_id, []).append(info)

                boundary_segments = []
                for obj_id, contour_infos in contour_groups.items():
                    contour_points = []
                    for contour_info in contour_infos:
                        contour_points.append(read_points_mm(contour_info.path))
                    if not contour_points:
                        continue
                    contour_points_mm = np.vstack(contour_points)
                    polygon = MultiPoint(contour_points_mm).convex_hull
                    if polygon.geom_type != "Polygon" or polygon.is_empty:
                        continue
                    bx, by = polygon.exterior.xy
                    segment = np.column_stack(
                        [
                            np.asarray(bx, dtype=np.float32),
                            np.asarray(by, dtype=np.float32),
                            np.full(len(bx), z_val, dtype=np.float32),
                        ]
                    )
                    boundary_segments.append(segment)

                if boundary_segments:
                    separator = np.array([[np.nan, np.nan, np.nan]], dtype=np.float32)
                    boundary_xyz = np.vstack(
                        [seg if idx == len(boundary_segments) - 1 else np.vstack([seg, separator])
                         for idx, seg in enumerate(boundary_segments)]
                    )

        if not points_xyz_list:
            return {
                "points_xyz": np.zeros((0, 3), dtype=np.float32),
                "color_values": np.zeros((0,), dtype=np.float32),
                "alpha_values": np.zeros((0,), dtype=np.float32),
                "path_xyz": None,
                "path_color_values": None,
                "boundary_xyz": None,
                "display_points": 0,
                "total_points": total_points,
                "layer_count": layer_count,
                "mode": mode,
            }

        points_xyz = np.vstack(points_xyz_list)
        color_values = np.concatenate(color_values_list)
        alpha_values = np.concatenate(alpha_values_list)

        return {
            "points_xyz": points_xyz,
            "color_values": color_values,
            "alpha_values": alpha_values,
            "path_xyz": path_xyz,
            "path_color_values": path_color_values,
            "boundary_xyz": boundary_xyz,
            "display_points": len(points_xyz),
            "total_points": total_points,
            "layer_count": layer_count,
            "mode": mode,
        }

    def _apply_preview_data(self, data: dict) -> None:
        points_xyz = data["points_xyz"]
        color_values = data["color_values"]
        alpha_values = data.get("alpha_values")
        path_xyz = data["path_xyz"]
        path_color_values = data.get("path_color_values")
        boundary_xyz = data["boundary_xyz"]
        mode = data["mode"]

        mapped = self.preview_canvas.colormap.map(color_values)
        point_colors = np.asarray(getattr(mapped, "rgba", mapped), dtype=np.float32)
        if alpha_values is not None and len(alpha_values) == len(point_colors):
            point_colors[:, 3] = point_colors[:, 3] * alpha_values

        path_colors = None
        if path_xyz is not None and path_color_values is not None:
            mapped_path = self.preview_canvas.colormap.map(path_color_values)
            path_colors = np.asarray(getattr(mapped_path, "rgba", mapped_path), dtype=np.float32)

        show_points = mode in ("Punkte", "Beides")
        show_path = mode in ("Linien", "Beides")

        self.preview_canvas.update_preview(
            points_xyz=points_xyz,
            point_colors=point_colors,
            path_xyz=path_xyz,
            path_colors=path_colors,
            boundary_xyz=boundary_xyz,
            show_points=show_points,
            show_path=show_path,
        )

        total = data["total_points"]
        display_points = data["display_points"]
        layer_count = data["layer_count"]
        self.preview_progress.setRange(0, 100)
        self.preview_progress.setValue(100)
        self.preview_status.setText(
            f"Vorschau geladen: {layer_count} Layer, {display_points} Punkte"
        )
        self.status_bar.showMessage(
            f"Vorschau: {layer_count} Layer, {display_points} Punkte (gesamt {total})"
        )

    def _preview_error(self, message: str) -> None:
        self.preview_progress.setRange(0, 100)
        self.preview_progress.setValue(0)
        self.preview_status.setText(f"Vorschau-Fehler: {message}")
        self.status_bar.showMessage(f"Vorschau-Fehler: {message}")

    def _preview_finished(self) -> None:
        self.preview_worker_active = False
        if self.preview_pending:
            self.preview_pending = False
            self._request_preview()

    def _run_export(self) -> None:
        if not self.session or not self.session.infill_files:
            self.status_bar.showMessage("Keine Infill-Dateien gefunden")
            return

        params = self._collect_params()
        output_dir = self.output_dir_edit.text().strip()
        if not output_dir:
            self.status_bar.showMessage("Bitte Ausgabeordner setzen")
            return

        self.export_button.setEnabled(False)
        self.load_button.setEnabled(False)
        self.output_dir_button.setEnabled(False)
        self.output_dir_edit.setEnabled(False)
        self.progress_bar.setValue(0)
        self.export_status.setText("Verarbeite Infill-Dateien...")

        worker = Worker(self._export_job, params, output_dir)
        worker.progress_callback = worker.signals.progress.emit
        worker.signals.progress.connect(self.progress_bar.setValue)
        worker.signals.result.connect(self._export_finished)
        worker.signals.error.connect(self._export_error)
        worker.signals.finished.connect(lambda: self.export_button.setEnabled(True))
        worker.signals.finished.connect(lambda: self.load_button.setEnabled(True))
        worker.signals.finished.connect(lambda: self.output_dir_button.setEnabled(True))
        worker.signals.finished.connect(lambda: self.output_dir_edit.setEnabled(True))
        self.thread_pool.start(worker)

    def _export_job(self, params: dict, output_dir: str, progress_callback=None) -> dict:
        if not self.session:
            return {"errors": ["Keine Session"], "out_zip": ""}

        def progress_cb(current: int, total: int) -> None:
            if progress_callback is None:
                return
            value = int((current / total) * 100) if total else 0
            progress_callback(value)

        errors = process_infill_files(self.session.infill_files, params, progress_cb=progress_cb)

        base_name = os.path.splitext(os.path.basename(self.session.zip_path))[0]
        out_zip = export_zip(self.session.extract_dir, output_dir, base_name)

        return {"errors": errors, "out_zip": out_zip}

    def _export_finished(self, result: dict) -> None:
        errors = result.get("errors", [])
        out_zip = result.get("out_zip", "")
        if errors:
            self.export_status.setText(f"{len(errors)} Fehler beim Verarbeiten")
        else:
            self.export_status.setText(f"Export OK: {out_zip}")
        self.status_bar.showMessage("Export abgeschlossen")

    def _export_error(self, message: str) -> None:
        self.export_status.setText(f"Export-Fehler: {message}")
        self.status_bar.showMessage("Export-Fehler")

    def closeEvent(self, event) -> None:
        if self.session:
            self.session.cleanup()
        super().closeEvent(event)


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
