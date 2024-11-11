import normit.geo
import pytest


GEOJSON_OPTION = "--geojson-dir"


def pytest_addoption(parser):
    parser.addoption(GEOJSON_OPTION, help="Directory containing GeoJson files")


@pytest.fixture
def georeader(request):
    geojson_dir = request.config.getoption(GEOJSON_OPTION)
    if geojson_dir is not None:
        return normit.geo.GeoJsonDirReader(geojson_dir)
    else:
        pytest.skip(f"skipping as no {GEOJSON_OPTION}=DIR was provided")
