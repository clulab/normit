import dataclasses
import pint
import pyproj
import pyproj.enums
import shapely
import shapely.affinity
import shapely.ops
import utm

UNITS = pint.UnitRegistry()


@dataclasses.dataclass
class GeoCardinal:
    azimuth: int

    def of(self,
           geometry: shapely.geometry.base.BaseGeometry,
           distance: pint.Quantity = None) -> shapely.Polygon:

        # start with the circle or ring defined by Near
        result = Near.to(geometry, distance)

        # create point at azimuth 0 (North) and rotate (negative = clockwise)
        radius = shapely.minimum_bounding_radius(result)
        c = geometry.centroid
        p = shapely.Point(c.x, c.y + radius * 1.5)
        p = shapely.affinity.rotate(p, -self.azimuth, origin=c)

        # construct a roughly sector-shaped polygon
        p45n = shapely.affinity.rotate(p, -45, origin=c)
        p45p = shapely.affinity.rotate(p, +45, origin=c)
        sector = shapely.convex_hull(shapely.MultiPoint([c, p45n, p, p45p]))

        # keep only the selected sector of the circle or ring
        return result.intersection(sector)

    def part_of(self, geometry: shapely.geometry.base.BaseGeometry):
        d = shapely.minimum_bounding_radius(geometry) * 2
        c = geometry.centroid
        # create point at azimuth 0 (North) and rotate (negative = clockwise)
        point = shapely.Point(c.x, c.y + d)
        point = shapely.affinity.rotate(point, -self.azimuth, origin=c)
        # find a line perpendicular to that point
        line = _line_through_centroid_perpendicular_to_point(geometry, point)
        # find the one-directional buffer of the chord that crosses the point
        buf1 = line.buffer(distance=d, single_sided=True, cap_style='flat')
        buf2 = line.buffer(distance=-d, single_sided=True, cap_style='flat')
        polygon = buf1 if buf1.intersection(point) else buf2
        # keep only the region that overlaps with the input
        return polygon.intersection(geometry)


North = GeoCardinal(azimuth=0)
NorthEast = GeoCardinal(azimuth=45)
East = GeoCardinal(azimuth=90)
SouthEast = GeoCardinal(azimuth=135)
South = GeoCardinal(azimuth=180)
SouthWest = GeoCardinal(azimuth=225)
West = GeoCardinal(azimuth=270)
NorthWest = GeoCardinal(azimuth=315)


class Near:
    @staticmethod
    def to(geometry: shapely.geometry.base.BaseGeometry,
           distance: pint.Quantity = None):
        # project to UTM where we can measure distance in meters
        lon = geometry.centroid.x
        lat = geometry.centroid.y
        utm_zone = utm.latlon_to_zone_number(lon, lat)
        proj = pyproj.Proj(proj='utm', zone=utm_zone, ellps='WGS84')
        geometry = shapely.ops.transform(proj, geometry)
        # for lines, use a default radius of 1km
        if geometry.area == 0.0:
            radius = 1000
        # for polygons, use the radius of the minimum bounding circle
        else:
            radius = shapely.minimum_bounding_radius(geometry)
        # if no distance is specified, buffer by one radius
        if distance is None:
            result = geometry.buffer(radius)
        # if a distance is specified, construct a ring-like buffer at a distance
        else:
            dist = max(0.0, distance.to(UNITS.meter).magnitude)
            result = (geometry.buffer(dist + radius) -
                      geometry.buffer(dist - radius))
        # remove any overlap with the original geometry
        result -= geometry
        # project back to latitude, longitude
        return shapely.ops.transform(lambda *args: proj(*args, inverse=True),
                                     result)


class Between:
    @staticmethod
    def of(geometry1: shapely.geometry.base.BaseGeometry,
           geometry2: shapely.geometry.base.BaseGeometry) -> shapely.Polygon:
        chord1 = _chord_perpendicular_to_point(geometry1, geometry2.centroid)
        chord2 = _chord_perpendicular_to_point(geometry2, geometry1.centroid)
        return chord1.union(chord2).convex_hull - geometry1 - geometry2


def _line_through_centroid_perpendicular_to_point(
        geometry: shapely.geometry.base.BaseGeometry,
        point: shapely.Point) -> shapely.LineString:
    # line through the centroid to the point, extending equally on either side
    start = shapely.affinity.rotate(point, angle=180, origin=geometry.centroid)
    line = shapely.LineString([start, point])
    # rotate the line to be perpendicular
    line = shapely.affinity.rotate(line, angle=90, origin=geometry.centroid)
    # extend the line past the geometry
    scale = line.length / (shapely.minimum_bounding_radius(geometry) * 2)
    return shapely.affinity.scale(line, xfact=scale, yfact=scale)


def _chord_perpendicular_to_point(geometry: shapely.geometry.base.BaseGeometry,
                                  point: shapely.Point) -> shapely.LineString:
    line = _line_through_centroid_perpendicular_to_point(geometry, point)
    # return only the portion of the line that intersects the input
    result = line.intersection(geometry)
    # if the line is discontinuous, take the longest piece
    if isinstance(result, shapely.MultiLineString):
        result = max(result.geoms, key=lambda g: g.length)
    return result