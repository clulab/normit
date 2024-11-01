import normit.geo
import pytest


GEOJSON_OPTION = "--geojson-dir"


def pytest_addoption(parser):
    parser.addoption(GEOJSON_OPTION, required=True,
                     help="Directory containing GeoJson files")


@pytest.fixture
def georeader(request):
    return normit.geo.GeoJsonDirReader(request.config.getoption(GEOJSON_OPTION))
