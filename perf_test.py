import time
from src.geometry import GeometryEngine
from src.strategies.raster import RasterStrategy
from src.exporter import B99Exporter
from src.strategies.base_strategy import ScanPath

print('Starting performance test for 20x20x20mm cube at 50um layer thickness (400 layers)')
start_time = time.time()

layers = GeometryEngine.create_cube_layers(20.0, 20.0, 20.0, 50.0)
gen_time = time.time()

print(f'Geometry Engine extracted {len(layers)} layers in {gen_time - start_time:.4f} seconds.')

all_paths = []
raster = RasterStrategy()

path_start = time.time()
for i, layer in enumerate(layers):
    p = raster.generate_path(layer, hatch_spacing=200.0, point_spacing=100.0, rotation_angle_deg=67.0 * i)
    all_paths.append(p)
path_end = time.time()

print(f'Raster Pathing completed in {path_end - path_start:.4f} seconds.')

exp_start = time.time()
b99_data = B99Exporter.generate_b99_content(all_paths)
exp_end = time.time()

print(f'Exporting formatted strings completed in {exp_end - exp_start:.4f} seconds.')
print(f'Total B99 string size: {len(b99_data) / 1024 / 1024:.2f} MB')
print(f'Total Process Time: {exp_end - start_time:.4f} seconds.')
