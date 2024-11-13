import shapely.geometry.base

from normit.geo import *


def plot(reference: shapely.geometry.base.BaseGeometry,
         prediction: shapely.geometry.base.BaseGeometry,
         prediction_parts: list[shapely.geometry.base.BaseGeometry]):
    geometries = [reference, prediction] + prediction_parts
    gdf = geopandas.GeoDataFrame(geometry=geometries, crs='EPSG:4326')
    ax = gdf.iloc[2:].plot(cmap='tab10', aspect='equal', alpha=0.5)
    gdf.iloc[0:1].plot(ax=ax, facecolor='none', edgecolor='blue')
    if prediction.area:
        gdf.iloc[1:2].plot(ax=ax, facecolor='none', edgecolor='red')
    plt.show()


def test_oseetah_lake(georeader: GeoJsonDirReader, score_logger, request):
    # Oseetah Lake [osm r 7931454]
    # is an 826-acre (3.34&#160;km2) lake with a mean depth of three feet
    # (0.91 m).[1] It is in
    # New York State [osm r 61320]'s
    # Adirondack Park [osm r 1695394],
    # two and a half miles (4.0 km) south of the village of
    # Saranac Lake [osm n r 158836364 176209] on the
    # Saranac River [osm w w w r 138999640 138999641 605606940 7400653].
    # It is located mostly in the town of
    # Harrietstown [osm n 158896350],
    # but its easternmost portion extends into the town of
    # North Elba [osm n 158852414].
    oseetah_lake = georeader.read(7931454)
    new_york_state = georeader.read(61320)
    adirondack_park = georeader.read(1695394)
    saranac_lake = georeader.read(158836364, 176209)
    saranac_river = georeader.read(138999640, 138999641, 605606940, 7400653)
    # skip the node-only geometries, since they're not usable
    # harrietstown = georeader.read(158896350)
    # north_elba = georeader.read(158852414)

    prediction_parts = [
        new_york_state,
        adirondack_park,
        South.of(saranac_lake, distance=4 * UNITS.km),
        Near.to(saranac_river),
    ]
    prediction = Intersection.of(*prediction_parts)
    p, r, f1 = score_logger.p_r_f1(oseetah_lake, prediction, request)
    assert f1 > .2, plot(oseetah_lake, prediction, prediction_parts)


def test_jincheon_county(georeader: GeoJsonDirReader, score_logger, request):
    # Jincheon [osm n r 415157745 2538513]
    # belongs to the middle of
    # Chungcheongbuk-do [osm n r 1895837469 2327258].
    # It borders several cities of its province but also meets
    # Gyeonggi-do [n r 1850580646 2306392]
    # The southwestern part of this area is mountainous.
    jincheon_jounty = georeader.read(415157745, 2538513)
    chungcheongbuk_do = georeader.read(1895837469, 2327258)
    gyeonggi_do = georeader.read(1850580646, 2306392)

    prediction_parts = [
        chungcheongbuk_do,
        Near.to(gyeonggi_do),
    ]
    prediction = Intersection.of(*prediction_parts)
    p, r, f1 = score_logger.p_r_f1(jincheon_jounty, prediction, request)
    # high recall + low precision because the tightest constraint is based on
    # the province, which is much larger than the county
    assert p > 0 and r > .9, plot(jincheon_jounty, prediction, prediction_parts)


def test_tikehau(georeader: GeoJsonDirReader, score_logger, request):
    # Tikehau [osm w r 139162465 6062940]
    # is located 340 kilometres (210 miles) northeast of
    # Tahiti [osm r 3992237]
    # in the
    # Tuamotu Islands [osm r 6065911].
    # The nearest atoll,
    # Rangiroa [osm w r 139157465 6062926],
    # lies only 12 kilometres (7.5 miles) to the east.
    # Mataiva [osm w r 138011339 6062918],
    # the westernmost atoll of the same group, is located 35 kilometres
    # (22 miles) to the west.
    tikehau = georeader.read(139162465, 6062940)
    tahiti = georeader.read(3992237)
    tuamotu_islands = georeader.read(6065911)
    rangiroa = georeader.read(139157465, 6062926)
    mataiva = georeader.read(6062918)  # local database is missing 138011339

    prediction_parts = [
        tuamotu_islands,
        NorthEast.of(tahiti, 340 * UNITS.km),
        West.of(rangiroa, 12 * UNITS.km),
        East.of(mataiva, 35 * UNITS.km),
    ]
    prediction = Intersection.of(*prediction_parts)
    p, r, f1 = score_logger.p_r_f1(tikehau, prediction, request)
    # high precision + low recall because constraints are based on Tuamotu
    # Islands, which is the landmass in OSM, while reference is Tikehau, which
    # includes the territorial waters in OSM
    assert p > .9 and r > 0, plot(tikehau, prediction, prediction_parts)


def test_gylen_castle(georeader: GeoJsonDirReader, score_logger, request):
    # Gylen Castle [osm w 275932847]
    # is a ruined castle, or tower house, at the south end of the island of
    # Kerrera [osm r 4092586]
    # in
    # Argyll and Bute [osm r 1775685],
    # Scotland, on a promontory overlooking the
    # Firth of Lorne [osm n 4805297529].
    # It was made a scheduled monument in 1931.
    gylen_castle = georeader.read(275932847)
    kerrera = georeader.read(4092586)
    argyll_and_bute = georeader.read(1775685)

    prediction_parts = [
        South.part_of(kerrera),
        argyll_and_bute
    ]
    prediction = Intersection.of(*prediction_parts)
    p, r, f1 = score_logger.p_r_f1(gylen_castle, prediction, request)
    # high recall + low precision because tightest constraint is based on the
    # island and the castle is tiny compared to the island
    assert p > 0 and r > .9, plot(gylen_castle, prediction, prediction_parts)


def test_bitburg(georeader: GeoJsonDirReader, score_logger, request):
    # Bitburg [osm n r 27377727 572813]
    # (German pronunciation: [&#712;b&#618;tb&#650;&#641;k];
    # French: Bitbourg; Luxembourgish: B&#233;ibreg) is a city in
    # Germany [osm n r r 1683325355 51477 62781],
    # in the state of
    # Rhineland-Palatinate [osm n r 519436857 62341]
    # approximately 25&#160;km (16&#160;mi.) northwest of
    # Trier [osm n r 31941291 172679]
    # and 50&#160;km (31&#160;mi.) northeast of
    # Luxembourg [osm n r 52943358 407489] city.
    # The American Spangdahlem Air Base [osm w 81974947] is nearby.
    bitburg = georeader.read(27377727, 572813)
    germany = georeader.read(1683325355, 51477, 62781)
    rhineland_palatinate = georeader.read(519436857, 62341)
    trier = georeader.read(31941291, 172679)
    luxembourg_city = georeader.read(52943358, 407489)
    spangdahlem_air_base = georeader.read(81974947)

    prediction_parts = [
        germany,
        rhineland_palatinate,
        NorthWest.of(trier, distance=25 * UNITS.km),
        NorthEast.of(luxembourg_city, distance=50 * UNITS.km),
        # skip the air base because the default size of Near.to is twice the
        # radius of the base, which will be too small
        # Near.to(spangdahlem_air_base),
    ]
    prediction = Intersection.of(*prediction_parts)
    p, r, f1 = score_logger.p_r_f1(bitburg, prediction, request)
    assert f1 > .1, plot(bitburg, prediction, prediction_parts)


# <entity id="GL543_093" wikipedia="St_George's_Hanover_Square_Church" osm="38310265" type="way" status="5">
#       <p id="GL543_093_001" num_links="5">St George's Hanover Square Church is an Anglican church in the <link id="GL543_093_001_001" wikipedia="City_of_Westminster" osm="27365306 51781" type="node relation">City of Westminster</link>, central London, built in the early eighteenth century. The land on which the church stands was donated by General William Steuart, who laid the first stone in 1721. The church was designed by John James and was constructed under a project to build fifty new churches around London (the Queen Anne Churches). The building is one small block south of <link id="GL543_093_001_002" wikipedia="Hanover_Square,_Westminster" osm="38310101" type="way">Hanover Square</link>, near <link id="GL543_093_001_003" wikipedia="Oxford_Street" osm="2354980085" type="node">Oxford Circus</link>, in what is now the <link id="GL543_093_001_004" wikipedia="City_of_Westminster" osm="27365306 51781" type="node relation">City of Westminster</link>. Owing to its <link id="GL543_093_001_005" wikipedia="Mayfair" osm="26745366" type="node">Mayfair</link> location, it has frequently been the venue for high society weddings. </p> </entity>
#
# <entity id="GL249_256" wikipedia="Imola" osm="69300194 43020" type="node relation" status="5">
#       <p id="GL249_256_001" num_links="7">Imola (Italian:&#160;[&#712;i&#720;mola]; Emilian: Iommla, Romagnol: J&#244;mla or Jemula) is a city and comune in the <link id="GL249_256_001_001" wikipedia="Metropolitan_City_of_Bologna" osm="42856" type="relation">Metropolitan City of Bologna</link>, located on the river <link id="GL249_256_001_002" wikipedia="Santerno" osm="2250854" type="relation">Santerno</link>, in the <link id="GL249_256_001_003" wikipedia="Emilia-Romagna" osm="1781917318 42611" type="node relation">Emilia-Romagna</link> region of northern Italy. The city is traditionally considered the western entrance to the historical region <link id="GL249_256_001_004" wikipedia="Romagna" osm="9084464" type="relation">Romagna</link>. </p> </entity>
#
# <entity id="GL244_177" wikipedia="Hummingbird_Highway_(Belize)" osm="9126103" type="relation" status="5">
#       <p id="GL244_177_001" num_links="7">Hummingbird Highway is one of the four major highways in <link id="GL244_177_001_001" wikipedia="Belize" osm="332779764 2609003380 287827" type="node node relation">Belize</link>. It connects the <link id="GL244_177_001_002" wikipedia="George_Price_Highway" osm="9319136" type="relation">George Price Highway</link> outside of <link id="GL244_177_001_003" wikipedia="Belmopan" osm="282294082" type="node">Belmopan</link>, <link id="GL244_177_001_004" wikipedia="Cayo_District" osm="962357" type="relation">Cayo District</link> to the <link id="GL244_177_001_005" wikipedia="Southern_Highway_(Belize)" osm="9103780" type="relation">Southern Highway</link> outside of <link id="GL244_177_001_006" wikipedia="Dangriga" osm="297463331" type="node">Dangriga</link>, <link id="GL244_177_001_007" wikipedia="Stann_Creek_District" osm="962353" type="relation">Stann Creek District</link>. </p> </entity>
#
# <entity id="GL265_134" wikipedia="Julian&#243;w,_Ryki_County" osm="31875917 5580948" type="node relation" status="5">
#       <p id="GL265_134_001" num_links="5">Julian&#243;w [ju&#712;ljanuf] is a village in the administrative district of <link id="GL265_134_001_005" wikipedia="Gmina_K%C5%82oczew" osm="2696479" type="relation">Gmina K&#322;oczew</link>, within <link id="GL265_134_001_001" wikipedia="Ryki_County" osm="2617226" type="relation">Ryki County</link>, <link id="GL265_134_001_002" wikipedia="Lublin_Voivodeship" osm="505006035 130919" type="node relation">Lublin Voivodeship</link>, in eastern Poland.[1] It lies approximately 10 kilometres (6&#160;mi) north of <link id="GL265_134_001_003" wikipedia="Ryki" osm="362659264 3008764" type="node relation">Ryki</link> and 67&#160;km (42&#160;mi) north-west of the regional capital <link id="GL265_134_001_004" wikipedia="Lublin" osm="30014556 2206549 2904797 2904798" type="node relation relation relation">Lublin</link>. </p> </entity>
#
# <entity id="GL079_094" wikipedia="Burg_Stargard" osm="117830170 1419900" type="node relation" status="5">
#       <p id="GL079_094_001" num_links="4">Burg Stargard (Polabian Stargart, is a small town in the <link id="GL079_094_001_001" wikipedia="Mecklenburgische_Seenplatte_(district)" osm="1739376" type="relation">Mecklenburgische Seenplatte</link> district, in <link id="GL079_094_001_002" wikipedia="Mecklenburg-Vorpommern" osm="473857781 28322 62774" type="node relation relation">Mecklenburg-Vorpommern</link>, <link id="GL079_094_001_003" wikipedia="Germany" osm="1683325355 51477 62781" type="node relation relation">Germany</link>. It is situated 8 kilometres (5.0&#160;mi) southeast of <link id="GL079_094_001_004" wikipedia="Neubrandenburg" osm="29680830 62705" type="node relation">Neubrandenburg</link>. </p> </entity>
