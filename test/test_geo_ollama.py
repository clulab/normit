import os
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
    def __init__(self,
                 call_style: str,
                 example_location: str,
                 example_style: str,
                 code_block_style: str):
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
        self.system_text = textwrap.dedent("""\
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
            * Number * UNITS.miles -> pint.Quantity""".format(**self.function_names))
        match example_style:
            case "single":
                self.examples = [
                    dict(
                        text="Y is in Alexandria, Beechworth.",
                        objects="alexandria, beechworth",
                        code="""\
                            # "in Alexandria, Beechworth" means:
                            Y = {intersection}(alexandria, beechworth)"""),
                    dict(
                        text="Y is near Seward.",
                        objects="seward",
                        code="""\
                            # "near Seward" means:
                            Y = {near}(seward)"""),
                    dict(
                        text="Y is 10 miles from Ferryhill.",
                        objects="ferryhill",
                        code="""\
                            # "10 miles from Ferryhill" means:
                            Y = {near}(ferryhill, distance=10 * UNITS.miles)"""),
                    dict(
                        text="Y is between Attle and Palmdale.",
                        objects="attle, palmdale",
                        code="""\
                            # "between Attle and Palmdale" means:
                            Y = {between}(attle, palmdale)"""),
                    dict(
                        text="Y is north of Cicero.",
                        objects="cicero",
                        code="""\
                            # "north of Cicero" means:
                            Y = {north_of}(cicero)"""),
                    dict(
                        text="Y is 5 km east of Bodmin.",
                        objects="bodmin",
                        code="""\
                            # "5 km east of Bodmin" means:
                            Y = {east_of}(bodmin, distance=5 * UNITS.km)"""),
                    dict(
                        text="Y is in southern Wembley.",
                        objects="wembley",
                        code="""\
                            # "in southern Wembley" means:
                            Y = {south_part_of}(wembley)"""),
                ]
            case "multi":
                self.examples = [
                    dict(
                        text="Y is in Alexandria, Beechworth, near Seward.",
                        objects="alexandria, beechworth, seward",
                        code="""\
                            Y = {intersection}(
                                # "Alexandria" means:
                                alexandria,
                                # "Beechworth" means:
                                beechworth,
                                "near Seward" means:
                                {near}(seward),
                            )"""),
                    dict(
                        text="Y is 10 miles from Ferryhill, between Attle and Palmdale.",
                        objects="ferryhill, attle, palmdale",
                        code="""\
                            Y = {intersection}(
                                # "10 miles from Ferryhill" means:
                                {near}(ferryhill, distance=10 * UNITS.miles)
                                # "between Attle and Palmdale" means:
                                {between}(attle, palmdale),
                            )"""),
                    dict(
                        text="Y is north of Cicero, 5 km east of Bodmin, in southern Wembley.",
                        objects="cicero, bodmin, wembley",
                        code="""\
                            Y = {intersection}(
                                # "north of Cicero" means:
                                {north_of}(cicero),
                                # "5 km east of Bodmin" means:
                                {east_of}(bodmin, distance=5 * UNITS.km),
                                # "in southern Wembley" means:
                                {south_part_of}(wembley),
                            )"""),
                ]
        for example in self.examples:
            code = textwrap.dedent(example['code'].format(**self.function_names))
            match code_block_style:
                case 'ticks':
                    example['code'] = f'```python\n{code}\n```'
                case 'none':
                    example['code'] = code
                case _:
                    raise NotImplementedError(code_block_style)
        match example_location:
            case "system":
                example_texts = []
                for example in self.examples:
                    example_texts.append(textwrap.dedent("""\
                        Given the input text:

                        "{text}"

                        and the Geometry objects:

                        {objects}

                        the geometry of Y can be calculated with the following Python code:

                        {code}
                        """).format(**example))
                self.messages = [
                    dict(
                        role='system',
                        content=textwrap.dedent("""\
                            {system}

                            Here are some examples of using the library:

                            {example_text}""").format(
                                system=self.system_text,
                                example_text='\n'.join(example_texts)))
                ]
            case "chat":
                self.messages = [
                    dict(
                        role='system',
                        content=self.system_text)
                ]
                for example in self.examples:
                    self.messages.append(self.user(
                        text=example['text'],
                        objects=example['objects'],
                    ))
                    self.messages.append(dict(
                        role='assistant',
                        content=example['code']))
            case _:
                raise NotImplementedError(call_style)

    def user(self, text, objects):
        return dict(
            role='user',
            content=textwrap.dedent(f"""\
                Given the input text:

                "{text}"

                and the Geometry objects:

                {objects}

                Write Python code to calculate the Geometry of Y. Your code should use only the given Geometry objects, and should call only the normit library functions listed above. Write only a single line of code."""))

    def prompt(self):
        return self.messages


@pytest.mark.skipif("not 'ollama' in config.getoption('keyword')")
def test_ollama_geocode_test(georeader: GeoJsonDirReader, score_logger):

    # import locally, as these are not yet required for the rest of the library
    import ollama
    import simpleeval

    model_name = os.environ["MODEL"]  # llama3.2:3b qwen2.5:14b
    factory = GeoPromptFactory(
        call_style=os.environ['CALL_STYLE'],
        example_location=os.environ['EXAMPLE_LOCATION'],
        example_style=os.environ['EXAMPLE_STYLE'],
        code_block_style=os.environ['CODE_BLOCK_STYLE'],
    )

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
        code = response.message.content
        print('='*50)
        print('assistant')
        print('-'*50)
        print(code)

        # remove code block markup
        last_code_block_end = code.rfind('```')
        if last_code_block_end > 0:
            code = code[:last_code_block_end]
        last_code_block_start = code.rfind('```')
        if last_code_block_start >= 0:
            code = code[last_code_block_start:]
            code = code.replace('```python', '')
            code = code.replace('```', '')

        # remove assignment, since simpleeval only does expressions
        code = code.replace("Y = ", "")

        # run the code to calculate the predicted geometry
        try:
            prediction = simpleeval.simple_eval(
                code,
                names=geo_ops | references,
                functions=geo_ops_functions)
        except Exception:
            print(traceback.format_exc())
            # make a prediction with 0 area so 0 precision and recall are logged
            prediction = target.centroid

        score_logger.p_r_f1(target, prediction, target_name)
