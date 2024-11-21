import abc
import collections
import dataclasses
import datetime

import dateutil.relativedelta
import dateutil.rrule
import enum
import typing

# noinspection PyUnresolvedReferences
__all__ = [  # noqa: F822
    'Interval',
    'Unit',
    'MICROSECOND',
    'MILLISECOND',
    'SECOND',
    'MINUTE',
    'HOUR',
    'DAY',
    'WEEK',
    'MONTH',
    'QUARTER_YEAR',
    'YEAR',
    'DECADE',
    'QUARTER_CENTURY',
    'CENTURY',
    'Shift',
    'Period',
    'PeriodSum',
    'Repeating',
    'Spring',
    'Summer',
    'Fall',
    'Winter',
    'Weekend',
    'Morning',
    'Noon',
    'Afternoon',
    'Day',
    'Evening',
    'Night',
    'Midnight',
    'EveryNth',
    'ShiftUnion',
    'RepeatingIntersection',
    'Year',
    'YearSuffix',
    'Last',
    'Next',
    'Before',
    'After',
    'Nth',
    'This',
    'Between',
    'Intersection',
    'Intervals',
    'LastN',
    'NextN',
    'NthN',
    'These',
    'flatten',
]


def _dataclass(cls):
    cls = dataclasses.dataclass(repr=False)(cls)

    def __repr__(self):
        fields = [f for f in dataclasses.fields(self)
                  if f.repr
                  and getattr(self, f.name) != f.default
                  and (f.default_factory is dataclasses.MISSING
                       or getattr(self, f.name) != f.default_factory())]
        field_str = ', '.join([f"{f.name}={getattr(self, f.name)!r}"
                               for f in fields])
        return f"{self.__class__.__qualname__}({field_str})"

    cls.__repr__ = __repr__
    return cls


@dataclasses.dataclass
class Interval:
    """
    An interval on the timeline, defined by a starting point (inclusive) and an
    ending point (exclusive).
    For example, the expression "1990", interpreted as the entire year on the
    timeline, would be represented as::

        Interval(start=datetime.datetime.fromisoformat("1990-01-01T00:00:00"),
                 end=datetime.datetime.fromisoformat("1991-01-01T00:00:00"))

    See the :func:`fromisoformat` and :func:`of` methods for more concise ways
    of constructing Intervals.
    """
    start: datetime.datetime | None
    end: datetime.datetime | None

    @classmethod
    def fromisoformat(cls, string: str):
        """
        Creates an Interval from two dates in ISO 8601 format.
        For example, "May 1362" may be represented as::

            Interval.fromisoformat("1362-03-01T00:00:00 1362-04-01T00:00:00")

        The supported formats are the same as
        :func:`datetime.datetime.fromisoformat`, so "May 1362" may be more
        concisely written as::

            Interval.fromisoformat("1362-03-01 1362-04-01")

        :param string: A string containing a starting point and an ending point
            in ISO 8601 format.
        :return: An Interval from the starting point to the ending point.
        """
        isoformats = string.split()
        start, end = [datetime.datetime.fromisoformat(x) for x in isoformats]
        return cls(start, end)

    @classmethod
    def of(cls, *args: int):
        """
        Creates an Interval that aligns to exactly one calendar unit.
        For example, "1990" may be represented as::

            Interval.of(1990)

        And "1 Apr 1918" may be represented as::

            Interval.of(1998, 4, 1)

        :param args: A starting point specified by any prefix of the list of
            time units: year, month, day, hour, minute, second, and microsecond.
        :return: An Interval that starts from the given starting point, and ends
            after the smallest time unit specified.
        """
        # match Interval.of arguments with datetime.__init__ arguments
        names = ["year", "month", "day",
                 "hour", "minute", "second", "microsecond"]
        if len(args) > len(names):
            raise ValueError(f"found {len(args)} arguments, {args!r}, for only "
                             f"{len(names)} time units, {names!r}")
        pairs = list(zip(names, args))
        kwargs = dict(pairs)
        # month and day are required by datetime, so give defaults here
        for name in ["month", "day"]:
            if name not in kwargs:
                kwargs[name] = 1
        # create the datetime for the start
        start = datetime.datetime(**kwargs)
        # end is one smallest unit specified larger than the start
        last_name, _ = pairs[-1]
        # relativedelta argument names are plural
        last_name += "s"
        end = start + dateutil.relativedelta.relativedelta(**{last_name: 1})
        return cls(start, end)

    def is_defined(self) -> bool:
        return self.start is not None and self.end is not None

    def isoformat(self) -> str:
        start_str = "..." if self.start is None else self.start.isoformat()
        end_str = "..." if self.end is None else self.end.isoformat()
        return f"{start_str} {end_str}"

    def __repr__(self):
        delta = dateutil.relativedelta.relativedelta(self.end, self.start)
        if delta == dateutil.relativedelta.relativedelta(years=+1):
            tuple_index = 1
        elif delta == dateutil.relativedelta.relativedelta(months=+1):
            tuple_index = 2
        elif delta == dateutil.relativedelta.relativedelta(days=+1):
            tuple_index = 3
        elif delta == dateutil.relativedelta.relativedelta(hours=+1):
            tuple_index = 4
        elif delta == dateutil.relativedelta.relativedelta(minutes=+1):
            tuple_index = 5
        elif delta == dateutil.relativedelta.relativedelta(seconds=+1):
            tuple_index = 6
        else:
            tuple_index = None
        if tuple_index is not None:
            tup = self.start.timetuple()[:tuple_index]
            return f"Interval.of({', '.join(map(repr, tup))})"
        elif self.start is not None and self.end is not None:
            start = self.start.isoformat()
            end = self.end.isoformat()
            return f"Interval.fromisoformat('{start} {end}')"
        else:
            return f"Interval(start={self.start}, end={self.end})"

    def __len__(self):
        return 2

    def __iter__(self):
        yield self.start
        yield self.end

    def __add__(self, shift):
        return self.end + shift

    def __sub__(self, shift):
        return self.start - shift


class Unit(enum.Enum):
    """
    A named unit of time.

    Note that the values of this enum are also available at the module level.
    So, for example, :const:`normit.time.SECOND` is an alias for
    :const:`normit.time.Unit.SECOND`.
    """
    MICROSECOND = (1, "microseconds")
    MILLISECOND = (2, None)
    SECOND = (3, "seconds")
    MINUTE = (4, "minutes")
    HOUR = (5, "hours")
    DAY = (6, "days")
    WEEK = (7, "weeks")
    MONTH = (8, "months")
    QUARTER_YEAR = (9, None)
    YEAR = (10, "years")
    DECADE = (11, None)
    QUARTER_CENTURY = (12, None)
    CENTURY = (13, None)

    def __init__(self, n, relativedelta_name):
        self._n = n
        self._relativedelta_name = relativedelta_name

    def __lt__(self, other) -> bool:
        if self.__class__ is other.__class__:
            return self._n < other._n
        return NotImplemented

    def __repr__(self):
        return self.name

    def truncate(self, dt: datetime.datetime) -> datetime.datetime:
        """
        Sets all units smaller than this one in the datetime to zero.

        :param dt: The datetime to truncate
        :return: The truncated datetime
        """
        match self:
            case Unit.MILLISECOND:
                dt = dt.replace(microsecond=dt.microsecond // 1000 * 1000)
            case Unit.SECOND:
                dt = dt.replace(microsecond=0)
            case Unit.MINUTE:
                dt = dt.replace(second=0, microsecond=0)
            case Unit.HOUR:
                dt = dt.replace(minute=0, second=0, microsecond=0)
            case Unit.DAY:
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            case Unit.WEEK:
                timetuple = dt.timetuple()
                diff = timetuple.tm_yday - timetuple.tm_wday
                ordinal = diff if diff >= 1 else diff + 7
                start = datetime.date.fromordinal(ordinal)
                dt = datetime.datetime(dt.year, start.month, start.day)
                if diff < 1:
                    dt = dt + dateutil.relativedelta.relativedelta(days=-7)
            case Unit.MONTH:
                dt = datetime.datetime(dt.year, dt.month, 1)
            case Unit.QUARTER_YEAR:
                dt = datetime.datetime(dt.year, (dt.month - 1) // 3 * 3 + 1, 1)
            case Unit.YEAR:
                dt = datetime.datetime(dt.year, 1, 1)
            case Unit.DECADE:
                dt = datetime.datetime(dt.year // 10 * 10, 1, 1)
            case Unit.QUARTER_CENTURY:
                dt = datetime.datetime(dt.year // 25 * 25, 1, 1)
            case Unit.CENTURY:
                year = dt.year // 100 * 100
                year = 1 if year == 0 else year  # year 0 does not exist
                dt = datetime.datetime(year, 1, 1)
        return dt

    def relativedelta(self, n) -> dateutil.relativedelta.relativedelta:
        """
        Constructs a :class:`dateutil.relativedelta.relativedelta` object
        representing of a number of repetitions of this unit.
        :param n: The number of repetitions
        :return: The constructed relativedelta
        """
        if self._relativedelta_name is not None:
            kwargs = {self._relativedelta_name: n}
        elif self is Unit.CENTURY:
            kwargs = {Unit.YEAR._relativedelta_name: 100 * n}
        elif self is Unit.QUARTER_CENTURY:
            kwargs = {Unit.YEAR._relativedelta_name: 25 * n}
        elif self is Unit.DECADE:
            kwargs = {Unit.YEAR._relativedelta_name: 10 * n}
        elif self is Unit.QUARTER_YEAR:
            kwargs = {Unit.MONTH._relativedelta_name: 3 * n}
        else:
            raise NotImplementedError
        return dateutil.relativedelta.relativedelta(**kwargs)

    def expand(self, interval: Interval, n: int = 1) -> Interval:
        """
        Expands an interval to the width of a number of repetitions of this
        unit.

        :param interval: The interval to expand
        :param n: The number of repetitions
        :return: The expanded interval
        """
        if interval.start + self.relativedelta(n) > interval.end:
            mid = interval.start + (interval.end - interval.start) / 2
            if n % 2 == 0 or self in {Unit.MILLISECOND,
                                      Unit.MICROSECOND,
                                      Unit.SECOND,
                                      Unit.MINUTE,
                                      Unit.HOUR,
                                      Unit.DAY,
                                      Unit.WEEK}:
                half = self.relativedelta(n / 2)
            elif self is Unit.MONTH:
                half = Unit.DAY.relativedelta(30 / 2)
            elif self is Unit.YEAR:
                half = Unit.DAY.relativedelta(365 / 2)
            else:
                raise NotImplementedError(f"don't know how to take {n}/2 "
                                          f"of {self}")
            start = mid - half
            interval = Interval(start, start + self.relativedelta(n))
        return interval


# allow e.g., DAY instead of Unit.DAY
globals().update(Unit.__members__)


class Shift:
    """
    An object that can be added or subtracted from a time point yielding an
    Interval
    """

    unit: Unit

    def __rsub__(self, other: datetime.datetime) -> Interval:
        raise NotImplementedError

    def __radd__(self, other: datetime.datetime) -> Interval:
        raise NotImplementedError


@_dataclass
class Period(Shift):
    """
    An amount of time, expressed as counts of standard time units.
    For example, "three months" would be represented as::

        Period(MONTH, 3)

    Note that periods are independent of the timeline. For example, given only
    the period expression "10 weeks", it is impossible to assign time points of
    the form XXXX-XX-XXTXX:XX:XX to its start and end.
    """
    unit: Unit
    n: int | None
    span: (int, int) = dataclasses.field(default=None, repr=False)

    def __radd__(self, other: datetime.datetime) -> Interval:
        if self.unit is None or self.n is None:
            return Interval(other, None)
        else:
            end = other + self.unit.relativedelta(self.n)
            # in the first century, there's only 99 years
            if other == datetime.datetime.min and self.unit is Unit.CENTURY:
                end -= Unit.YEAR.relativedelta(1)
            return Interval(other, end)

    def __rsub__(self, other: datetime.datetime) -> Interval:
        if self.unit is None or self.n is None:
            return Interval(None, other)
        else:
            return Interval(other - self.unit.relativedelta(self.n), other)


@_dataclass
class PeriodSum(Shift):
    """
    A period whose duration is the sum of two or more periods.
    For example, "two years and a day" would be represented as::

        PeriodSum([Period(YEAR, 2), Period(DAY, 1)])
    """
    periods: list[Period]
    span: (int, int) = dataclasses.field(default=None, repr=False)

    def __post_init__(self):
        self.unit = max(self.periods, key=lambda p: p.unit).unit

    def __radd__(self, other: datetime.datetime) -> Interval:
        end = other
        for period in self.periods:
            end = (end + period).end
        return Interval(other, end)

    def __rsub__(self, other: datetime.datetime) -> Interval:
        start = other
        for period in self.periods:
            start = (start - period).start
        return Interval(start, other)


@_dataclass
class Repeating(Shift):
    """
    A Repeating identifies intervals that are named by the calendar system and
    repeat along the timeline.
    For example, the set of all months of year "February" would be represented
    as::

        Repeating(MONTH, YEAR, value=2)

    While the set of all generic calendar "day" would be represented as::

        Repeating(DAY)

    Note that for days of the week, the value follows dateutil in assigning
    Monday as 0, Tuesday as 1, etc.
    So the set of all days of the week "Thursday" would be represented as::

        Repeating(DAY, WEEK, value=3)
    """
    unit: Unit
    range: Unit = None
    value: int = dataclasses.field(default=None, kw_only=True)
    n_units: int = dataclasses.field(default=1, kw_only=True)
    rrule_kwargs: dict = dataclasses.field(default_factory=dict,
                                           kw_only=True, repr=False)
    span: (int, int) = dataclasses.field(default=None, repr=False)

    def __post_init__(self):
        self.period = Period(self.unit, self.n_units)
        if self.range == self.unit:
            pass  # same as self.range is None
        elif self.range is None:
            self.range = self.unit
        elif self.value is None:
            raise ValueError(f"value=None is not allowed for unit={self.unit} "
                             f"and range={self.range}")
        else:
            match self.range:
                case Unit.SECOND:
                    rrule_freq = dateutil.rrule.SECONDLY
                case Unit.MINUTE:
                    rrule_freq = dateutil.rrule.MINUTELY
                case Unit.HOUR:
                    rrule_freq = dateutil.rrule.HOURLY
                case Unit.DAY:
                    rrule_freq = dateutil.rrule.DAILY
                case Unit.WEEK:
                    rrule_freq = dateutil.rrule.WEEKLY
                case Unit.MONTH:
                    rrule_freq = dateutil.rrule.MONTHLY
                case Unit.YEAR:
                    rrule_freq = dateutil.rrule.YEARLY
                case _:
                    raise NotImplementedError
            self.rrule_kwargs["freq"] = rrule_freq

            match (self.unit, self.range):
                case (Unit.SECOND, Unit.MINUTE):
                    rrule_by = "bysecond"
                case (Unit.MINUTE, Unit.HOUR):
                    rrule_by = "byminute"
                case (Unit.HOUR, Unit.DAY):
                    rrule_by = "byhour"
                case (Unit.DAY, Unit.WEEK):
                    rrule_by = "byweekday"
                case (Unit.DAY, Unit.MONTH):
                    rrule_by = "bymonthday"
                case (Unit.DAY, Unit.YEAR):
                    rrule_by = "byyearday"
                case (Unit.WEEK, Unit.YEAR):
                    rrule_by = "byweekno"
                case (Unit.MONTH, Unit.YEAR):
                    rrule_by = "bymonth"
                case _:
                    raise NotImplementedError
            self.rrule_kwargs[rrule_by] = self.value

    def __rsub__(self, other: datetime.datetime) -> Interval:
        if self.unit is None:
            return Interval(None, None)
        other = self.unit.truncate(other)
        if self.rrule_kwargs:
            # HACK: rrule requires a starting point even when going backwards
            # so use a big one
            dtstart = other - Unit.YEAR.relativedelta(100)
            min_end = other - self.period.unit.relativedelta(self.period.n)
            rrule = dateutil.rrule.rrule(dtstart=dtstart, **self.rrule_kwargs)
            start = rrule.before(min_end, inc=True)
            if start is None:
                raise ValueError(f"between {dtstart} and {min_end} there is "
                                 f"no {self.rrule_kwargs}")
            interval = start + self.period
        else:
            interval = other - self.period
        return interval

    def __radd__(self, other: datetime.datetime) -> Interval:
        if self.unit is None:
            return Interval(None, None)
        start = self.unit.truncate(other)
        if self.rrule_kwargs:
            rrule = dateutil.rrule.rrule(dtstart=start, **self.rrule_kwargs)
            start = rrule.after(other, inc=True)
        elif start < other:
            start += self.period.unit.relativedelta(1)
        return start + self.period


# Defined as "meterological seasons"
# https://www.ncei.noaa.gov/news/meteorological-versus-astronomical-seasons
@_dataclass
class Spring(Repeating):
    """
    The repeating interval for meteorological springs in the Northern
    Hemisphere, i.e., March, April, and May
    """
    unit: Unit = Unit.MONTH
    range: Unit = Unit.YEAR
    value: int = 3
    n_units: int = 3


@_dataclass
class Summer(Repeating):
    """
    The repeating interval for meteorological summers in the Northern
    Hemisphere, i.e., June, July, and August
    """
    unit: Unit = Unit.MONTH
    range: Unit = Unit.YEAR
    value: int = 6
    n_units: int = 3


@_dataclass
class Fall(Repeating):
    """
    The repeating interval for meteorological falls in the Northern Hemisphere,
    i.e., September, October, and November
    """
    unit: Unit = Unit.MONTH
    range: Unit = Unit.YEAR
    value: int = 9
    n_units: int = 3


@_dataclass
class Winter(Repeating):
    """
    The repeating interval for meteorological winters in the Northern
    Hemisphere, i.e., December, January, and February
    """
    unit: Unit = Unit.MONTH
    range: Unit = Unit.YEAR
    value: int = 12
    n_units: int = 3


@_dataclass
class Weekend(Repeating):
    """
    The repeating interval for weekends, i.e., Saturdays and Sundays
    """
    unit: Unit = Unit.DAY
    n_units: int = 2
    rrule_kwargs: dict = dataclasses.field(
        default_factory=lambda: dict(freq=dateutil.rrule.DAILY, byweekday=5))


# defined as used in forecasts
# https://www.weather.gov/bgm/forecast_terms
@_dataclass
class Morning(Repeating):
    """
    The repeating interval for meteorological mornings, i.e., 06:00 until 12:00
    """
    unit: Unit = Unit.HOUR
    range: Unit = Unit.DAY
    value: int = 6
    n_units: int = 6


@_dataclass
class Noon(Repeating):
    """
    The repeating interval for noons, i.e., 12:00 until 12:01
    """
    unit: Unit = Unit.MINUTE
    rrule_kwargs: dict = dataclasses.field(
        default_factory=lambda: dict(freq=dateutil.rrule.DAILY,
                                     byhour=12, byminute=0))


@_dataclass
class Afternoon(Repeating):
    """
    The repeating interval for meteorological afternoons, i.e.,
    12:00 until 18:00
    """
    unit: Unit = Unit.HOUR
    range: Unit = Unit.DAY
    value: int = 12
    n_units: int = 6


@_dataclass
class Day(Repeating):
    """
    The repeating interval for meteorological daytime, i.e., 06:00 until 06:00
    """
    unit: Unit = Unit.HOUR
    range: Unit = Unit.DAY
    value: int = 6
    n_units: int = 12


@_dataclass
class Evening(Repeating):
    """
    The repeating interval for meteorological evenings, i.e., 18:00 until 00:00
    """
    unit: Unit = Unit.HOUR
    range: Unit = Unit.DAY
    value: int = 18
    n_units: int = 6


@_dataclass
class Night(Repeating):
    """
    The repeating interval for meteorological nights, i.e., 00:00 until 06:00
    """
    unit: Unit = Unit.HOUR
    range: Unit = Unit.DAY
    value: int = 0
    n_units: int = 6


@_dataclass
class Midnight(Repeating):
    """
    The repeating interval for midnights, i.e., 00:00 until 00:01
    """
    unit: Unit = Unit.MINUTE
    rrule_kwargs: dict = dataclasses.field(
        default_factory=lambda: dict(freq=dateutil.rrule.DAILY,
                                     byhour=0, byminute=0))


@_dataclass
class EveryNth(Shift):
    """
    A repeating interval that retains only every nth interval of another
    repeating interval.
    For example, "every other Friday" would be represented as::

        EveryNth(Repeating(DAY, WEEK, value=4), n=2)
    """
    shift: Shift
    n: int
    span: (int, int) = dataclasses.field(default=None, repr=False)

    def __rsub__(self, other: datetime.datetime) -> Interval:
        interval = other - self.shift
        for _ in range(self.n - 1):
            interval -= self.shift
        return interval

    def __radd__(self, other: datetime.datetime) -> Interval:
        interval = other + self.shift
        for _ in range(self.n - 1):
            interval += self.shift
        return interval


@_dataclass
class ShiftUnion(Shift):
    """
    The union of two or more time shifts (periods, repeating intervals, etc.).
    For example, the set of all days of the week "Mondays and Fridays" would be
    represented as::

        ShiftUnion([Repeating(DAY, WEEK, value=0),
                    Repeating(DAY, WEEK, value=4)])
    """
    shifts: typing.Iterable[Shift]
    span: (int, int) = dataclasses.field(default=None, repr=False)

    def __post_init__(self):
        self.unit = min(o.unit for o in self.shifts)
        self.range = max(o.unit for o in self.shifts)

    def __rsub__(self, other: datetime.datetime) -> Interval:
        return max((other - shift for shift in self.shifts),
                   key=lambda i: (i.end, i.end - i.start))

    def __radd__(self, other: datetime.datetime) -> Interval:
        return min((other + shift for shift in self.shifts),
                   key=lambda i: (i.start, i.start - i.end))


@_dataclass
class RepeatingIntersection(Shift):
    """
    A repeating interval that is the intersection of two or more repeating
    intervals.
    For example, "Saturdays in March" would be represented as::

        RepeatingIntersection([Repeating(DAY, WEEK, value=5),
                               Repeating(MONTH, YEAR, value=3)])
    """
    shifts: typing.Iterable[Repeating]
    span: (int, int) = dataclasses.field(default=None, repr=False)

    def _iter_shifts(self) -> typing.Iterator[Repeating]:
        for shift in self.shifts:
            if isinstance(shift, RepeatingIntersection):
                yield from shift._iter_shifts()
            elif not isinstance(shift, Repeating):
                raise NotImplementedError(shift)
            else:
                yield shift

    def __post_init__(self):
        if not self.shifts:
            cls_name = self.__class__.__name__
            raise ValueError(f"{cls_name} shifts cannot be empty")
        self.rrule_kwargs = {}
        periods = []
        rrule_periods = []
        non_rrule_periods = []
        for shift in self._iter_shifts():
            periods.append(shift.period)
            if shift.rrule_kwargs:
                self.rrule_kwargs |= shift.rrule_kwargs
                rrule_periods.append(shift.period)
            else:
                non_rrule_periods.append(shift.period)

        def by_unit(period: Period) -> Unit:
            # note that 0 is smaller than all Unit._n values
            return period.unit._n if period.unit is not None else 0
        self.min_period = min(periods, default=None, key=by_unit)
        self.rrule_period = min(rrule_periods, default=None, key=by_unit)
        self.non_rrule_period = min(non_rrule_periods, default=None,
                                    key=by_unit)
        self.unit = self.min_period.unit
        self.range = max(periods, default=None, key=by_unit).unit

    def __rsub__(self, other: datetime.datetime) -> Interval:
        if self.unit is None:
            return Interval(None, None)
        start = self.min_period.unit.truncate(other)
        if self.rrule_period is not None:
            # HACK: rrule requires a starting point even when going backwards.
            # So we use a big one, but this is inefficient
            dtstart = start - Unit.YEAR.relativedelta(100)
            while True:
                # find the start and interval using the rrule
                rrule = dateutil.rrule.rrule(dtstart=dtstart,
                                             **self.rrule_kwargs)
                start = rrule.before(start, inc=True)
                if start is None:
                    raise ValueError(f"no {self.rrule_kwargs} between "
                                     f"{dtstart} and {start}")
                interval = start + self.rrule_period

                # subtract off any non-rrule period
                if self.non_rrule_period is not None:
                    interval = start - self.non_rrule_period

                    # if outside the valid range of the rrule, move back in
                    if interval.start < self.rrule_period.unit.truncate(start):
                        delta = self.rrule_period.unit.relativedelta
                        interval = Interval(
                            interval.start + delta(self.rrule_period.n),
                            interval.end + delta(self.rrule_period.n))

                # start is guaranteed to be before other by rrule; end is not
                if interval.end <= other:
                    break
                start -= Unit.MICROSECOND.relativedelta(1)
        elif self.non_rrule_period is not None:
            interval = start - self.non_rrule_period
        else:
            raise ValueError(f"{self.rrule_period} and {self.non_rrule_period} "
                             f"are both None")
        return interval

    def __radd__(self, other: datetime.datetime) -> Interval:
        if self.unit is None:
            return Interval(None, None)
        start = self.min_period.unit.truncate(other)
        if start < other:
            start += self.min_period.unit.relativedelta(self.min_period.n)
        if self.rrule_period is not None:
            rrule = dateutil.rrule.rrule(dtstart=start, **self.rrule_kwargs)
            start = rrule.after(start, inc=True)
            if start is None:
                raise ValueError(f"no {self.rrule_kwargs} between "
                                 f"{start} and {other}")
        return start + self.min_period


_RepeatingLike = Repeating | ShiftUnion | RepeatingIntersection
_PeriodLike = Period | PeriodSum


@_dataclass
class Year(Interval):
    """
    The interval from the first second of a year (inclusive) to the first second
    of the next year (exclusive).
    For example, the year-long interval "2014" would be represented as::

        Year(2014)

    Year can also be used to identify decades and centuries by indicating how
    many digits are missing.
    For example, the 10-year-long interval "the 1980s" would be represented as::

        Year(198, n_missing_digits=1)
    """
    digits: int
    n_missing_digits: int = 0
    start: datetime.datetime | None = dataclasses.field(init=False, repr=False)
    end: datetime.datetime | None = dataclasses.field(init=False, repr=False)
    span: (int, int) = dataclasses.field(default=None, repr=False)

    def __post_init__(self):
        duration_in_years = 10 ** self.n_missing_digits
        year = self.digits * duration_in_years
        self.start = datetime.datetime(year=year, month=1, day=1)
        delta = dateutil.relativedelta.relativedelta(years=duration_in_years)
        self.end = self.start + delta


@_dataclass
class YearSuffix(Interval):
    """
    A year-long interval created from the year of another interval and a suffix
    of digits to replace in that year.
    For example, the year "96" in the context of a document written in 1993
    would be represented as::

        YearSuffix(Year(1993), last_digits=96)

    YearSuffix can also be used to modify decades and centuries by indicating
    how many digits are missing.
    For example, the 10-year-long interval "the 70s" in the context of a
    document written in 1864 be represented as::

        YearSuffix(Year(1864), 7, n_missing_digits=1)
    """
    interval: Interval
    digits: int
    n_missing_digits: int = 0
    start: datetime.datetime | None = dataclasses.field(init=False, repr=False)
    end: datetime.datetime | None = dataclasses.field(init=False, repr=False)
    span: (int, int) = dataclasses.field(default=None, repr=False)

    def __post_init__(self):
        n_digits = len(str(self.digits))
        divider = 10 ** (n_digits + self.n_missing_digits)
        multiplier = 10 ** n_digits
        digits = self.interval.start.year // divider * multiplier + self.digits
        self.start, self.end = Year(digits, self.n_missing_digits)


@_dataclass
class _IntervalOp(Interval):
    """
    A base class for operators that take in an Interval and a Shift and produce
    an Interval.
    """
    interval: Interval
    shift: Shift
    start: datetime.datetime | None = dataclasses.field(init=False, repr=False)
    end: datetime.datetime | None = dataclasses.field(init=False, repr=False)


@_dataclass
class Last(_IntervalOp):
    """
    The closest preceding interval matching the specified Shift.
    For example, "over the past four days" when spoken on 1 Nov 2024 would be
    represented as::

        Last(Interval.of(2024, 11, 1), Period(DAY, 4))

    Similarly, "the previous summer" when spoken on 14 Feb 1912 would be
    represented as::

        Last(Interval.of(1912, 2, 14), Summer())

    By default, the resulting interval must end by the start of the input
    interval, but :code:`interval_included=True` will allow the resulting
    interval to end as late as the end of the input interval.
    For example, if text written on Tue 8 Nov 2016 wrote "arrived on Tuesday"
    with the intention of "arrived today" (a common practice in news articles),
    it would be represented as::

        Last(Interval.of(2016, 11, 8),
             Repeating(DAY, WEEK, value=1),
             interval_included=True)
    """
    interval_included: bool = False
    span: (int, int) = dataclasses.field(default=None, repr=False)

    def __post_init__(self):
        if not self.interval.is_defined():
            self.start = None
            self.end = None
        elif self.shift is None:
            self.start = None
            self.end = self.interval.start
        else:
            if self.interval_included:
                start = self.interval.end
            else:
                start = self.interval.start
            self.start, self.end = start - self.shift


@_dataclass
class Next(_IntervalOp):
    """
    The closest following interval matching the specified Shift.
    For example, "the next three hours" when spoken on 1 Nov 2024 would be
    represented as::

        Next(Interval.of(2024, 11, 1), Period(HOUR, 3))

    Similarly, "the coming week" when spoken on 14 Feb 1912 would be represented
    as::

        Next(Interval.of(1912, 2, 14), Repeating(WEEK))

    By default, the resulting interval must not start before the end of the
    input interval, but :code:`interval_included=True` will allow the resulting
    interval to start as early as the start of the input interval.
    """
    interval_included: bool = False
    span: (int, int) = dataclasses.field(default=None, repr=False)

    def __post_init__(self):
        if not self.interval.is_defined():
            self.start = None
            self.end = None
        elif self.shift is None:
            self.start = self.interval.end
            self.end = None
        else:
            if self.interval_included:
                end = self.interval.start
                # to allow repeating intervals to start with our start,
                # subtract a tiny amount
                if isinstance(self.shift, _RepeatingLike):
                    end -= Unit.MICROSECOND.relativedelta(1)
            else:
                end = self.interval.end
            self.start, self.end = end + self.shift


@_dataclass
class Before(_IntervalOp):
    """
    Moves the input Interval earlier by the specified Shift the specified number
    of times.
    For example, "a year ago" written on 13 Sep 1595 would be represented as::

        Before(Interval.of(1595, 9, 13), Period(YEAR, 1))

    Similarly, "two Tuesdays before" written on Sat 23 Jan 1993 would be
    represented as::

        Before(Interval.of(1993, 1, 23), Repeating(DAY, WEEK, value=1), n=2)

    By default, the resulting interval must end by the start of the input
    interval, but when the Shift is a Repeating, :code:`interval_included=True`
    will allow the resulting interval to end as late as the end of the input
    interval.
    """
    n: int = 1
    interval_included: bool = False
    span: (int, int) = dataclasses.field(default=None, repr=False)

    def __post_init__(self):
        if not self.interval.is_defined():
            self.start = None
            self.end = None
        elif isinstance(self.shift, _RepeatingLike):
            if self.interval_included:
                start = self.interval.end
            else:
                start = self.interval.start
            for i in range(self.n - 1):
                start = (start - self.shift).start
            self.start, self.end = start - self.shift
        elif isinstance(self.shift, _PeriodLike):
            if self.interval_included:
                raise ValueError("interval_included=True cannot be used "
                                 "with Periods")
            self.start, self.end = self.interval
            for i in range(self.n):
                self.start = (self.start - self.shift).start
                self.end = (self.end - self.shift).start
        elif self.shift is None:
            self.start = None
            self.end = self.interval.start
        else:
            raise NotImplementedError


@_dataclass
class After(_IntervalOp):
    """
    Moves the input Interval later by the specified Shift the specified number
    of times.
    For example, "a month later" written on 13 Sep 1595 would be represented
    as::

        After(Interval.of(1595, 9, 13), Period(MONTH, 1))

    Similarly, "three Aprils after" written on Sat 23 Jan 1993 would be
    represented as::

        After(Interval.of(1993, 1, 23), Repeating(MONTH, YEAR, value=4), n=3)

    By default, the resulting interval must not start before the end of the
    input interval, but when the Shift is a Repeating,
    :code:`interval_included=True` will allow the resulting interval to start as
    early as the start of the input interval.
    """
    n: int = 1
    interval_included: bool = False
    span: (int, int) = dataclasses.field(default=None, repr=False)

    def __post_init__(self):
        if not self.interval.is_defined():
            self.start = None
            self.end = None
        elif isinstance(self.shift, _RepeatingLike):
            # to allow repeating intervals to overlap start with our start,
            # subtract a tiny amount
            end = self.interval.start - Unit.MICROSECOND.relativedelta(
                1) if self.interval_included else self.interval.end
            for i in range(self.n - 1):
                end = (end + self.shift).end
            self.start, self.end = end + self.shift
        elif isinstance(self.shift, _PeriodLike):
            if self.interval_included:
                raise ValueError("interval_included=True cannot be used "
                                 "with Periods")
            self.start, self.end = self.interval
            for i in range(self.n):
                self.start = (self.start + self.shift).end
                self.end = (self.end + self.shift).end
        elif self.shift is None:
            self.start = self.interval.end
            self.end = None
        else:
            raise NotImplementedError


@_dataclass
class Nth(_IntervalOp):
    """
    Selects the nth repetition of a Shift starting from one end of the Interval.
    For example, "second hour of the meeting" for a meeting at 09:30-12:30 on
    30 Mar 2007 would be represented as::

        Nth(Interval.fromisoformat("2007-03-30T09:30 2007-03-30T12:30"),
            Period(HOUR, 1),
            index=2)

    Similarly, "fiftieth day of 2016" would be represented as::

        Nth(Year(2016), Repeating(DAY), index=50)

    By default, Nth will start from the start and count forward in time, but
    with :code:`from_end=True` Nth will instead start from the end and count
    backward in time.
    For example, "third-to-last Sunday of 2024" would be represented as::

        Nth(Year(2024), Repeating(DAY, WEEK, value=6), index=3, from_end=True)
    """
    index: int
    from_end: bool = False
    span: (int, int) = dataclasses.field(default=None, repr=False)

    def __post_init__(self):
        if self.shift is None or (self.from_end and self.interval.end is None) \
                or (not self.from_end and self.interval.start is None):
            self.start = None
            self.end = None
        else:
            point = self.interval.end if self.from_end else self.interval.start
            # to allow repeating intervals to overlap start with our start,
            # subtract a tiny amount
            if isinstance(self.shift, _RepeatingLike) \
                    and not self.from_end \
                    and not point == datetime.datetime.min:
                point -= Unit.MICROSECOND.relativedelta(1)
            for i in range(self.index - 1):
                if self.from_end:
                    point = (point - self.shift).start
                else:
                    point = (point + self.shift).end
            if self.from_end:
                interval = point - self.shift
            else:
                interval = point + self.shift
            self.start, self.end = interval
            if (self.start is not None and self.interval.start is not None and
                self.start < self.interval.start) or \
                    (self.end is not None and self.interval.end is not None and
                     self.end > self.interval.end):
                raise ValueError(f"{self.isoformat()} is not within "
                                 f"{self.interval.isoformat()}:\n{self}")


@_dataclass
class This(_IntervalOp):
    """
    For period Shifts, creates an interval of the given length centered at the
    given interval.
    For example, "these six days" spoken on 29 Apr 1176 would be interpreted as
    [1176-04-26T12:00:00, 1176-05-02T12:00:00) and represented as::

        This(Interval.of(1176, 4, 29), Period(DAY, 6))

    For repeating Shifts, finds the Shift range containing this interval, then
    finds the Shift unit within that range.
    For example, "this January" spoken on 10 Nov 1037 would be interpreted as
    [1037-01-01T00:00:00, 1037-02-01T00:00:00) and represented as::

        This(Interval.of(1037, 11, 10), Repeating(MONTH, YEAR, value=1))
    """
    interval: Interval
    shift: Shift
    start: datetime.datetime | None = dataclasses.field(init=False, repr=False)
    end: datetime.datetime | None = dataclasses.field(init=False, repr=False)
    span: (int, int) = dataclasses.field(default=None, repr=False)

    def __post_init__(self):
        if not self.interval.is_defined() or self.shift is None:
            self.start = None
            self.end = None
        elif isinstance(self.shift, _RepeatingLike):
            if self.shift.range is None:
                self.start = self.end = None
            else:
                start = self.shift.range.truncate(self.interval.start)
                start -= Unit.MICROSECOND.relativedelta(1)
                self.start, self.end = start + self.shift
                if (self.end + self.shift).end < self.interval.end:
                    raise ValueError(f"there is more than one {self.shift} in "
                                     f"{self.interval.isoformat()}")
        elif isinstance(self.shift, _PeriodLike):
            if self.shift.unit is None or self.shift.n is None:
                self.start = self.end = None
            else:
                interval = self.shift.unit.expand(self.interval, self.shift.n)
                self.start, self.end = interval
        else:
            raise NotImplementedError


@_dataclass
class Between(Interval):
    """
    Selects the interval between a start and an end interval.
    For example, "since 1994" written on 09 Jan 2007 and interpreted as
    [1995-01-01T00:00:00, 2007-01-09T00:00:00) would be represented as::

        Between(Year(1994), Interval.of(2007, 1, 9))

    If :code:`start_included=False`, starts from the end of `start_interval`,
    otherwise, starts from the start.
    If :code:`end_included=False`, ends at the start of `end_interval`,
    otherwise ends at the end.
    So "since 1994" written on 09 Jan 2007 and interpreted as
    [1994-01-01T00:00:00, 2007-01-10T00:00:00) would be represented as::

        Between(Year(1994), Interval.of(2007, 1, 9),
                start_included=True, end_included=True)
    """
    start_interval: Interval
    end_interval: Interval
    start_included: bool = False
    end_included: bool = False
    start: datetime.datetime | None = dataclasses.field(init=False, repr=False)
    end: datetime.datetime | None = dataclasses.field(init=False, repr=False)
    span: (int, int) = dataclasses.field(default=None, repr=False)

    def __post_init__(self):
        if not self.start_interval.is_defined() or \
                not self.end_interval.is_defined():
            self.start = None
            self.end = None
        else:
            if self.start_included:
                self.start = self.start_interval.start
            else:
                self.start = self.start_interval.end
            if self.end_included:
                self.end = self.end_interval.end
            else:
                self.end = self.end_interval.start
            if self.end < self.start:
                start_iso = self.start_interval.isoformat()
                end_iso = self.end_interval.isoformat()
                raise ValueError(f"{start_iso} is not before {end_iso}")


@_dataclass
class Intersection(Interval):
    """
    Selects the interval in which all given intervals overlap.
    For example, "Earlier that day" in the context of "We met at 6:00 on 24 Jan
    1979. Earlier that day..." would be interpreted as
    [1979-01-24T00:00:00, 1979-01-24T06:00:00) and represented as::

        Intersection([Last(Interval.of(1979, 1, 24, 6), None),
                      Interval.of(1979, 1, 24)])
    """
    intervals: typing.Iterable[Interval]
    start: datetime.datetime | None = dataclasses.field(init=False, repr=False)
    end: datetime.datetime | None = dataclasses.field(init=False, repr=False)
    span: (int, int) = dataclasses.field(default=None, repr=False)

    def __post_init__(self):
        if any(i.start is None and i.end is None for i in self.intervals):
            self.start = self.end = None
        else:
            starts = (i.start for i in self.intervals if i.start is not None)
            ends = (i.end for i in self.intervals if i.end is not None)
            self.start = max(starts, default=None)
            self.end = min(ends, default=None)
        if self.start is not None and self.end is not None and \
                self.start >= self.end:
            raise ValueError(f"{self.start.isoformat()} is not before "
                             f"{self.end.isoformat()}")


class Intervals(collections.abc.Iterable[Interval], abc.ABC):
    """
    A collection of intervals on the timeline.
    """
    def isoformats(self) -> list[str]:
        return [interval.isoformat() for interval in self]


@_dataclass
class _N(Intervals):
    """
    A base class for operators that in an Interval, a Shift, and an integer, and
    produce an Interval.
    """
    interval: Interval
    shift: Shift
    n: int
    interval_included: bool = False
    base_class: type = None

    def _adjust_for_n_none(self, interval: Interval):
        raise NotImplementedError

    def __iter__(self) -> typing.Iterator[Interval]:
        interval = self.interval
        interval_included = self.interval_included
        n = 2 if self.n is None else self.n
        for i in range(n):
            interval = self.base_class(interval, self.shift, interval_included)
            if self.n is None and i == 1:
                self._adjust_for_n_none(interval)
            yield interval
            if i == 0:
                interval_included = False


@_dataclass
class LastN(_N):
    """
    Repeats the `Last` operation n times.
    For example, "the previous two summers" when written on 29 May 1264 would be
    represented as::

        LastN(Interval.of(1264, 5, 29), Summer(), n=2)
    """
    base_class: type = Last
    span: (int, int) = dataclasses.field(default=None, repr=False)

    def _adjust_for_n_none(self, interval: Interval):
        interval.start = None


@_dataclass
class NextN(_N):
    """
    Repeats the `Next` operation n times.
    For example, "the next six Fridays" when written on Sat 22 Dec 1714 would be
    represented as::

        NextN(Interval.of(1714, 12, 22), Repeating(DAY, WEEK, value=4), n=6)
    """
    base_class: type = Next
    span: (int, int) = dataclasses.field(default=None, repr=False)

    def _adjust_for_n_none(self, interval: Interval):
        interval.end = None


@_dataclass
class NthN(Intervals):
    """
    Selects a specified number of nth repetitions of a Shift starting from one
    end of the Interval.
    For example, "the second six Mondays of 1997" would be represented as::

        NthN(Year(1997), Repeating(DAY, WEEK, value=0), index=2, n=6)
    """
    interval: Interval
    shift: Shift
    index: int
    n: int
    from_end: bool = False
    span: (int, int) = dataclasses.field(default=None, repr=False)

    def __iter__(self) -> typing.Iterator[Interval]:
        n = 2 if self.n is None else self.n
        start = 1 + (self.index - 1) * n
        for index in range(start, start + n):
            interval = Nth(self.interval, self.shift, index,
                           from_end=self.from_end)
            if self.n is None and index == start + 1:
                if self.from_end:
                    interval.start = None
                else:
                    interval.end = None
            yield interval


@_dataclass
class These(Intervals):
    """
    Finds the Shift range containing this interval, then finds the Shift units
    within that range.
    For example, "Tuesdays and Thursdays in January 2025" would be represented
    as::

        These(Interval.of(2025, 1),
              ShiftUnion([Repeating(DAY, WEEK, value=1),
                          Repeating(DAY, WEEK, value=3)]))
    """
    interval: Interval
    shift: Shift
    span: (int, int) = dataclasses.field(default=None, repr=False)

    def __post_init__(self):
        if not self.interval.is_defined() or self.shift is None:
            start = None
            end = None
        else:
            if isinstance(self.shift, Repeating):
                range_unit = self.shift.range
            else:
                range_unit = self.shift.unit
            start = range_unit.truncate(self.interval.start)
            end = range_unit.truncate(self.interval.end)
            if end != self.interval.end:
                _, end = end + Repeating(range_unit)
        self.interval = Interval(start, end)

    def __iter__(self) -> typing.Iterator[Interval]:
        # without a start, we can't find anything
        if self.interval.start is None:
            yield Interval(None, None)
        # without an end, we would generate an infinite number of intervals
        elif self.interval.end is None:
            yield Interval(None, None)
        else:
            interval = self.interval.start + self.shift
            while True:
                if interval.end is None:
                    yield Interval(None, None)
                    break
                if interval.end > self.interval.end:
                    break
                yield interval
                interval = interval.end + self.shift


def flatten(shift_or_interval: Shift | Interval) -> Shift | Interval:
    """
    Flattens any nested RepeatingIntersection objects.

    :param shift_or_interval: The object to flatten
    :return: A copy with any nested RepeatingIntersection replaced with a single
     nested RepeatingIntersection.
    """
    match shift_or_interval:
        case RepeatingIntersection() as ri if any(
                isinstance(o, RepeatingIntersection) for o in ri.shifts):
            shifts = []
            for shift in ri.shifts:
                shift = flatten(shift)
                if isinstance(shift, RepeatingIntersection):
                    shifts.extend(shift.shifts)
                else:
                    shifts.append(shift)
            return dataclasses.replace(ri, shifts=shifts)
        case op if hasattr(op, "shift"):
            return dataclasses.replace(op, shift=flatten(op.shift))
        case _:
            return shift_or_interval
