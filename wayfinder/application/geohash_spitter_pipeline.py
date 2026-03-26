from collections import defaultdict
from wayfinder.domain.geohashing_service import Geohasher


class GeohasherSplittingPipeline:
    """
    Groups GeoJSON LineString features into geohash buckets, keeping
    topologically connected segments (shared endpoints) in the same bucket.
    """

    def __init__(self, precision: int = 8, skip_closed: bool = True):
        """
        Args:
            precision:   Geohash precision (default 8 ≈ 38m × 19m).
            skip_closed: Drop features where Status != "Open" (default True).
        """
        self._geohasher = Geohasher()
        self.precision = precision
        self.skip_closed = skip_closed

    def run(self, data: dict) -> dict[str, list]:
        """
        Args:
            data: A GeoJSON FeatureCollection dict.

        Returns:
            { geohash_string: [feature, ...] }
        """
        features = data.get("features", [])

        if self.skip_closed:
            features = [
                f for f in features
                if f.get("properties", {}).get("Status") == "Open"
            ]

        components = self._build_components(features)

        chunks: dict[str, list] = defaultdict(list)

        for component in components:
            lat, lon = self._component_centroid(features, component)
            key = self._geohasher.encode(lat, lon, self.precision)
            for i in component:
                chunks[key].append(features[i])

        return dict(chunks)

    def _build_components(self, features: list) -> list[list[int]]:
        """
        Union-Find over feature indices. Two features are connected if they
        share an endpoint coordinate (within ~1cm rounding tolerance).
        Returns a list of components, each a list of feature indices.
        """
        parent = list(range(len(features)))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            a, b = find(a), find(b)
            if a != b:
                parent[b] = a

        endpoint_index: dict[tuple, list[int]] = defaultdict(list)
        for i, feature in enumerate(features):
            coords = feature["geometry"]["coordinates"]
            geom_type = feature["geometry"]["type"]
            if geom_type == "MultiLineString":
                # Flatten: take first point of first line and last point of last line
                endpoints = (coords[0][0], coords[-1][-1])
            else:
                endpoints = (coords[0], coords[-1])
            for coord in endpoints:
                endpoint_index[self._coord_key(coord)].append(i)

        for indices in endpoint_index.values():
            for j in range(1, len(indices)):
                union(indices[0], indices[j])

        groups: dict[int, list[int]] = defaultdict(list)
        for i in range(len(features)):
            groups[find(i)].append(i)

        return list(groups.values())

    @staticmethod
    def _coord_key(coord: list) -> tuple:
        """Round to ~1cm precision to treat near-identical endpoints as the same node."""
        return (round(coord[0], 7), round(coord[1], 7))

    @staticmethod
    def _centroid(coordinates: list) -> tuple[float, float]:
        lons = [c[0] for c in coordinates]
        lats = [c[1] for c in coordinates]
        return sum(lats) / len(lats), sum(lons) / len(lons)

    def _component_centroid(self, features: list, indices: list[int]) -> tuple[float, float]:
        """Mean centroid across all segments in a component."""
        lats, lons = [], []
        for i in indices:
            geom = features[i]["geometry"]
            coords = geom["coordinates"]
            if geom["type"] == "MultiLineString":
                coords = [pt for line in coords for pt in line]
            lat, lon = self._centroid(coords)
            lats.append(lat)
            lons.append(lon)
        return sum(lats) / len(lats), sum(lons) / len(lons)