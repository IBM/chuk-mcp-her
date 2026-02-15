"""
BNG (EPSG:27700) to/from WGS84 (EPSG:4326) coordinate conversion.

Provides basic Helmert transformation (~5m accuracy) with optional
pyproj fallback for sub-metre accuracy when installed.

Reference points used for validation:
    Tower of London: E=533500 N=180500 -> 51.5081N, 0.0759W
    Stonehenge:      E=412200 N=142400 -> 51.1789N, 1.8262W
"""

from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)

# Try pyproj for accurate conversion; fall back to Helmert approximation
_transformer_to_wgs84 = None
_transformer_to_bng = None

try:
    from pyproj import Transformer

    _transformer_to_wgs84 = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
    _transformer_to_bng = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)
    logger.info("Using pyproj for coordinate conversion (sub-metre accuracy)")
except ImportError:
    logger.info(
        "pyproj not installed; using Helmert approximation (~5m accuracy). "
        "Install pyproj for better precision: pip install pyproj"
    )


# ============================================================================
# Helmert transformation constants (OSGB36 <-> WGS84)
# ============================================================================

# Airy 1830 ellipsoid (OSGB36)
_AIRY_A = 6377563.396
_AIRY_B = 6356256.909
_AIRY_E2 = 1 - (_AIRY_B * _AIRY_B) / (_AIRY_A * _AIRY_A)

# GRS80 ellipsoid (WGS84)
_GRS80_A = 6378137.0
_GRS80_B = 6356752.314140
_GRS80_E2 = 1 - (_GRS80_B * _GRS80_B) / (_GRS80_A * _GRS80_A)

# National Grid origin
_E0 = 400000.0
_N0 = -100000.0
_F0 = 0.9996012717
_PHI0 = math.radians(49.0)
_LAMBDA0 = math.radians(-2.0)


def _bng_to_osgb36(easting: float, northing: float) -> tuple[float, float]:
    """Convert BNG easting/northing to OSGB36 lat/lon (radians)."""
    a = _AIRY_A
    b = _AIRY_B
    e2 = _AIRY_E2
    n = (a - b) / (a + b)
    n2 = n * n
    n3 = n * n * n

    phi = _PHI0
    M = 0.0

    # Iterate to find phi
    while True:
        phi = (northing - _N0 - M) / (a * _F0) + phi
        M = (
            b
            * _F0
            * (
                (1 + n + 5 / 4 * n2 + 5 / 4 * n3) * (phi - _PHI0)
                - (3 * n + 3 * n2 + 21 / 8 * n3) * math.sin(phi - _PHI0) * math.cos(phi + _PHI0)
                + (15 / 8 * n2 + 15 / 8 * n3)
                * math.sin(2 * (phi - _PHI0))
                * math.cos(2 * (phi + _PHI0))
                - 35 / 24 * n3 * math.sin(3 * (phi - _PHI0)) * math.cos(3 * (phi + _PHI0))
            )
        )
        if abs(northing - _N0 - M) < 0.00001:
            break

    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)
    tan_phi = math.tan(phi)

    nu = a * _F0 / math.sqrt(1 - e2 * sin_phi * sin_phi)
    rho = a * _F0 * (1 - e2) / math.pow(1 - e2 * sin_phi * sin_phi, 1.5)
    eta2 = nu / rho - 1

    VII = tan_phi / (2 * rho * nu)
    VIII = tan_phi / (24 * rho * nu**3) * (5 + 3 * tan_phi**2 + eta2 - 9 * tan_phi**2 * eta2)
    IX = tan_phi / (720 * rho * nu**5) * (61 + 90 * tan_phi**2 + 45 * tan_phi**4)
    X = 1 / (cos_phi * nu)
    XI = 1 / (cos_phi * 6 * nu**3) * (nu / rho + 2 * tan_phi**2)
    XII = 1 / (cos_phi * 120 * nu**5) * (5 + 28 * tan_phi**2 + 24 * tan_phi**4)
    XIIA = (
        1
        / (cos_phi * 5040 * nu**7)
        * (61 + 662 * tan_phi**2 + 1320 * tan_phi**4 + 720 * tan_phi**6)
    )

    dE = easting - _E0

    lat = phi - VII * dE**2 + VIII * dE**4 - IX * dE**6
    lon = _LAMBDA0 + X * dE - XI * dE**3 + XII * dE**5 - XIIA * dE**7

    return lat, lon


def _helmert_osgb36_to_wgs84(lat_rad: float, lon_rad: float) -> tuple[float, float]:
    """Apply Helmert transformation from OSGB36 to WGS84."""
    # Helmert parameters (OSGB36 -> WGS84)
    tx = 446.448
    ty = -125.157
    tz = 542.060
    s = -20.4894e-6
    rx = math.radians(0.1502 / 3600)
    ry = math.radians(0.2470 / 3600)
    rz = math.radians(0.8421 / 3600)

    sin_lat = math.sin(lat_rad)
    cos_lat = math.cos(lat_rad)
    sin_lon = math.sin(lon_rad)
    cos_lon = math.cos(lon_rad)

    nu = _AIRY_A / math.sqrt(1 - _AIRY_E2 * sin_lat * sin_lat)

    x1 = nu * cos_lat * cos_lon
    y1 = nu * cos_lat * sin_lon
    z1 = nu * (1 - _AIRY_E2) * sin_lat

    x2 = tx + (1 + s) * x1 + (-rz) * y1 + ry * z1
    y2 = ty + rz * x1 + (1 + s) * y1 + (-rx) * z1
    z2 = tz + (-ry) * x1 + rx * y1 + (1 + s) * z1

    p = math.sqrt(x2 * x2 + y2 * y2)
    lat = math.atan2(z2, p * (1 - _GRS80_E2))

    for _ in range(10):
        nu2 = _GRS80_A / math.sqrt(1 - _GRS80_E2 * math.sin(lat) ** 2)
        lat = math.atan2(z2 + _GRS80_E2 * nu2 * math.sin(lat), p)

    lon = math.atan2(y2, x2)
    return math.degrees(lat), math.degrees(lon)


def _wgs84_to_osgb36_helmert(lat_deg: float, lon_deg: float) -> tuple[float, float]:
    """Apply inverse Helmert transformation from WGS84 to OSGB36."""
    tx = -446.448
    ty = 125.157
    tz = -542.060
    s = 20.4894e-6
    rx = math.radians(-0.1502 / 3600)
    ry = math.radians(-0.2470 / 3600)
    rz = math.radians(-0.8421 / 3600)

    lat_rad = math.radians(lat_deg)
    lon_rad = math.radians(lon_deg)

    sin_lat = math.sin(lat_rad)
    cos_lat = math.cos(lat_rad)
    sin_lon = math.sin(lon_rad)
    cos_lon = math.cos(lon_rad)

    nu = _GRS80_A / math.sqrt(1 - _GRS80_E2 * sin_lat * sin_lat)

    x1 = nu * cos_lat * cos_lon
    y1 = nu * cos_lat * sin_lon
    z1 = nu * (1 - _GRS80_E2) * sin_lat

    x2 = tx + (1 + s) * x1 + (-rz) * y1 + ry * z1
    y2 = ty + rz * x1 + (1 + s) * y1 + (-rx) * z1
    z2 = tz + (-ry) * x1 + rx * y1 + (1 + s) * z1

    p = math.sqrt(x2 * x2 + y2 * y2)
    lat = math.atan2(z2, p * (1 - _AIRY_E2))

    for _ in range(10):
        nu2 = _AIRY_A / math.sqrt(1 - _AIRY_E2 * math.sin(lat) ** 2)
        lat = math.atan2(z2 + _AIRY_E2 * nu2 * math.sin(lat), p)

    lon = math.atan2(y2, x2)
    return lat, lon


def _osgb36_to_bng(lat_rad: float, lon_rad: float) -> tuple[float, float]:
    """Convert OSGB36 lat/lon (radians) to BNG easting/northing."""
    a = _AIRY_A
    b = _AIRY_B
    e2 = _AIRY_E2
    n = (a - b) / (a + b)
    n2 = n * n
    n3 = n * n * n

    sin_phi = math.sin(lat_rad)
    cos_phi = math.cos(lat_rad)
    tan_phi = math.tan(lat_rad)

    nu = a * _F0 / math.sqrt(1 - e2 * sin_phi * sin_phi)
    rho = a * _F0 * (1 - e2) / math.pow(1 - e2 * sin_phi * sin_phi, 1.5)
    eta2 = nu / rho - 1

    M = (
        b
        * _F0
        * (
            (1 + n + 5 / 4 * n2 + 5 / 4 * n3) * (lat_rad - _PHI0)
            - (3 * n + 3 * n2 + 21 / 8 * n3) * math.sin(lat_rad - _PHI0) * math.cos(lat_rad + _PHI0)
            + (15 / 8 * n2 + 15 / 8 * n3)
            * math.sin(2 * (lat_rad - _PHI0))
            * math.cos(2 * (lat_rad + _PHI0))
            - 35 / 24 * n3 * math.sin(3 * (lat_rad - _PHI0)) * math.cos(3 * (lat_rad + _PHI0))
        )
    )

    t_I = M + _N0
    t_II = nu / 2 * sin_phi * cos_phi
    t_III = nu / 24 * sin_phi * cos_phi**3 * (5 - tan_phi**2 + 9 * eta2)
    t_IIIA = nu / 720 * sin_phi * cos_phi**5 * (61 - 58 * tan_phi**2 + tan_phi**4)
    t_IV = nu * cos_phi
    t_V = nu / 6 * cos_phi**3 * (nu / rho - tan_phi**2)
    t_VI = (
        nu
        / 120
        * cos_phi**5
        * (5 - 18 * tan_phi**2 + tan_phi**4 + 14 * eta2 - 58 * tan_phi**2 * eta2)
    )

    dL = lon_rad - _LAMBDA0

    easting = _E0 + t_IV * dL + t_V * dL**3 + t_VI * dL**5
    northing = t_I + t_II * dL**2 + t_III * dL**4 + t_IIIA * dL**6

    return easting, northing


# ============================================================================
# Public API
# ============================================================================


def bng_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """Convert BNG easting/northing to WGS84 (lat, lon).

    Returns:
        Tuple of (latitude, longitude) in decimal degrees.
    """
    if _transformer_to_wgs84 is not None:
        lon, lat = _transformer_to_wgs84.transform(easting, northing)
        return lat, lon

    lat_rad, lon_rad = _bng_to_osgb36(easting, northing)
    return _helmert_osgb36_to_wgs84(lat_rad, lon_rad)


def wgs84_to_bng(lat: float, lon: float) -> tuple[float, float]:
    """Convert WGS84 lat/lon to BNG (easting, northing).

    Returns:
        Tuple of (easting, northing) in metres.
    """
    if _transformer_to_bng is not None:
        easting, northing = _transformer_to_bng.transform(lon, lat)
        return easting, northing

    osgb_lat_rad, osgb_lon_rad = _wgs84_to_osgb36_helmert(lat, lon)
    return _osgb36_to_bng(osgb_lat_rad, osgb_lon_rad)


def bbox_wgs84_to_bng(
    min_lon: float, min_lat: float, max_lon: float, max_lat: float
) -> tuple[float, float, float, float]:
    """Convert a WGS84 bounding box to BNG.

    Args:
        min_lon, min_lat, max_lon, max_lat: WGS84 bounds.

    Returns:
        Tuple of (xmin, ymin, xmax, ymax) in BNG metres.
    """
    e1, n1 = wgs84_to_bng(min_lat, min_lon)
    e2, n2 = wgs84_to_bng(max_lat, max_lon)
    return min(e1, e2), min(n1, n2), max(e1, e2), max(n1, n2)


def bbox_bng_to_wgs84(
    xmin: float, ymin: float, xmax: float, ymax: float
) -> tuple[float, float, float, float]:
    """Convert a BNG bounding box to WGS84.

    Returns:
        Tuple of (min_lon, min_lat, max_lon, max_lat).
    """
    lat1, lon1 = bng_to_wgs84(xmin, ymin)
    lat2, lon2 = bng_to_wgs84(xmax, ymax)
    return min(lon1, lon2), min(lat1, lat2), max(lon1, lon2), max(lat1, lat2)


def point_buffer_bng(
    easting: float, northing: float, radius_m: float
) -> tuple[float, float, float, float]:
    """Create a BNG bounding box around a point.

    Returns:
        Tuple of (xmin, ymin, xmax, ymax) in BNG metres.
    """
    return (
        easting - radius_m,
        northing - radius_m,
        easting + radius_m,
        northing + radius_m,
    )


def distance_m(e1: float, n1: float, e2: float, n2: float) -> float:
    """Euclidean distance between two BNG points in metres."""
    return math.sqrt((e2 - e1) ** 2 + (n2 - n1) ** 2)


def bearing_deg(e1: float, n1: float, e2: float, n2: float) -> float:
    """Bearing from point 1 to point 2 in BNG, in degrees (0=N, 90=E)."""
    angle = math.degrees(math.atan2(e2 - e1, n2 - n1))
    return angle % 360


# ============================================================================
# OS National Grid Reference Parser
# ============================================================================

# Two-letter prefix -> (base_easting, base_northing) in metres
_GRID_LETTERS: dict[str, tuple[int, int]] = {
    "SV": (0, 0),
    "SW": (100000, 0),
    "SX": (200000, 0),
    "SY": (300000, 0),
    "SZ": (400000, 0),
    "TV": (500000, 0),
    "TW": (600000, 0),
    "SQ": (0, 100000),
    "SR": (100000, 100000),
    "SS": (200000, 100000),
    "ST": (300000, 100000),
    "SU": (400000, 100000),
    "TQ": (500000, 100000),
    "TR": (600000, 100000),
    "SL": (0, 200000),
    "SM": (100000, 200000),
    "SN": (200000, 200000),
    "SO": (300000, 200000),
    "SP": (400000, 200000),
    "TL": (500000, 200000),
    "TM": (600000, 200000),
    "SF": (0, 300000),
    "SG": (100000, 300000),
    "SH": (200000, 300000),
    "SJ": (300000, 300000),
    "SK": (400000, 300000),
    "TF": (500000, 300000),
    "TG": (600000, 300000),
    "SA": (0, 400000),
    "SB": (100000, 400000),
    "SC": (200000, 400000),
    "SD": (300000, 400000),
    "SE": (400000, 400000),
    "TA": (500000, 400000),
    "TB": (600000, 400000),
    "NV": (0, 500000),
    "NW": (100000, 500000),
    "NX": (200000, 500000),
    "NY": (300000, 500000),
    "NZ": (400000, 500000),
    "OV": (500000, 500000),
    "OW": (600000, 500000),
    "NQ": (0, 600000),
    "NR": (100000, 600000),
    "NS": (200000, 600000),
    "NT": (300000, 600000),
    "NU": (400000, 600000),
    "OQ": (500000, 600000),
    "OR": (600000, 600000),
    "NL": (0, 700000),
    "NM": (100000, 700000),
    "NN": (200000, 700000),
    "NO": (300000, 700000),
    "NP": (400000, 700000),
    "NF": (0, 800000),
    "NG": (100000, 800000),
    "NH": (200000, 800000),
    "NJ": (300000, 800000),
    "NK": (400000, 800000),
    "NA": (0, 900000),
    "NB": (100000, 900000),
    "NC": (200000, 900000),
    "ND": (300000, 900000),
    "HW": (100000, 1000000),
    "HX": (200000, 1000000),
    "HY": (300000, 1000000),
    "HZ": (400000, 1000000),
    "HT": (300000, 1100000),
    "HU": (400000, 1100000),
    "HP": (400000, 1200000),
}


def grid_ref_to_bng(grid_ref: str) -> tuple[float, float]:
    """Convert an OS National Grid reference to BNG easting/northing.

    Accepts formats: ``"TL 905 085"`` (6-figure), ``"TL905085"``
    (no spaces), ``"TL 9050 0850"`` (8-figure), ``"TL 90500 08500"``
    (10-figure).

    Args:
        grid_ref: OS National Grid reference string.

    Returns:
        Tuple of (easting, northing) in BNG metres.

    Raises:
        ValueError: If the grid reference format is not recognised.
    """
    cleaned = grid_ref.strip().upper()
    if len(cleaned) < 4:
        raise ValueError(f"Invalid grid reference: '{grid_ref}'")

    prefix = cleaned[:2]
    if prefix not in _GRID_LETTERS:
        raise ValueError(f"Invalid grid reference prefix: '{prefix}'")

    base_e, base_n = _GRID_LETTERS[prefix]

    # Extract digits only (strip spaces)
    digits = cleaned[2:].replace(" ", "")
    if not digits or not digits.isdigit():
        raise ValueError(f"Invalid grid reference digits: '{grid_ref}'")
    if len(digits) % 2 != 0:
        raise ValueError(f"Grid reference must have even number of digits: '{grid_ref}'")

    half = len(digits) // 2
    e_digits = digits[:half]
    n_digits = digits[half:]

    # Scale to metres: 1 digit = 10km, 2 = 1km, 3 = 100m, 4 = 10m, 5 = 1m
    scale = 10 ** (5 - half)
    offset_e = int(e_digits) * scale
    offset_n = int(n_digits) * scale

    return float(base_e + offset_e), float(base_n + offset_n)
