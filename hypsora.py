#!/usr/bin/env python3
"""HYPSORA — terminal-driven regional digital elevation model (DEM) viewer.

Prompts for every run-specific input; no file path, geographic region, display
resolution, elevation unit, or vertical exaggeration is assumed.

Dependencies: rasterio, numpy, matplotlib, pyproj.
"""

from pathlib import Path
import sys
import math

import numpy as np
import rasterio
from pyproj import CRS
from rasterio.windows import from_bounds, Window
from rasterio.enums import Resampling
import matplotlib.pyplot as plt
from matplotlib import cm, colors


def ask_text(prompt):
    while True:
        answer = input(f"{prompt}: ").strip()
        if answer:
            return answer
        print("A value is required.")


def ask_float(prompt, validator, message):
    while True:
        try:
            value = float(ask_text(prompt))
            if math.isfinite(value) and validator(value):
                return value
        except ValueError:
            pass
        print(message)


def ask_int(prompt, minimum, maximum):
    while True:
        try:
            value = int(ask_text(prompt))
            if minimum <= value <= maximum:
                return value
        except ValueError:
            pass
        print(f"Enter a whole number from {minimum} to {maximum}.")


def get_region():
    print("\nEnter geographic bounds in decimal degrees.")
    print("Latitude: south/north in [-90, 90]; longitude: west/east in [-180, 180].")
    while True:
        south = ask_float("South latitude", lambda v: -90 <= v <= 90, "Latitude must be between -90 and 90.")
        north = ask_float("North latitude", lambda v: -90 <= v <= 90, "Latitude must be between -90 and 90.")
        west = ask_float("West longitude", lambda v: -180 <= v <= 180, "Longitude must be between -180 and 180.")
        east = ask_float("East longitude", lambda v: -180 <= v <= 180, "Longitude must be between -180 and 180.")
        if south < north and west < east:
            return south, north, west, east
        print("Bounds must satisfy south < north and west < east. Regions crossing the date line are not supported by this version.\n")


def main():
    print("=" * 58)
    print("HYPSORA — REGIONAL TERRAIN VIEWER")
    print("=" * 58)

    dem_path = Path(ask_text("Path to elevation GeoTIFF")).expanduser()
    if not dem_path.is_file():
        print(f"\nFile not found: {dem_path}")
        return 1

    south, north, west, east = get_region()
    max_dimension = ask_int("Maximum output grid dimension (50–3000; lower is faster)", 50, 3000)
    vertical_exaggeration = ask_float(
        "Vertical exaggeration (1 means unexaggerated)",
        lambda v: v > 0,
        "Enter a finite value greater than zero.",
    )
    unit_text = ask_text("Elevation unit in source data (m, km, or ft)").lower()
    unit_to_km = {"m": 0.001, "km": 1.0, "ft": 0.0003048}
    if unit_text not in unit_to_km:
        print("Unsupported elevation unit. Enter m, km, or ft.")
        return 1

    try:
        with rasterio.open(dem_path) as src:
            print("\nDataset information")
            print(f"  CRS: {src.crs}")
            print(f"  Raster size: {src.width:,} × {src.height:,} pixels")
            print(f"  Bounds: {src.bounds}")
            print(f"  Resolution: {src.res}")

            if src.crs is None or not src.crs.is_geographic:
                print("\nThis version requires a geographic-coordinate raster (latitude/longitude).")
                return 1
            if src.transform.b != 0 or src.transform.d != 0 or src.transform.a <= 0 or src.transform.e >= 0:
                print("\nThis version requires a north-up raster with no rotation.")
                return 1

            overlap_west = max(west, src.bounds.left)
            overlap_east = min(east, src.bounds.right)
            overlap_south = max(south, src.bounds.bottom)
            overlap_north = min(north, src.bounds.top)
            if overlap_west >= overlap_east or overlap_south >= overlap_north:
                print("\nThe requested region does not overlap this raster's coverage.")
                return 1
            if (overlap_west, overlap_east, overlap_south, overlap_north) != (west, east, south, north):
                print("\nNote: requested bounds extend beyond the raster; only available coverage will be shown.")

            window = from_bounds(overlap_west, overlap_south, overlap_east, overlap_north, src.transform)
            window = window.round_offsets().round_lengths()
            window = window.intersection(Window(0, 0, src.width, src.height))
            if window.width < 2 or window.height < 2:
                print("\nSelected region is too small to render. Increase the bounds.")
                return 1

            scale = min(1.0, max_dimension / max(window.width, window.height))
            out_width = max(2, int(round(window.width * scale)))
            out_height = max(2, int(round(window.height * scale)))
            elevation = src.read(
                1,
                window=window,
                out_shape=(out_height, out_width),
                masked=True,
                resampling=Resampling.bilinear,
            ).astype(np.float32)
            transform = src.window_transform(window)
            x_res = transform.a * window.width / out_width
            y_res = transform.e * window.height / out_height
            longitudes = transform.c + (np.arange(out_width) + 0.5) * x_res
            latitudes = transform.f + (np.arange(out_height) + 0.5) * y_res
            lon_grid, lat_grid = np.meshgrid(longitudes, latitudes)

            data = np.asarray(elevation.filled(np.nan), dtype=np.float32)
            valid = np.isfinite(data)
            if src.nodata is not None:
                valid &= data != src.nodata
            if not np.any(valid):
                print("\nNo valid elevation samples found in that region.")
                return 1
            values = data[valid]
            print("\nRegion read successfully")
            print(f"  Sample grid: {out_width:,} × {out_height:,}")
            print(f"  Valid samples: {values.size:,} / {data.size:,}")
            print(f"  Elevation range: {values.min():.3f} to {values.max():.3f} {unit_text}")
            print(f"  Mean elevation: {values.mean():.3f} {unit_text}")
            geod = CRS.from_user_input(src.crs).get_geod()

    except Exception as exc:
        print(f"\nCould not read the dataset: {exc}")
        return 1

    # Convert each grid point to distances from the region's geographic center
    # using the ellipsoid associated with the input CRS, rather than a fixed radius.
    center_lon = (overlap_west + overlap_east) / 2.0
    center_lat = (overlap_south + overlap_north) / 2.0
    center_lons = np.full(lon_grid.shape, center_lon, dtype=np.float64)
    center_lats = np.full(lat_grid.shape, center_lat, dtype=np.float64)
    azimuth, _, distance_m = geod.inv(center_lons, center_lats, lon_grid, lat_grid)
    azimuth_rad = np.radians(azimuth)
    distance_km = distance_m / 1000.0
    x_km = distance_km * np.sin(azimuth_rad)
    y_km = distance_km * np.cos(azimuth_rad)
    z_km = data * unit_to_km[unit_text] * vertical_exaggeration

    x_plot = np.ma.array(x_km, mask=~valid)
    y_plot = np.ma.array(y_km, mask=~valid)
    z_plot = np.ma.array(z_km, mask=~valid)

    fig = plt.figure(figsize=(12, 8), facecolor="#101318")
    ax = fig.add_subplot(111, projection="3d", facecolor="#101318")
    cmap = cm.terrain.copy()
    cmap.set_bad((0, 0, 0, 0))
    low, high = float(values.min()), float(values.max())
    if high <= low:
        high = low + 1.0
    norm = colors.Normalize(vmin=low, vmax=high)
    facecolors = cmap(norm(np.ma.array(data, mask=~valid)))
    ax.plot_surface(
        x_plot, y_plot, z_plot,
        facecolors=facecolors,
        rstride=1, cstride=1,
        linewidth=0, antialiased=True, shade=False,
    )
    ax.set_title(
        f"Regional Terrain: {dem_path.name}\n"
        f"Lat {overlap_south:.5f}° to {overlap_north:.5f}°, "
        f"lon {overlap_west:.5f}° to {overlap_east:.5f}°",
        color="white", pad=18,
    )
    ax.set_xlabel("East–West distance (km)", color="white", labelpad=10)
    ax.set_ylabel("North–South distance (km)", color="white", labelpad=10)
    ax.set_zlabel(f"Elevation (km; exaggeration ×{vertical_exaggeration:g})", color="white", labelpad=10)
    ax.tick_params(colors="#d0d0d0")
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_facecolor((0.06, 0.07, 0.09, 1.0))
    ax.view_init(elev=35, azim=-125)
    x_span = float(np.nanmax(x_km) - np.nanmin(x_km))
    y_span = float(np.nanmax(y_km) - np.nanmin(y_km))
    z_span = float(np.nanmax(z_km[valid]) - np.nanmin(z_km[valid]))
    ax.set_box_aspect((max(x_span, 1e-6), max(y_span, 1e-6), max(z_span, 1e-6)))
    fig.tight_layout()
    plt.show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
