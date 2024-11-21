"""
The normit.geo module provides utilities for normalizing geographical
expressions in text.
"""

import geopandas
import matplotlib.pyplot as plt
import shapely.geometry

from .ops import *  # noqa: F401


__all__ = ops.__all__ + ['show_plot', 'GeoJsonDirReader']
for _name in ops.__all__:
    _obj = globals()[_name]
    if hasattr(_obj, "__module__"):
        _obj.__module__ = __name__


_PolygonLike = shapely.geometry.Polygon | shapely.geometry.MultiPolygon


def show_plot(*geometries: shapely.geometry.base.BaseGeometry):
    gdf = geopandas.GeoDataFrame(geometry=list(geometries), crs='EPSG:4326')
    color_list = plt.rcParams['axes.prop_cycle'].by_key()['color']
    gdf.plot(color=color_list, aspect='equal')
    plt.show()


class GeoJsonDirReader:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir

    def read(self, *osms) -> shapely.geometry.base.BaseGeometry:
        results = []
        for osm in osms:
            with open(f"{self.root_dir}/{str(osm)[:2]}/{osm}") as f:
                collection = shapely.from_geojson(f.read())
            [geom] = collection.geoms
            # recover polygons inappropriately stored as line strings
            if not isinstance(geom, _PolygonLike):
                polygons, cuts, dangles, invalid = shapely.polygonize_full(
                    shapely.get_parts(geom))
                if not cuts and not dangles and not invalid:
                    geom = shapely.multipolygons(shapely.get_parts(polygons))
            results.append(geom)
        # skip the unnecessary union if there's only one result
        match results:
            case [geom]:
                return geom
            case geoms:
                return shapely.union_all(geoms)
