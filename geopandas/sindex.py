from warnings import warn
from collections import namedtuple

from pandas import notnull

from . import _compat as compat
from .array import GeometryDtype as GeometryIterable
from .array import _shapely_to_geom


def has_sindex():
    """
    Dynamically checks for ability to generate spatial index.
    """
    return get_sindex_class() is not None


def get_sindex_class():
    """
    Dynamically chooses a spatial indexing backend.
    Required to comply with _compat.USE_PYGEOS.
    The order of preference goes PyGeos > RTree > None.
    """
    if compat.USE_PYGEOS:
        return PyGEOSSTRTreeIndex
    elif compat.HAS_RTREE:
        return RTreeIndex
    else:
        warn("Cannot generate spatial index: Missing package `rtree`.")
        return None


if compat.HAS_RTREE:

    from rtree.index import Index as ToblerityRTreeIndex  # noqa
    from rtree.core import RTreeError  # noqa

    warn(
        "`rtree` will be deprecated in GeoPandas 0.8; "
        "Please use `pygeos` instead: https://github.com/pygeos/pygeos"
    )

    class RTreeIndex(ToblerityRTreeIndex):
        """
        A simple wrapper around rtree's RTree Index
        """

        def __init__(self, geometry):
            stream = (
                (i, item.bounds, idx)
                for i, (idx, item) in enumerate(geometry.iteritems())
                if notnull(item) and not item.is_empty
            )
            try:
                super().__init__(stream)
            except RTreeError:
                # What we really want here is an empty generator error, or
                # for the bulk loader to log that the generator was empty
                # and move on.
                # See https://github.com/Toblerity/rtree/issues/20.
                super().__init__()

        @property
        def size(self):
            return len(self.leaves()[0][1])

        @property
        def is_empty(self):
            if len(self.leaves()) > 1:
                return False
            return self.size < 1


if compat.HAS_PYGEOS:

    from pygeos import STRtree, box, GeometryType  # noqa

    class PyGEOSSTRTreeIndex(STRtree):
        """
        A simple wrapper around pygeos's STRTree
        """

        with_objects = namedtuple("with_objects", "object id")

        def __init__(self, geometry):
            # for compatibility with old RTree implementation, store ids/indexes
            original_indexes = geometry.index
            non_empty = geometry[~geometry.values.is_empty]
            self.objects = self.ids = original_indexes[~geometry.values.is_empty]
            super().__init__(non_empty.values.data)

        def _process_query(self, geometry, op, objects):
            if isinstance(geometry, GeometryType):
                geometry = _shapely_to_geom(geometry)
                indexes = super().query(geometry, predicate=op)
                if objects:
                    return self.objects.iloc[indexes]
                else:
                    return indexes
            elif isinstance(geometry, GeometryIterable):
                raise NotImplementedError("Coming soon.")
            elif isinstance(geometry, (tuple, list)) and len(geometry) == 4:
                # bounds, convert to geometry
                # this is for RTree compatibility
                indexes = super().query(box(*geometry), predicate=op)
                if objects:
                    objs = self.objects[indexes].values
                    ids = self.ids[indexes]
                    return [
                        self.with_objects(id=id, object=obj)
                        for id, obj in zip(ids, objs)
                    ]
                else:
                    return indexes
            else:
                raise ValueError(
                    "`geometry` must be a Geometry object or tuple of bounds."
                )

        def intersection(self, geometry, objects=False):
            return self._process_query(geometry, op="intersects", objects=objects)

        def contains(self, geometry, objects=False):
            return self._process_query(geometry, op="contains", objects=objects)

        @property
        def size(self):
            return len(self)

        @property
        def is_empty(self):
            return len(self) == 0
