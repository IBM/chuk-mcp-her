"""Grid-based spatial index for BNG coordinate matching."""

from __future__ import annotations

import math
from typing import Any


class GridSpatialIndex:
    """Grid-based spatial index for efficient nearest-neighbour search.

    Divides the BNG coordinate space into square cells. Each cell
    stores a list of assets whose easting/northing fall within it.
    For a query point, only the 3x3 neighbourhood of cells is checked,
    reducing O(n*m) to O(n+m) amortised.

    Args:
        cell_size_m: Grid cell size in metres. Should be >= the maximum
            search radius to ensure the 3x3 neighbourhood covers it.
    """

    def __init__(self, cell_size_m: float = 200.0) -> None:
        if cell_size_m <= 0:
            raise ValueError("cell_size_m must be positive")
        self._cell_size = cell_size_m
        self._grid: dict[tuple[int, int], list[dict[str, Any]]] = {}
        self._count = 0

    def _cell_key(self, easting: float, northing: float) -> tuple[int, int]:
        """Compute grid cell key for a coordinate."""
        return (
            int(math.floor(easting / self._cell_size)),
            int(math.floor(northing / self._cell_size)),
        )

    def insert(self, asset: dict[str, Any]) -> bool:
        """Insert an asset into the index.

        Returns False if the asset has no valid easting/northing.
        """
        e = asset.get("easting")
        n = asset.get("northing")
        if e is None or n is None:
            return False
        key = self._cell_key(e, n)
        if key not in self._grid:
            self._grid[key] = []
        self._grid[key].append(asset)
        self._count += 1
        return True

    def build(self, assets: list[dict[str, Any]]) -> int:
        """Bulk-insert a list of assets. Returns count inserted."""
        inserted = 0
        for asset in assets:
            if self.insert(asset):
                inserted += 1
        return inserted

    def nearest(
        self, easting: float, northing: float, max_distance: float
    ) -> tuple[dict[str, Any] | None, float]:
        """Find the nearest asset to the given point within max_distance.

        Checks the 3x3 neighbourhood of cells around the query point.

        Returns:
            Tuple of (nearest_asset, distance) or (None, inf).
        """
        cx, cy = self._cell_key(easting, northing)
        best_dist = float("inf")
        best_asset: dict[str, Any] | None = None

        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cell = self._grid.get((cx + dx, cy + dy))
                if cell is None:
                    continue
                for asset in cell:
                    ae = asset["easting"]
                    an = asset["northing"]
                    d = math.sqrt((easting - ae) ** 2 + (northing - an) ** 2)
                    if d < best_dist:
                        best_dist = d
                        best_asset = asset

        if best_dist > max_distance:
            return None, float("inf")
        return best_asset, best_dist

    @property
    def count(self) -> int:
        """Number of assets in the index."""
        return self._count

    @property
    def cell_count(self) -> int:
        """Number of non-empty grid cells."""
        return len(self._grid)
