"""Tools to log data from the network."""
import abc
import collections
from typing import Any
from typing import Dict  # noqa pylint: disable=W0611
from typing import List
from typing import Tuple
from typing import Iterable

import pandas as pd  # type: ignore

Attr = str
"""In our logs, we record attributes as strings."""

AttrObs = Tuple[Attr, Any]
"""
An observation of one of an object's attributes.

It is a tuple containing the attribute name, and the value of that attribute,
e.g. ("unit_act", 0.3).

"""

ObjObs = List[AttrObs]
"""An observation of an object (i.e. many of the object's attributes."""


class DataFrameBuffer:
    """A buffer of dataframe rows.

    This gives us constant time append. When we're done collecting rows, we
    can condense them all into a dataframe.
    """

    def __init__(self) -> None:
        self.length = 0

        def new() -> List[Any]:
            return [None] * self.length

        self.buf = collections.defaultdict(new)  # type: Dict[str, List[Any]]

    def append(self, row: ObjObs) -> None:
        """Appends a row to the dataframe buffer.

        If the row contains an attribute that hasn't been logged before, the
        column is filled in with Nones for previous time steps. If the row
        doesn't contain all the attributes in the dataframe, the missing
        attributes take None for their values.

        Args:
            row: The list of attribute observations to append to the buffer.

        """
        for k, v in row:
            self.buf[k].append(v)
        self.length += 1
        self._pad()

    def to_df(self) -> pd.DataFrame:
        """Returns a DataFrame containing the data in the buffer."""
        return pd.DataFrame.from_dict(self.buf)

    def _pad(self) -> None:
        """Pads all the columns in the buffer with Nones until they are the
        same length."""
        for _, v in self.buf.items():
            while len(v) < self.length:
                v.append(None)


class ObservableMixin(metaclass=abc.ABCMeta):
    """Defines the interface required by `Logger` to record attributes.

    Attributes:
        name (str): The name of the object.

    """

    def __init__(self, name: str, *args: Any, **kwargs: Any) -> None:
        self.name = name
        super().__init__(*args, **kwargs)  # type: ignore

    @abc.abstractmethod
    def observe(self, attr: str) -> List[Tuple[str, Any]]:
        """Observes an attribute on this object.

        Args:
            attr: The attribute to observe. The name "attribute" is a bit of a
                misnomer, because it could be something computed on-the-fly.

        Returns:
            A list of observations of the attribute. A single observation is a
            Tuple[str, Any], where the first element is the attribute name and
            the second element is the observation value. We return a list
            because one attribute, like a layer's "unit_act", can return many
            observations, e.g. [("unit0_act", 0.0), ("unit1_act", 0.0), ...]

        Raises:
            ValueError: if attr is not a loggable attribute.

        """


class Logger:
    """Records target attributes to an internal buffer.

    Args:
        target: The object from which to record attributes. It must inherit
            from `ObservableMixin`.
        attrs: A list of attribute names to log.

    Attrs:
        name (str): The name of the target object.

    """

    def __init__(self, target: ObservableMixin, attrs: Iterable[str]) -> None:
        self.target = target
        self.target_name = target.name
        self.attrs = attrs
        self.buffer = DataFrameBuffer()

    def record(self) -> None:
        """Records the attributes to an internal buffer."""
        row = []  # type: ObjObs
        for a in self.attrs:
            row.extend(self.target.observe(a))
        self.buffer.append(row)

    def to_df(self) -> pd.DataFrame:
        """Converts the internal buffer to a dataframe.

        Returns:
            A dataframe containing the contents of the internal buffer. The
            columns names are the attribute names, and each row contains the
            observations for one call of the record() method.

        """
        return self.buffer.to_df()
