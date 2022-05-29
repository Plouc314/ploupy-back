import itertools
import functools
import numpy as np

from src.core import Coord


class Geometry:
    @staticmethod
    def translate(coords: set[Coord], vector: Coord) -> set[Coord]:
        """
        Return the set of `coords` each translated by `vector`

        Example:
            `translate([(1,0), (0,1)], (2,0)) -> [(3,0), (2,1)]`
        """
        return {(vector[0] + c[0], vector[1] + c[1]) for c in coords}

    @functools.lru_cache
    @staticmethod
    def _ring(distance: int) -> set[Coord]:
        """
        Actual implementation of `ring`
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

        coords = set()

        if distance == 0:
            coords.add((0, 0))
            return coords

        for moves in corners:
            combinations = itertools.combinations_with_replacement(moves, distance)

            for comb in combinations:
                flat = [0,0]
                for move in comb:
                    flat[0] += move[0]
                    flat[1] += move[1]
                coords.add(tuple(flat))

        return coords

    @functools.lru_cache
    @staticmethod
    def _square(distance: int) -> set[Coord]:
        """
        Actual implementation of `square`
        """
        coords = set()
        for dist in range(distance + 1):
            coords |= Geometry._ring(dist)
        return coords

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
        return Geometry.translate(Geometry._ring(distance), origin)

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
        return Geometry.translate(Geometry._square(distance), origin)
