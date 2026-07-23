import numpy as np
import pyvista as pv
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely.prepared import prep

def slice_to_polygons(slice_mesh):
    """Turn the line loops from mesh.slice() into shapely polygons."""
    strip = slice_mesh.strip()  # merge segments into connected polylines
    pts = strip.points[:, :2]
    lines = strip.lines
    polygons = []
    i = 0
    while i < len(lines):
        n = lines[i]
        idx = lines[i + 1 : i + 1 + n]
        loop = pts[idx]
        if len(loop) >= 3:
            poly = Polygon(loop)
            if poly.is_valid and poly.area > 0:
                polygons.append(poly)
            elif not poly.is_valid:
                polygons.append(poly.buffer(0))  # fix self-intersections
        i += n + 1
    return unary_union(polygons)


from shapely.geometry import Point

def filter_filled_by_slice(filled, slice_mesh):
    poly = slice_to_polygons(slice_mesh)
    prepared = prep(poly)
    centers = filled.cell_centers().points[:, :2]
    mask = np.array([prepared.contains(Point(c)) for c in centers])
    return filled.extract_cells(np.where(mask)[0])

def slice_stl(input_filepath, height):
    mesh = pv.read(input_filepath)
    origin = (mesh.center[0], mesh.center[1], 0)

    slice1 = mesh.slice(normal=[0, 0, 1], origin=origin)
    filled = slice1.delaunay_2d(alpha=0.5)
    filled_clipped = filter_filled_by_slice(filled, slice1)

    pl = pv.Plotter()
    pl.add_mesh(filled_clipped)
    pl.add_mesh(slice1, color='black')
    pl.show()

slice_stl('data/missing_struts/stls/0.stl', 0)