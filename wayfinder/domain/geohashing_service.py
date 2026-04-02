"""
Minimal geohash encoder/decoder — zero external dependencies.

Geohash precision controls the spatial grouping radius:
    Precision 6 ≈ 1.2km × 0.6km
    Precision 7 ≈ 153m  × 153m
    Precision 8 ≈  38m  ×  19m   (≈ 60–120 ft — good default)
    Precision 9 ≈   5m  ×   5m
"""

class Geohasher:
    _BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
    _DECODE_MAP = {c: i for i, c in enumerate(_BASE32)}

    def encode(self, lat: float, lng: float, precision: int = 8) -> str:
        """Encode a (lat, lng) pair into a geohash string."""
        lat_range, lng_range = [-90.0, 90.0], [-180.0, 180.0]
        geohash, bits, bit = [], 0, 0
        is_lng = True

        while len(geohash) < precision:
            if is_lng:
                mid = (lng_range[0] + lng_range[1]) / 2
                if lng >= mid:
                    bits = bits * 2 + 1
                    lng_range[0] = mid
                else:
                    bits = bits * 2
                    lng_range[1] = mid
            else:
                mid = (lat_range[0] + lat_range[1]) / 2
                if lat >= mid:
                    bits = bits * 2 + 1
                    lat_range[0] = mid
                else:
                    bits = bits * 2
                    lat_range[1] = mid
            is_lng = not is_lng
            bit += 1
            if bit == 5:
                geohash.append(self._BASE32[bits])
                bits, bit = 0, 0

        return "".join(geohash)


    def decode(self, geohash: str) -> tuple[float, float]:
        """Decode a geohash string into its center (lat, lng)."""
        lat_range, lng_range = [-90.0, 90.0], [-180.0, 180.0]
        is_lng = True

        for ch in geohash:
            val = self._DECODE_MAP[ch]
            for i in range(4, -1, -1):
                bit_val = (val >> i) & 1
                if is_lng:
                    mid = (lng_range[0] + lng_range[1]) / 2
                    if bit_val:
                        lng_range[0] = mid
                    else:
                        lng_range[1] = mid
                else:
                    mid = (lat_range[0] + lat_range[1]) / 2
                    if bit_val:
                        lat_range[0] = mid
                    else:
                        lat_range[1] = mid
                is_lng = not is_lng

        return (lat_range[0] + lat_range[1]) / 2, (lng_range[0] + lng_range[1]) / 2

    def neighbors(self, geohash: str) -> list[str]:
        lat, lng = self.decode(geohash)
        precision = len(geohash)
        dlat = 180.0 / (2 ** (2.5 * precision - 1))
        dlng = 360.0 / (2 ** (2.5 * precision))
        offsets = [
            (dlat, 0), (-dlat, 0), (0, dlng), (0, -dlng),
            (dlat, dlng), (dlat, -dlng), (-dlat, dlng), (-dlat, -dlng),
        ]
        return [self.encode(lat + o[0], lng + o[1], precision) for o in offsets]