import shapely

from normit.geo import *


def test_reader(georeader: GeoJsonDirReader):
    # node
    kintbury = georeader.read(21517801)
    assert isinstance(kintbury, shapely.Point)

    # multipolygon stored as multiline string
    za = georeader.read(87565)
    assert isinstance(za, shapely.MultiPolygon)


def test_inner_regions(georeader: GeoJsonDirReader):
    india = georeader.read(304716)
    delhi = georeader.read(1942586)
    hyderabad = georeader.read(7868535)
    gorakhpur = georeader.read(1959872)

    # Delhi is in the North of India
    assert North.part_of(india).intersection(delhi).area > 0
    assert South.part_of(india).intersection(delhi).area == 0

    # Hyderabad is in the South of India
    assert North.part_of(india).intersection(hyderabad).area == 0
    assert South.part_of(india).intersection(hyderabad).area > 0

    # Gorakhpur is in the NorthEast of India
    assert NorthEast.part_of(india).intersection(gorakhpur).area > 0
    assert SouthWest.part_of(india).intersection(gorakhpur).area == 0

    # SouthWest part of a point is the point
    kintbury = georeader.read(21517801)
    assert SouthWest.part_of(kintbury) == kintbury


def test_outer_regions(georeader: GeoJsonDirReader):
    az = georeader.read(162018)
    ca = georeader.read(165475)
    co = georeader.read(161961)
    la = georeader.read(224922)
    mx = georeader.read(114686)
    nm = georeader.read(162014)
    nv = georeader.read(165473)
    ut = georeader.read(161993)

    assert Near.to(az).intersection(nm).area > 0.0

    # Utah is north of Arizona
    assert NorthWest.of(az).intersection(ut).area > 0
    assert North.of(az).intersection(ut).area > 0
    assert NorthEast.of(az).intersection(ut).area > 0
    assert East.of(az).intersection(ut).area == 0
    assert SouthEast.of(az).intersection(ut).area == 0
    assert South.of(az).intersection(ut).area == 0
    assert SouthWest.of(az).intersection(ut).area == 0
    assert West.of(az).intersection(ut).area == 0

    # Colorado is northeast of Arizona
    assert North.of(az).intersection(co).area > 0
    assert NorthEast.of(az).intersection(co).area > 0
    assert East.of(az).intersection(co).area > 0
    assert SouthEast.of(az).intersection(co).area == 0
    assert South.of(az).intersection(co).area == 0
    assert SouthWest.of(az).intersection(co).area == 0
    assert West.of(az).intersection(co).area == 0
    assert NorthWest.of(az).intersection(co).area == 0

    # New Mexico is east of Arizona
    assert NorthEast.of(az).intersection(nm).area > 0
    assert East.of(az).intersection(nm).area > 0
    assert SouthEast.of(az).intersection(nm).area > 0
    # assert South.of(az).intersection(nm).area == 0
    assert SouthWest.of(az).intersection(nm).area == 0
    assert West.of(az).intersection(nm).area == 0
    assert NorthWest.of(az).intersection(nm).area == 0
    # assert North.of(az).intersection(nm).area == 0

    # Mexico is southeast, south, and southwest of Arizona
    assert East.of(az).intersection(mx).area > 0
    assert SouthEast.of(az).intersection(mx).area > 0
    assert South.of(az).intersection(mx).area > 0
    assert SouthWest.of(az).intersection(mx).area > 0
    assert West.of(az).intersection(mx).area > 0
    assert NorthWest.of(az).intersection(mx).area == 0
    assert North.of(az).intersection(mx).area == 0
    assert NorthEast.of(az).intersection(mx).area == 0

    # California is west of Arizona
    assert SouthWest.of(az).intersection(ca).area > 0
    assert West.of(az).intersection(ca).area > 0
    assert NorthWest.of(az).intersection(ca).area > 0
    assert North.of(az).intersection(ca).area == 0
    assert NorthEast.of(az).intersection(ca).area == 0
    assert East.of(az).intersection(ca).area == 0
    assert SouthEast.of(az).intersection(ca).area == 0
    assert South.of(az).intersection(ca).area == 0

    # Nevada is northwest of Arizona
    assert West.of(az).intersection(nv).area > 0
    assert NorthWest.of(az).intersection(nv).area > 0
    assert North.of(az).intersection(nv).area > 0
    assert NorthEast.of(az).intersection(nv).area == 0
    assert East.of(az).intersection(nv).area == 0
    assert SouthEast.of(az).intersection(nv).area == 0
    assert South.of(az).intersection(nv).area == 0
    assert SouthWest.of(az).intersection(nv).area == 0

    # Louisiana is not adjacent to Arizona
    assert Near.to(az).intersection(la).area == 0.0

    # the Colorado River is not near Albuquerque
    colorado_river = georeader.read(2718127)
    albuquerque = georeader.read(171262)
    assert Near.to(colorado_river).intersection(albuquerque).area == 0


def test_distance(georeader: GeoJsonDirReader):
    de = georeader.read(51477)
    fr = georeader.read(1403916)  # "Metropolitan France" not the territories
    es = georeader.read(1311341)

    # Near should not overlap the original polygon
    assert Near.to(de).intersection(de).area == 0
    assert Near.to(fr).intersection(fr).area == 0
    assert Near.to(es).intersection(es).area == 0

    # Near should not overlap
    assert Near.to(de, distance=1 * UNITS.km).intersection(de).area == 0
    assert Near.to(fr, distance=10 * UNITS.km).intersection(fr).area == 0
    assert Near.to(es, distance=100 * UNITS.km).intersection(es).area == 0

    # Spain is southwest of Germany, across France
    fr_diameter = 1000 * UNITS.km
    assert Near.to(de, distance=fr_diameter).intersection(es).area > 0.0
    assert SouthWest.of(de, distance=fr_diameter).intersection(es).area > 0.0
    assert Near.to(es, distance=fr_diameter).intersection(de).area > 0.0
    assert NorthEast.of(es, distance=fr_diameter).intersection(de).area > 0.0


def test_between(georeader: GeoJsonDirReader):
    na = georeader.read(195266)  # Namibia
    bw = georeader.read(1889339)  # Botswana
    zw = georeader.read(195272)  # Zimbabwe
    za = georeader.read(87565)  # South Africa
    za_ru = georeader.read(30391973) # Rustenburg (a Point) in South Africa

    # Botswana is between Namibia and Zimbabwe
    assert Between.of(na, zw).intersection(bw).area > 0
    assert Between.of(zw, na).intersection(bw).area > 0
    assert Between.of(na, bw).intersection(zw).area == 0
    assert Between.of(bw, na).intersection(zw).area == 0

    # Botswana is between Namibia and South Africa
    assert Between.of(na, za).intersection(bw).area > 0
    assert Between.of(za, na).intersection(bw).area > 0
    assert Between.of(na, za_ru).intersection(bw).area > 0
    assert Between.of(za_ru, na).intersection(bw).area > 0

    # Namibia is not between South Africa and Zimbabwe
    assert Between.of(za, zw).intersection(na).area == 0
    assert Between.of(zw, za).intersection(na).area == 0


def test_union_intersection(georeader: GeoJsonDirReader):
    jp = georeader.read(382313)  # Japan
    os = georeader.read(358674)  # Osaka
    kr = georeader.read(307756)  # South Korea
    se = georeader.read(2297418)  # Seoul

    assert Intersection.of(jp, kr).area == 0
    assert shapely.equals(Intersection.of(jp, os), os)
    assert shapely.equals(Intersection.of(kr, se), se)

    assert shapely.equals(Union.of(jp, kr).intersection(jp), jp)
    assert shapely.equals(Union.of(jp, kr).intersection(kr), kr)
