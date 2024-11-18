import argparse
import datetime
import pathlib
import sys
import traceback
import xml.etree.ElementTree as et

from normit.time import *


parser = argparse.ArgumentParser()
subparser = parser.add_subparsers()
xml_parser = subparser.add_parser("xml")
xml_parser.add_argument("xml_dir")
xml_parser.add_argument("--xml-suffix", default=".TimeNorm.gold.completed.xml")
xml_parser.add_argument("--text-dir")
xml_parser.add_argument("--dct-dir")
xml_parser.add_argument("--silent", action="store_true")
xml_parser.add_argument("--flatten", action="store_true")
args = parser.parse_args()

n_errors = 0

# iterate over the selected Anafora XML paths
xml_paths = list(pathlib.Path(args.xml_dir).glob(f"**/*{args.xml_suffix}"))
if not xml_paths:
    message = f"no such paths: {args.xml_dir}/**/*.{args.xml_suffix}\n"
    parser.exit(message=message)
for xml_path in xml_paths:

    # load the document creation time, if provided
    if args.dct_dir is not None:
        dct_name = xml_path.name.replace(args.xml_suffix, ".dct")
        dct_path = pathlib.Path(args.dct_dir) / dct_name
        with open(dct_path) as dct_file:
            dct_text = dct_file.read().strip()
            [year, month, day] = map(int, dct_text.strip().split("-"))
            doc_time = Interval.of(int(year), int(month), int(day))

    # use today for the document creation time, if not provided
    else:
        today = datetime.date.today()
        doc_time = Interval.of(today.year, today.month, today.day)

    # parse the Anafora XML into Intervals, Shifts, etc.
    elem = et.parse(xml_path).getroot()
    try:
        for obj in from_xml(elem, known_intervals={(None, None): doc_time}):
            if args.flatten:
                obj = flatten(obj)
            if not args.silent:
                print(obj)
    except AnaforaXMLParsingError as e:
        text_name = xml_path.name.replace(args.xml_suffix, "")
        if args.text_dir:
            text_dir = pathlib.Path(args.text_dir)
        else:
            text_dir = xml_path.parent
        with open(text_dir / text_name) as text_file:
            text = text_file.read()

        start, end = e.trigger_span
        pre_text = text[max(0, start - 100):start]
        post_text = text[end:min(len(text), end + 100)]
        traceback.print_exception(e.__cause__)
        print(f"\nContext:\n{pre_text}[[{text[start:end]}]]{post_text}"
              f"\nXML:\n{e}"
              f"\nFile:\n{xml_path}\n", file=sys.stderr)
        n_errors += 1

if n_errors:
    print(f"Errors: {n_errors}", file=sys.stderr)
