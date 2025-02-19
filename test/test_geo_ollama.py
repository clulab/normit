import pathlib
import pytest
import xml.etree.ElementTree as et
import re
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
geo_ops_as_functions = {name: name for name in geo_ops_functions.keys()}
geo_ops_as_methods = dict(
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

task = """\
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
* Number * UNITS.miles -> pint.Quantity"""

prompt_template = """\
Given the input text:

"{text}"

and the Geometry objects:

{objects}

Write a single line of Python code to calculate the Geometry of Y. Your code should use only the given Geometry objects, and should call only the normit library functions listed above."""

sample_data = [
    dict(text="Y is a circular mountain range in southern Waterford, 10 miles north of Martins Ferry.",
         objects="waterford, martins_ferry",
         response="""\
Y = {intersection}(
  # "southern Waterford"
  {south_part_of}(waterford),  
  # "10 miles north of Martins Ferry"
  {north_of}(martins_ferry, distance=10 * UNITS.miles)
  # "circular mountain range" is irrelevant to the geometry of Y
)
"""),
    dict(text="Y is between Garden City and Stanley, in Litchfield, 25 km south east of Bebington Vale. The north west of Y is rainy.",
         objects="litchfield, garden_city, stanley, bebington_vale",
         response="""\
Y = {intersection}(
  # "in Litchfield"
  litchfield,
  # "between Garden City and Stanley"
  {between}(garden_city, stanley),
  # "25 km south east of Bebington Vale"
  {south_east_of}(bebington_vale, distance=25 * UNITS.km)
  # "north west of Y is rainy" is irrelevant to the geometry of Y
)
"""),
]


@pytest.mark.skipif("not 'ollama' in config.getoption('keyword')")
def test_ollama_geocode_test(georeader: GeoJsonDirReader, score_logger):

    # import locally, as these are not yet required for the rest of the library
    import ollama
    import simpleeval

    # Select the model to evaluate
    model_name = 'llama3.2:3b'
    # model_name = 'deepseek-r1:14b'

    # Select the API style to evaluate
    # ops_names = geo_ops_as_methods
    ops_names = geo_ops_as_functions

    def simplify_name(name):
        return re.sub(r'[\W_]+', '_', name).strip('_').lower()

    # collect the geographical operators for use when running code
    geo_ops = {name: value for name, value in vars(normit.geo.ops).items()
               if name in normit.geo.ops.__all__}

    # assemble the chat history, with the task and the few-shot examples
    messages = [dict(role='system', content=task.format(**ops_names))]
    for datum in sample_data:
        prompt = prompt_template.format(**ops_names | datum)
        messages.append(dict(role='user', content=prompt))
        response = datum['response'].format(**ops_names)
        messages.append(dict(role='assistant', content=response))

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
        datum = dict(text=text, objects=', '.join(references.keys()))
        prompt = prompt_template.format(**ops_names | datum)
        print('='*50)
        print('user')
        print('-'*50)
        print(prompt)

        # ask the model to generate a response to the prompt
        response = ollama.chat(
            model_name,
            options=dict(temperature=0, num_predict=1000),
            messages=messages + [{'role': 'user', 'content': prompt}],
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
