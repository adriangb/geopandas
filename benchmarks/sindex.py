import random

from geopandas import GeoDataFrame, GeoSeries
from shapely.geometry import Point, Polygon
import numpy as np


class BenchPredicates:

    param_names = ["predicate"]
    params = [(None, "intersects", "contains", "within")]

    def setup(self, *args):
        triangles = GeoSeries(
            [
                Polygon([(random.random(), random.random()) for _ in range(3)])
                for _ in range(100)
            ]
        )

        points = GeoSeries(
            [
                Point(x, y)
                for x, y in zip(np.random.random(1000), np.random.random(1000))
            ]
        )

        df1 = GeoDataFrame(
            {"val1": np.random.randn(len(triangles)), "geometry": triangles}
        )
        df2 = GeoDataFrame({"val1": np.random.randn(len(points)), "geometry": points})

        self.df, self.df2, self.data = df1, df2, df2.geometry.values.data
        self.bounds = [point.bounds for point in points]

    def time_bulk_query_data(self, predicate):
        self.df.sindex.query_bulk(self.data, predicate=predicate)

    def time_bulk_query(self, predicate):
        self.df.sindex.query_bulk(self.df2.geometry, predicate=predicate)

    def time_query(self, predicate):
        for geo in self.data:
            self.df.sindex.query(geo, predicate=predicate)


class BenchNoArgs:
    def setup(self, *args):
        triangles = GeoSeries(
            [
                Polygon([(random.random(), random.random()) for _ in range(3)])
                for _ in range(100)
            ]
        )

        points = GeoSeries(
            [
                Point(x, y)
                for x, y in zip(np.random.random(1000), np.random.random(1000))
            ]
        )

        df1 = GeoDataFrame(
            {"val1": np.random.randn(len(triangles)), "geometry": triangles}
        )
        df2 = GeoDataFrame({"val1": np.random.randn(len(points)), "geometry": points})

        self.df, self.df2, self.data = df1, df2, df2.geometry.values.data
        self.bounds = [point.bounds for point in points]

    def time_index_creation(self, *args):
        self.df._invalidate_sindex()
        self.df._generate_sindex()

    def time_intersects(self, *args):
        for bounds in self.bounds:
            self.df.sindex.intersection(bounds)

    def time_intersects_objects(self, *args):
        for bounds in self.bounds:
            self.df.sindex.intersection(bounds, objects=True)
