import normit.geo
import pathlib
import pytest
import shapely.geometry.base
import shapely.ops


GEOJSON_OPTION = "--geojson-dir"


def pytest_addoption(parser):
    parser.addoption(GEOJSON_OPTION, help="Directory containing GeoJson files")


@pytest.fixture
def georeader(request):
    geojson_dir = request.config.getoption(GEOJSON_OPTION)
    if geojson_dir is None:
        geojson_dir = pathlib.Path(__file__).parent / "data" / "openstreetmap"
    return normit.geo.GeoJsonDirReader(geojson_dir)


class ScoreLogger:
    def __init__(self):
        self.precisions = []
        self.recalls = []
        self.f1s = []
        self.names = []

    def p_r_f1(self,
               reference: shapely.geometry.base.BaseGeometry,
               prediction: shapely.geometry.base.BaseGeometry,
               request):
        proj = normit.geo.utm_proj(reference)
        reference = shapely.ops.transform(proj, reference)
        prediction = shapely.ops.transform(proj, prediction)
        # for rivers, etc. buffer to 1km so there is area to compare
        if not reference.area:
            reference = reference.buffer(1000)
        intersection_area = reference.intersection(prediction).area
        if not prediction.area:
            precision = 0.0
        else:
            precision = intersection_area / prediction.area
        if not reference.area:
            recall = 0.0
        else:
            recall = intersection_area / reference.area
        if not precision and not recall:
            f1 = 0.0
        else:
            f1 = 2 * precision * recall / (precision + recall)
        self.precisions.append(precision)
        self.recalls.append(recall)
        self.f1s.append(f1)
        if isinstance(request, pytest.FixtureRequest):
            self.names.append(request.function.__name__)
        else:
            self.names.append(request)
        return precision, recall, f1

    def log(self):
        if not self.names:
            return
        print()
        for precision, recall, f1, name in zip(self.precisions, self.recalls,
                                               self.f1s, self.names):
            print(f"P: {precision:.3f}  R: {recall:.3f}  F1: {f1:.3f}  {name}")
        precision = sum(self.precisions) / len(self.precisions)
        recall = sum(self.recalls) / len(self.recalls)
        if precision and recall:
            f1 = 2 * precision * recall / (precision + recall)
        else:
            f1 = 0.0
        print(f"P: {precision:.3f}  R: {recall:.3f}  F1: {f1:.3f}  MEAN")


@pytest.fixture(scope='session')
def score_logger(request):
    logger = ScoreLogger()
    yield logger
    # no capsys workaround: https://github.com/pytest-dev/pytest/issues/2704
    plugin = request.config.pluginmanager.getplugin("capturemanager")
    with plugin.global_and_fixture_disabled():
        logger.log()
