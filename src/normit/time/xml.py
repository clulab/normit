import collections
import dataclasses
import datetime
import dateutil.relativedelta
import re
import xml.etree.ElementTree as et

from .ops import *


__all__ = ['from_xml', 'AnaforaXMLParsingError']


def from_xml(elem: et.Element,
             known_intervals: dict[(int, int), Interval] = None
             ) -> list[Shift | Interval | Intervals]:
    """
    Reads Intervals and Shifts from SCATE Anafora XML.

    :param elem: The root <data> element of a SCATE Anafora XML document.
    :param known_intervals: A mapping from character offset spans to Intervals,
    representing intervals that are already known before parsing begins. The
    document creation time should be specified with the span (None, None).
    :return: Intervals and Shifts corresponding to the XML definitions.
    """
    if known_intervals is None:
        known_intervals = {}

    @dataclasses.dataclass
    class Number:
        value: int | float
        shift: Shift = None
        span: (int, int) = dataclasses.field(default=None, repr=False)

    @dataclasses.dataclass
    class AMPM:
        value: str
        span: (int, int) = dataclasses.field(default=None, repr=False)

    id_to_entity = {}
    id_to_children = {}
    id_to_n_parents = collections.Counter()
    for entity in elem.findall(".//entity"):
        entity_id = entity.findtext("id")
        if entity_id in id_to_entity:
            other = id_to_entity[entity_id]
            raise ValueError(f"duplicate id {entity_id} on "
                             f"{et.tostring(entity)} and {et.tostring(other)}")
        id_to_entity[entity_id] = entity
        id_to_children[entity_id] = set()
        for prop in entity.find("properties"):
            if prop.text and '@' in prop.text:
                id_to_children[entity_id].add(prop.text)
                id_to_n_parents[prop.text] += 1

    # to avoid infinite loops below, remove non-existent entities
    # (i.e., values that are not keys)
    for key in id_to_children:
        id_to_children[key].intersection_update(id_to_children.keys())

    # topological sort
    sorted_ids = {}
    while id_to_children:
        for key in list(id_to_children):
            if not id_to_children[key]:
                id_to_children.pop(key)
                sorted_ids[key] = True
        for key, values in id_to_children.items():
            id_to_children[key] -= sorted_ids.keys()

    id_to_obj = {}
    for entity_id in sorted_ids:
        entity = id_to_entity[entity_id]
        sub_interval_id = entity.findtext("properties/Sub-Interval")
        super_interval_id = entity.findtext("properties/Super-Interval")
        entity_type = entity.findtext("type")
        prop_value = entity.findtext("properties/Value")
        prop_type = entity.findtext("properties/Type")
        prop_number = entity.findtext("properties/Number")
        spans = []

        # TODO: revisit whether discontinuous spans need to be retained
        char_offsets = {int(x)
                        for start_end in entity.findtext("span").split(";")
                        for x in start_end.split(",")}
        trigger_span = (min(char_offsets), max(char_offsets))

        # helper for managing access to id_to_obj
        def pop(obj_id: str) -> \
                Interval | Shift | Period | Repeating | Number | AMPM:
            result = id_to_obj[obj_id]
            id_to_n_parents[obj_id] -= 1
            if not id_to_n_parents[obj_id]:
                id_to_obj.pop(obj_id)
            if result.__class__ is not Interval:  # raw Interval has no span
                spans.append(result.span)
            return result

        # helper for ET.findall + text + pop
        def pop_all_prop(prop_name: str) -> \
                list[Interval | Shift | Period | Repeating | Number | AMPM]:
            path = f"properties/{prop_name}"
            return [pop(e.text) for e in entity.findall(path) if e.text]

        # helper for managing the multiple interval properties
        def get_interval(prop_name: str) -> Interval:
            prop_interval_type = entity.findtext(f"properties/{prop_name}-Type")
            prop_interval = entity.findtext(f"properties/{prop_name}")
            match prop_interval_type:
                case "Link":
                    return pop(prop_interval)
                case "DocTime" if (None, None) in known_intervals:
                    return known_intervals.get((None, None))
                case "DocTime-Year" if (None, None) in known_intervals:
                    doc_time = known_intervals.get((None, None))
                    return Year(doc_time.start.year)
                case "DocTime" | "DocTime-Year":
                    raise ValueError("known_intervals[(None, None)] required")
                case "DocTime-Era":
                    return Interval(datetime.datetime.min, None)
                case "Unknown":
                    return Interval(None, None)
                case other_type:
                    raise NotImplementedError(other_type)

        # helper for managing the multiple shift properties
        def get_shift() -> Shift:
            prop_shift = entity.findtext("properties/Period") or \
                         entity.findtext("properties/Repeating-Interval")
            return pop(prop_shift) if prop_shift else None

        # helper for managing Included properties
        def get_included(prop_name: str) -> bool:
            match entity.findtext(f"properties/{prop_name}"):
                case "Included" | "Interval-Included":
                    return True
                case "Not-Included" | "Interval-Not-Included" | "Standard":
                    return False
                case other_type:
                    raise NotImplementedError(other_type)

        # create objects from <entity> elements
        try:
            match entity_type:
                case "Period":
                    if prop_type == "Unknown":
                        unit = None
                    else:
                        unit_name = prop_type.upper()
                        unit_name = re.sub(r"IES$", r"Y", unit_name)
                        unit_name = re.sub(r"S$", r"", unit_name)
                        unit_name = re.sub("-", "_", unit_name)
                        unit = globals()[unit_name]
                    if prop_number:
                        n = pop(prop_number).value
                    else:
                        n = None
                    obj = Period(unit, n)
                case "Sum":
                    obj = PeriodSum(pop_all_prop("Periods"))
                case "Year" | "Two-Digit-Year":
                    digits_str = prop_value.rstrip('?')
                    n_missing_digits = len(prop_value) - len(digits_str)
                    digits = int(digits_str)
                    match entity_type:
                        case "Year":
                            obj = Year(digits, n_missing_digits)
                        case "Two-Digit-Year":
                            obj = YearSuffix(get_interval("Interval"),
                                             digits, n_missing_digits)
                        case other:
                            raise NotImplementedError(other)
                case "Month-Of-Year":
                    dt = datetime.datetime.strptime(prop_type, '%B')
                    obj = Repeating(MONTH, YEAR, value=dt.month)
                case "Day-Of-Month":
                    obj = Repeating(DAY, MONTH, value=int(prop_value))
                case "Day-Of-Week":
                    day_str = prop_type.upper()[:2]
                    day_int = getattr(dateutil.relativedelta, day_str).weekday
                    obj = Repeating(DAY, WEEK, value=day_int)
                case "AMPM-Of-Day":
                    obj = AMPM(prop_type)
                case "Hour-Of-Day":
                    hour = int(prop_value)
                    prop_am_pm = entity.findtext("properties/AMPM-Of-Day")
                    if prop_am_pm:
                        match pop(prop_am_pm).value:
                            case "AM" if hour == 12:
                                hour = 0
                            case "PM" if hour != 12:
                                hour += 12
                            case "AM" | "PM":
                                pass
                            case other:
                                raise NotImplementedError(other)
                    obj = Repeating(HOUR, DAY, value=hour)
                case "Minute-Of-Hour":
                    obj = Repeating(MINUTE, HOUR, value=int(prop_value))
                case "Second-Of-Minute":
                    obj = Repeating(SECOND, MINUTE, value=int(prop_value))
                case "Season-Of-Year" | \
                     "Part-Of-Day" if prop_type in {"Unknown", "Dawn", "Dusk"}:
                    # TODO: improve handling of location-dependent times
                    obj = Repeating(None)
                case "Part-Of-Day" | "Part-Of-Week" | "Season-Of-Year":
                    obj = globals()[prop_type]()
                case "Calendar-Interval":
                    unit_name = prop_type.upper().replace("-", "_")
                    obj = Repeating(globals()[unit_name])
                case "Union":
                    obj = ShiftUnion(pop_all_prop("Repeating-Intervals"))
                case "Every-Nth":
                    obj = EveryNth(get_shift(), int(prop_value))
                case "Last" | "Next" | "Before" | "After" | \
                     "NthFromEnd" | "NthFromStart":
                    if entity_type.startswith("Nth"):
                        cls_name = "Nth"
                    else:
                        cls_name = entity_type
                    interval = get_interval("Interval")
                    shift = get_shift()
                    kwargs = {}
                    match cls_name:
                        case "Last" | "Next" | "Before" | "After":
                            kwargs["interval_included"] = \
                                get_included("Semantics")
                        case "Nth":
                            kwargs["index"] = int(prop_value)
                            kwargs["from_end"] = entity_type == "NthFromEnd"
                    if isinstance(shift, Number):
                        kwargs["n"] = shift.value
                        if cls_name not in {"Before", "After"}:
                            cls_name += "N"
                        shift = shift.shift
                    cls = globals()[cls_name]
                    obj = cls(interval=interval, shift=shift, **kwargs)
                case "This":
                    obj = This(get_interval("Interval"), get_shift())
                case "Between":
                    obj = Between(get_interval("Start-Interval"),
                                  get_interval("End-Interval"),
                                  start_included=get_included("Start-Included"),
                                  end_included=get_included("End-Included"))
                case "Intersection":
                    match (pop_all_prop("Intervals"),
                           pop_all_prop("Repeating-Intervals")):
                        case intervals, []:
                            obj = Intersection(intervals)
                        case [], repeating_intervals:
                            obj = RepeatingIntersection(repeating_intervals)
                        case [interval], [repeating_interval]:
                            obj = This(interval, repeating_interval)
                        case [interval], repeating_intervals:
                            obj = This(interval, RepeatingIntersection(
                                repeating_intervals))
                        case other:
                            raise NotImplementedError(other)
                case "Number":
                    if prop_value == '?':
                        value = None
                    elif prop_value.isdigit():
                        value = int(prop_value)
                    else:
                        try:
                            value = float(prop_value)
                        except ValueError:
                            # TODO: handle ranges better
                            value = None
                    obj = Number(value)
                case "Event":
                    obj = known_intervals.get(trigger_span)
                    if obj is None:
                        obj = Interval(None, None)
                case "Time-Zone" | "Modifier" | "Frequency" | \
                     "NotNormalizable" | "PreAnnotation":
                    # TODO: handle time zones, modifiers, and frequencies
                    continue
                case other:
                    raise NotImplementedError(other)

            # add spans to objects
            obj.span = obj.trigger_span = trigger_span
            spans.append(obj.span)

            # if Number property present, wrap shift with number for later use
            # skip this for Periods, which directly consume their Number above
            if prop_number and not isinstance(obj, Period):
                repeating_n = pop(prop_number)
                repeating_n.shift = obj
                obj = repeating_n

            # create additional objects as necessary for sub-intervals
            if sub_interval_id:
                sub_interval = pop(sub_interval_id)
                match entity_type:
                    case "Year" | "Two-Digit-Year":
                        obj = This(obj, sub_interval)
                    case "Month-Of-Year" | "Day-Of-Month" | "Day-Of-Week" | \
                         "Part-Of-Week" | "Part-Of-Day" | \
                         "Hour-Of-Day" | "Minute-Of-Hour" | "Second-Of-Minute":
                        obj = RepeatingIntersection([obj, sub_interval])
                    case other:
                        raise NotImplementedError(other)

            # create additional objects as necessary for super-intervals
            if super_interval_id:
                super_interval = pop(super_interval_id)
                match super_interval:
                    case Year() | YearSuffix() | This():
                        obj = This(super_interval, obj)
                    case Repeating():
                        obj = RepeatingIntersection([super_interval, obj])
                    case other:
                        raise NotImplementedError(other)

            obj.span = (min(start for start, _ in spans),
                        max(end for _, end in spans))

        except Exception as ex:
            raise AnaforaXMLParsingError(entity, trigger_span) from ex

        # add the object to the mapping
        id_to_obj[entity_id] = obj

    # remove any Number objects as they're internal implementation details
    for key in list(id_to_obj):
        if isinstance(id_to_obj[key], Number):
            del id_to_obj[key]

    return list(id_to_obj.values())


class AnaforaXMLParsingError(RuntimeError):
    """
    An exception thrown when `from_xml` is unable to parse a valid Shift,
    Interval, or Intervals from an Anafora XML
    """
    def __init__(self, entity: et.Element, trigger_span: (int, int)):
        self.entity = entity
        self.trigger_span = trigger_span
        xml_str = et.tostring(entity, encoding="unicode")
        super().__init__(re.sub(r"\s+", "", xml_str))
