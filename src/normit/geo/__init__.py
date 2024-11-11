import geopandas
import matplotlib.pyplot as plt

from .ops import *


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
            # recover polygons inappropriately stored as MultiLineStrings
            if isinstance(geom, shapely.geometry.MultiLineString):
                polygons, cuts, dangles, invalid = shapely.polygonize_full(
                    shapely.get_parts(geom))
                if not cuts and not dangles and not invalid:
                    geom = shapely.multipolygons(shapely.get_parts(polygons))
            results.append(geom)
        return results[0] if len(results) == 1 else shapely.union_all(results)


