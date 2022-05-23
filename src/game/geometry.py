import itertools
import numpy as np

from src.core import Coord


class Geometry:
    @staticmethod
    def ring(origin: Coord, distance: int) -> set[Coord]:
        """
        Return the coordinates at `distance` of the origin,
        in a square shape:
        ```
        scope: 1 & 2 & 3
                                          *
                          *             *   *
              *         *   *         *       *
            * O *     *   O   *     *     O     *
              *         *   *         *       *
                          *             *   *
                                          *
        ```
        """
        # directions to choose from
        corners = [
            [
                (1, 0),
                (0, 1),
            ],
            [
                (1, 0),
                (0, -1),
            ],
            [
                (-1, 0),
                (0, 1),
            ],
            [
                (-1, 0),
                (0, -1),
            ],
        ]

        origin = np.array(origin, dtype=int)
        coords = set()

        if distance == 0:
            coords.add(tuple(origin))
            return coords

        for moves in corners:
            combinations = itertools.combinations_with_replacement(moves, distance)

            for comb in combinations:
                flat = origin.copy()
                for move in comb:
                    flat[0] += move[0]
                    flat[1] += move[1]
                coords.add(tuple(flat))

        return coords

    @staticmethod
    def square(origin: Coord, distance: int) -> set[Coord]:
        """
        Return the coordinates from `distance` of the origin,
        in a square shape:
        ```
        scope: 1 & 2 & 3
                                          *
                          *             * * *
              *         * * *         * * * * *
            * O *     * * O * *     * * * O * * *
              *         * * *         * * * * *
                          *             * * *
                                          *
        ```
        """
        coords = set()
        for dist in range(distance + 1):
            coords |= Geometry.ring(origin, dist)
        return coords
