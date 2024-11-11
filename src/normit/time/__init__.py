from .ops import *
from .xml import *


def flatten(shift_or_interval: Shift | Interval) -> Shift | Interval:
    """
    Flattens any nested RepeatingIntersection objects.

    :param shift_or_interval: The object to flatten
    :return: A copy with any nested RepeatingIntersection replaced with a single nested RepeatingIntersection.
    """
    match shift_or_interval:
        case RepeatingIntersection() as ri if any(isinstance(o, RepeatingIntersection) for o in ri.shifts):
            shifts = []
            for shift in ri.shifts:
                shift = flatten(shift)
                if isinstance(shift, RepeatingIntersection):
                    shifts.extend(shift.shifts)
                else:
                    shifts.append(shift)
            return dataclasses.replace(ri, shifts=shifts)
        case has_shift if hasattr(has_shift, "shift"):
            return dataclasses.replace(has_shift, shift=flatten(has_shift.shift))
        case _:
            return shift_or_interval

