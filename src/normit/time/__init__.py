"""
The normit.time module provides utilities for normalizing time expressions in
text.
"""

from .ops import *  # noqa: F401
from .xml import *  # noqa: F401

__all__ = ops.__all__ + xml.__all__

for _name in __all__:
    _obj = globals()[_name]
    if hasattr(_obj, "__module__"):
        _obj.__module__ = __name__
