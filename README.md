normit
======

[![tests](https://github.com/clulab/normit/actions/workflows/tests.yml/badge.svg)](https://github.com/clulab/normit/actions/workflows/tests.yml)
[![docs](https://readthedocs.org/projects/normit/badge/?version=latest)](https://app.readthedocs.org/projects/normit/)

The normit library normalizes information in text: times, locations, etc.

For times, it provides an interface inspired by the SCATE schema of
[Bethard and Parker (2016)](#citation).
For example, the following code finds the first Friday the 13th after
November 21, 2024.

```pycon
>>> from normit.time import *
>>> Next(
...     Interval.of(2024, 11, 21),
...     RepeatingIntersection([
...          Repeating(DAY, WEEK, value=4),   # Friday
...          Repeating(DAY, MONTH, value=13), # the 13th
...     ])
... ).isoformat()
'2024-12-13T00:00:00 2024-12-14T00:00:00'
```

For locations, it provides an interface inspired by the GeoCoDe dataset of
[Laparra and Bethard (2020)](#citation).
For example, the following code finds the region that is 50km northwest of
Tucson and 90km southeast of Phoenix.
```pycon
>>> from normit.geo import *
>>> georeader = GeoJsonDirReader(...)
>>> tucson = georeader.read(253824)
>>> phoenix = georeader.read(111257)
>>> Intersection.of(
...     NorthWest.of(tucson, 50 * UNITS.km),
...     SouthEast.of(phoenix, 90 * UNITS.km))
<POLYGON ((-111.727 32.35, -111.718 32.407, -111.714 32.423, -111.711 32.436...>
```

Citation
--------
If you use the time operators, please cite:
```bibtex
@inproceedings{bethard-parker-2016-semantically,
    title = "A Semantically Compositional Annotation Scheme for Time Normalization",
    author = "Bethard, Steven  and
      Parker, Jonathan",
    booktitle = "Proceedings of the Tenth International Conference on Language Resources and Evaluation ({LREC}'16)",
    month = may,
    year = "2016",
    address = "Portoro{\v{z}}, Slovenia",
    publisher = "European Language Resources Association (ELRA)",
    url = "https://aclanthology.org/L16-1599",
    pages = "3779--3786",
}
```
If you use the geographical operators, please cite:
```bibtex
@inproceedings{laparra-bethard-2020-dataset,
    title = "A Dataset and Evaluation Framework for Complex Geographical Description Parsing",
    author = "Laparra, Egoitz  and
      Bethard, Steven",
    booktitle = "Proceedings of the 28th International Conference on Computational Linguistics",
    month = dec,
    year = "2020",
    address = "Barcelona, Spain (Online)",
    publisher = "International Committee on Computational Linguistics",
    url = "https://aclanthology.org/2020.coling-main.81",
    doi = "10.18653/v1/2020.coling-main.81",
    pages = "936--948",
}
```
