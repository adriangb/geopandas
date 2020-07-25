import numpy as np
import random

from geopandas import read_file, datasets
from geopandas.sindex import VALID_QUERY_PREDICATES


# Set random seeds
np.random.seed(0)
random.seed(0)


def generate_test_df():
    random.seed(0)
    np.random.seed(0)  # set numpy random seed for reproducible results
    world = read_file(datasets.get_path("naturalearth_lowres"))
    capitals = read_file(datasets.get_path("naturalearth_cities"))
    countries = world.to_crs("epsg:3395")[["geometry"]]
    capitals = capitals.to_crs("epsg:3395")[["geometry"]]
    mixed = capitals.append(countries)  # get a mix of geometries
    points = capitals
    polygons = countries
    # filter out invalid geometries
    data = {
        "mixed": mixed[mixed.is_valid],
        "points": points[points.is_valid],
        "polygons": polygons[polygons.is_valid],
    }
    # ensure index is pre-generated
    for data_type in data.keys():
        data[data_type].sindex.query(data[data_type].geometry.values.data[0])
    return data


class BenchIntersection:

    param_names = ["input_geom_type", "tree_geom_type"]
    params = [
        ["mixed", "points", "polygons"],
        ["mixed", "points", "polygons"],
    ]

    def setup(self, *args):
        self.data = generate_test_df()
        # cache bounds so that bound creation is not counted in benchmarks
        # cache bounds so that bound creation is not counted in benchmarks
        self.bounds = {
            geom_type: [g.bounds for g in self.data[geom_type].geometry]
            for geom_type in self.data.keys()
        }

    def time_intersects(self, input_geom_type, tree_geom_type):
        for bounds in self.bounds[input_geom_type]:
            self.data[tree_geom_type].sindex.intersection(bounds)


class BenchCreation:

    param_names = ["tree_geom_type"]
    params = [["mixed", "points", "polygons"]]

    def setup(self, *args):
        self.data = generate_test_df()
        # cache bounds so that bound creation is not counted in benchmarks
        self.bounds = [g.bounds for g in self.data["mixed"].geometry]

    def time_index_creation(self, tree_geom_type):
        """Time creation of spatial index.

        Note: pygeos will only create the index once; this benchmark
        is not intended to be used to compare rtree and pygeos.
        """
        self.data[tree_geom_type]._sindex_generated = None  # for old versions
        self.data[tree_geom_type].geometry.values._sindex = None  # for new versions
        self.data[tree_geom_type].sindex
        # also do a single query to ensure the index is actually
        # generated and used
        self.data[tree_geom_type].sindex.query(
            self.data[tree_geom_type].geometry.values.data[0]
        )


class BenchQuery:

    param_names = ["predicate", "input_geom_type", "tree_geom_type"]
    params = [
        [*sorted(VALID_QUERY_PREDICATES, key=lambda x: (x is None, x))],
        ["mixed", "points", "polygons"],
        ["mixed", "points", "polygons"],
    ]

    def setup(self, *args):
        self.data = generate_test_df()

    def time_query_bulk(self, predicate, input_geom_type, tree_geom_type):
        self.data[tree_geom_type].sindex.query_bulk(
            self.data[input_geom_type].geometry, predicate=predicate
        )

    def time_query(self, predicate, input_geom_type, tree_geom_type):
        for geo in self.data[input_geom_type].geometry:
            self.data[tree_geom_type].sindex.query(geo, predicate=predicate)
