# HYPSORA

**Computational Terrain Visualization**

HYPSORA is a terminal-driven Python tool for visualizing regional digital elevation models (DEMs) as three-dimensional terrain surfaces. It reads an elevation GeoTIFF, samples a user-selected geographic region, and plots the terrain with optional vertical exaggeration.

The program prompts for all run-specific settings. No input file, geographic region, output resolution, elevation unit, or vertical exaggeration is hard-coded.

## Requirements

- Python 3
- A geographic-coordinate (latitude/longitude) elevation GeoTIFF
- Python packages: `numpy`, `rasterio`, `matplotlib`, and `pyproj`

Install the dependencies:

```bash
python3 -m pip install numpy rasterio matplotlib pyproj
```

> Depending on your Python installation, you may prefer to create and activate a virtual environment before installing packages.

## Getting started

1. Download `hypsora.py` from this repository and save it on your computer.
2. Open Terminal (macOS/Linux) or a terminal in Windows.
3. Navigate to the directory containing the script:

   ```bash
   cd /path/to/your/folder
   ```

4. Start HYPSORA:

   ```bash
   python3 hypsora.py
   ```

5. Respond to the prompts:
   - **Path to elevation GeoTIFF:** the location of your DEM file.
   - **South / north latitude:** the geographic extent to display, in decimal degrees.
   - **West / east longitude:** the geographic extent to display, in decimal degrees.
   - **Maximum output grid dimension:** a number from 50 to 3000; smaller values generally render faster.
   - **Vertical exaggeration:** `1` for no exaggeration, or a larger positive value to emphasize relief.
   - **Elevation unit:** `m`, `km`, or `ft`, matching the source data.

6. HYPSORA prints information about the selected dataset and region, then opens a Matplotlib window containing the 3D terrain visualization. Use Matplotlib's interactive controls to rotate and inspect the plot.

## Example inputs

These values are **illustrative**. Choose bounds that overlap your own GeoTIFF, and confirm its elevation units.

```text
Path to elevation GeoTIFF: /path/to/elevation.tif
South latitude: 37.4139
North latitude: 37.4417
West longitude: -122.1836
East longitude: -122.1558
Maximum output grid dimension (50–3000; lower is faster): 300
Vertical exaggeration (1 means unexaggerated): 2
Elevation unit in source data (m, km, or ft): m
```

## How it works

HYPSORA uses Rasterio to read and resample the selected region of a DEM. It uses the geodetic model associated with the raster's coordinate reference system to estimate east–west and north–south distances from the region center. Elevations are converted to kilometers, optionally exaggerated, and displayed as a colored 3D surface with Matplotlib.

## Current limitations

- Input must be a **north-up, unrotated geographic-coordinate raster** (latitude/longitude). Projected-coordinate rasters are not supported in this version.
- Regions crossing the international date line are not supported.
- The requested region must overlap the raster's coverage.
- Elevation units must be provided manually; supported units are meters, kilometers, and feet.
- The script displays an interactive plot but does not currently export a 3D model or image automatically.
- Large output grids can be slow to render.
- Planetary support depends on whether the input raster's coordinate reference system and geodetic model are supported by the underlying libraries; this version has not been validated for general planetary datasets.

## Files

- `hypsora.py` — HYPSORA's command-line terrain visualization script.

## License

No license has been specified for this repository.
