import pathlib
import pytest
import xml.etree.ElementTree as et
import re

import normit.geo.ops
from normit.geo import *

task = """\
Use the normit.geo Python library, https://normit.readthedocs.io/, to calculate the shape of a geographical region.
The library operates over shapely Geometry objects and and pint Quantity objects.
The library provides the following functions:

* Intersection.of(*geometries: shapely.Geometry) -> Geometry
* Near.to(geometry: shapely.Geometry, distance: pint.Quantity = None, radius: pint.Quantity = None) -> Geometry
* Between.of(geometry1: shapely.Geometry, geometry2: shapely.Geometry) -> Geometry
* NorthWest.of(geometry: shapely.Geometry, distance: pint.Quantity = None) -> Geometry
* North.of(geometry: shapely.Geometry, distance: pint.Quantity = None) -> Geometry
* NorthEast.of(geometry: shapely.Geometry, distance: pint.Quantity = None) -> Geometry
* East.of(geometry: shapely.Geometry, distance: pint.Quantity = None) -> Geometry
* SouthEast.of(geometry: shapely.Geometry, distance: pint.Quantity = None) -> Geometry
* South.of(geometry: shapely.Geometry, distance: pint.Quantity = None) -> Geometry
* SouthWest.of(geometry: shapely.Geometry, distance: pint.Quantity = None) -> Geometry
* West.of(geometry: shapely.Geometry, distance: pint.Quantity = None) -> Geometry
* NorthWest.part_of(geometry: shapely.Geometry) -> Geometry
* North.part_of(geometry: shapely.Geometry) -> Geometry
* NorthEast.part_of(geometry: shapely.Geometry) -> Geometry
* East.part_of(geometry: shapely.Geometry) -> Geometry
* SouthEast.part_of(geometry: shapely.Geometry) -> Geometry
* South.part_of(geometry: shapely.Geometry) -> Geometry
* SouthWest.part_of(geometry: shapely.Geometry) -> Geometry
* West.part_of(geometry: shapely.Geometry) -> Geometry
* Number * UNITS.km -> pint.Quantity
* Number * UNITS.miles -> pint.Quantity
"""

prompt_template = """\
Given the input text:

"{text}"

and the Geometry objects:

{objects}

Write a single line of Python code using only the given geometry objects and the normit.geo library to calculate the Geometry of Y."""

sample_data = [
    dict(text="Y is a circular mountain range in southern Waterford, 10 miles north of Martins Ferry.",
         objects="waterford, martins_ferry",
         response="""\
Y = Intersection.of(
  # "southern Waterford"
  South.part_of(waterford),  
  # "10 miles north of Martins Ferry"
  North.of(martins_ferry, distance=10 * UNITS.miles)
  # "circular mountain range" is irrelevant to the geometry of Y
)
"""),
    dict(text="Y is between Garden City and Stanley, in Litchfield, 25 km south east of Bebington Vale. The north west of Y is rainy.",
         objects="litchfield, garden_city, stanley, bebington_vale",
         response="""\
Y = Intersection.of(
  # "in Litchfield"
  litchfield,
  # "between Garden City and Stanley"
  Between.of(garden_city, stanley),
  # "25 km south east of Bebington Vale"
  SouthEast.of(bebington_vale, distance=25 * UNITS.km)
  # "north west of Y is rainy" is irrelevant to the geometry of Y
)
"""),
]


@pytest.mark.skipif("not 'ollama' in config.getoption('keyword')")
def test_ollama_geocode_test(georeader: GeoJsonDirReader, score_logger):

    # import locally, as these are not yet required for the rest of the library
    import ollama
    import simpleeval

    model_name = 'llama3.2:3b'
    # model_name = 'deepseek-r1:14b'

    # collect the geographical operators for use when running code
    geo_ops = {name: value for name, value in vars(normit.geo.ops).items()
               if name in normit.geo.ops.__all__}

    # assemble the chat history, with the task and the few-shot examples
    messages = [dict(role='system', content=task)]
    for datum in sample_data:
        messages.append(dict(role='user', content=prompt_template.format(**datum)))
        messages.append(dict(role='assistant', content=datum['response']))

    # evaluate the prompt + model on the GeoCoDe test data
    tree = et.parse(pathlib.Path(__file__).parent / "data" / "geocode_test.xml")
    for entity_elem in tree.findall("entities/entity")[:10]:

        # collect the text and replace the target name with "Y"
        text = ''.join(entity_elem.itertext()).strip()
        text = "Y" + text[text.find(" is"):]

        # read in the target polygon and the reference polygons
        target_name = entity_elem.attrib['wikipedia']
        target = georeader.read(*entity_elem.attrib['osm'].split())
        references = {
            link.attrib['wikipedia'].replace(',', '').lower():
                georeader.read(*link.attrib['osm'].split())
            for link in entity_elem.findall('p/link')
            if link.text in text
        }

        # prepare the prompt for this example
        objects_str = ', '.join(references.keys())
        prompt = prompt_template.format(text=text, objects=objects_str)
        print('='*50)
        print(prompt)

        # ask the model to generate a response to the prompt
        response = ollama.chat(
            model_name,
            options={'temperature': 0},
            messages=messages + [{'role': 'user', 'content': prompt}],
        )
        print('-'*50)
        print(response.message.content)

        # extract the code and run it
        flags = re.DOTALL | re.MULTILINE
        match = re.search(r'^Y = (.*^[)])$', response.message.content, flags)
        try:
            code = match.group(1)
            prediction = simpleeval.simple_eval(code, names=geo_ops | references)
        except Exception as e:
            print(e)
        else:
            score_logger.p_r_f1(target, prediction, target_name)
            show_plot(target, prediction)
