import pathlib
import pytest
import xml.etree.ElementTree as et
import re
import textwrap
import traceback

import normit.geo.ops
from normit.geo import *

geo_ops_functions = dict(
    intersection=Intersection.of,
    near=Near.to,
    between=Between.of,
    north_west_of=NorthWest.of,
    north_of=North.of,
    north_east_of=NorthEast.of,
    east_of=East.of,
    south_east_of=SouthEast.of,
    south_of=South.of,
    south_west_of=SouthWest.of,
    west_of=West.of,
    north_west_part_of=NorthWest.part_of,
    north_part_of=North.part_of,
    north_east_part_of=NorthEast.part_of,
    east_part_of=East.part_of,
    south_east_part_of=SouthEast.part_of,
    south_part_of=South.part_of,
    south_west_part_of=SouthWest.part_of,
    west_part_of=West.part_of,
)


class GeoPromptFactory:
    def __init__(self, call_style):
        match call_style:
            case "function":
                self.function_names = {name: name for name in geo_ops_functions.keys()}
            case "classmethod":
                self.function_names = dict(
                    intersection='Intersection.of',
                    near='Near.to',
                    between='Between.of',
                    north_west_of='NorthWest.of',
                    north_of='North.of',
                    north_east_of='NorthEast.of',
                    east_of='East.of',
                    south_east_of='SouthEast.of',
                    south_of='South.of',
                    south_west_of='SouthWest.of',
                    west_of='West.of',
                    north_west_part_of='NorthWest.part_of',
                    north_part_of='North.part_of',
                    north_east_part_of='NorthEast.part_of',
                    east_part_of='East.part_of',
                    south_east_part_of='SouthEast.part_of',
                    south_part_of='South.part_of',
                    south_west_part_of='SouthWest.part_of',
                    west_part_of='West.part_of',
                )
            case _:
                raise NotImplementedError(call_style)

    def system(self):
        return dict(
            role='system',
            content=textwrap.dedent("""\
                Use the normit.geo Python library, https://normit.readthedocs.io/, to calculate the shape of a geographical region.
                The library operates over shapely Geometry objects and and pint Quantity objects.
                The library provides the following functions:

                * {intersection}(*geometries: shapely.Geometry) -> Geometry
                * {near}(geometry: shapely.Geometry, distance: pint.Quantity = None, radius: pint.Quantity = None) -> Geometry
                * {between}(geometry1: shapely.Geometry, geometry2: shapely.Geometry) -> Geometry
                * {north_west_of}(geometry: shapely.Geometry, distance: pint.Quantity = None) -> Geometry
                * {north_of}(geometry: shapely.Geometry, distance: pint.Quantity = None) -> Geometry
                * {north_east_of}(geometry: shapely.Geometry, distance: pint.Quantity = None) -> Geometry
                * {east_of}(geometry: shapely.Geometry, distance: pint.Quantity = None) -> Geometry
                * {south_east_of}(geometry: shapely.Geometry, distance: pint.Quantity = None) -> Geometry
                * {south_of}(geometry: shapely.Geometry, distance: pint.Quantity = None) -> Geometry
                * {south_west_of}(geometry: shapely.Geometry, distance: pint.Quantity = None) -> Geometry
                * {west_of}(geometry: shapely.Geometry, distance: pint.Quantity = None) -> Geometry
                * {north_west_part_of}(geometry: shapely.Geometry) -> Geometry
                * {north_part_of}(geometry: shapely.Geometry) -> Geometry
                * {north_east_part_of}(geometry: shapely.Geometry) -> Geometry
                * {east_part_of}(geometry: shapely.Geometry) -> Geometry
                * {south_east_part_of}(geometry: shapely.Geometry) -> Geometry
                * {south_part_of}(geometry: shapely.Geometry) -> Geometry
                * {south_west_part_of}(geometry: shapely.Geometry) -> Geometry
                * {west_part_of}(geometry: shapely.Geometry) -> Geometry
                * Number * UNITS.km -> pint.Quantity
                * Number * UNITS.miles -> pint.Quantity""".format(**self.function_names)))

    def user(self, text, objects):
        return dict(
            role='user',
            content=textwrap.dedent(f"""\
                Given the input text:

                "{text}"

                and the Geometry objects:

                {objects}

                Write a single line of Python code to calculate the Geometry of Y. Your code should use only the given Geometry objects, and should call only the normit library functions listed above."""))

    def assistant(self, response):
        return dict(
            role='assistant',
            content=textwrap.dedent(response.format(**self.function_names)))

    def prompt(self):
        return [
            self.system(),
            self.user(
                text="Y is a circular mountain range in southern Waterford, 10 miles north of Martins Ferry.",
                objects="waterford, martins_ferry"),
            self.assistant("""\
                Y = {intersection}(
                  # "a circular mountain range" is irrelevant to the geometry of Y
                  # "in southern Waterford" means:
                  {south_part_of}(waterford),
                  # "10 miles north of Martins Ferry" means:
                  {north_of}(martins_ferry, distance=10 * UNITS.miles),
                )
                """),
            self.user(
                text="Y is between Garden City and Stanley, in Litchfield, 25 km south east of Bebington Vale. The north west of Y is rainy.",
                objects="litchfield, garden_city, stanley, bebington_vale"),
            self.assistant("""\
                Y = {intersection}(
                  # "between Garden City and Stanley" means:
                  {between}(garden_city, stanley),
                  # "in Litchfield" means:
                  litchfield,
                  # "25 km south east of Bebington Vale" means:
                  {south_east_of}(bebington_vale, distance=25 * UNITS.km),
                  # "The north west of Y is rainy" is irrelevant to the geometry of Y
                )
                """),
        ]


@pytest.mark.skipif("not 'ollama' in config.getoption('keyword')")
def test_ollama_geocode_test(georeader: GeoJsonDirReader, score_logger):

    # import locally, as these are not yet required for the rest of the library
    import ollama
    import simpleeval

    model_name = 'llama3.2:3b'
    # model_name='deepseek-r1:14b'
    factory = GeoPromptFactory(call_style='function')

    def simplify_name(name):
        return re.sub(r'[\W_]+', '_', name).strip('_').lower()

    # collect the geographical operators for use when running code
    geo_ops = {name: value for name, value in vars(normit.geo.ops).items()
               if name in normit.geo.ops.__all__}

    # assemble the chat history, with the task and the few-shot examples
    messages = factory.prompt()

    print()
    for message in messages:
        print('='*50)
        print(message['role'])
        print('-'*50)
        print(message['content'])

    # evaluate the prompt + model on the GeoCoDe test data
    tree = et.parse(pathlib.Path(__file__).parent / "data" / "geocode_test.xml")
    for entity_elem in tree.findall("entities/entity")[:20]:

        # collect the text and replace the target name with "Y"
        text = ''.join(entity_elem.itertext()).strip()
        text = "Y" + text[text.find(" is"):]

        # read in the target polygon and the reference polygons
        target_name = entity_elem.attrib['wikipedia']
        target = georeader.read(*entity_elem.attrib['osm'].split())
        references = {}
        for link in entity_elem.findall('p/link'):

            # skip reference polygons deleted when the target was trimmed
            if link.text not in text:
                continue

            # skip items expressed in terms of too many components
            osms = link.attrib['osm'].split()
            if len(osms) > 5:
                references = {}
                break
            references[simplify_name(link.text)] = georeader.read(*osms)

        # skip examples with no reference polygons (or skipped above)
        if not references:
            continue

        # prepare the prompt for this example
        message = factory.user(text=text, objects=', '.join(references.keys()))
        print('='*50)
        print(message['role'])
        print('-'*50)
        print(message['content'])

        # ask the model to generate a response to the prompt
        response = ollama.chat(
            model_name,
            options=dict(temperature=0, num_predict=1000),
            messages=messages + [message],
        )

        # extract the code and run it
        flags = re.DOTALL | re.MULTILINE
        matches = re.findall(r'^Y = (.*?^[)])$', response.message.content, flags)
        print('='*50)
        print('assistant')
        print('-'*50)
        print(matches[-1] if matches else response.message.content)
        try:
            prediction = simpleeval.simple_eval(
                matches[-1],
                names=geo_ops | references,
                functions=geo_ops_functions)
        except Exception:
            print(traceback.format_exc())
            # make a prediction with 0 area so 0 precision and recall are logged
            prediction = target.centroid

        score_logger.p_r_f1(target, prediction, target_name)
        # show_plot(target, prediction)
