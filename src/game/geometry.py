import itertools
import numpy as np

from src.core import Coord


def expansion(origin: Coord, scope: int) -> set[Coord]:
    """
    Return the coordinates surrounding the origin (included),
    in a square shape:
    ```
    scope = 1:
        *
      * O *
        *
    scope = 2:
          *
        * * *
      * * O * *
        * * *
          *
    ```
    """
    # directions to choose from
    moves = [
        (1, 0),
        (-1, 0),
        (0, 1),
        (0, -1),
    ]

    origin = np.array(origin, dtype=int)
    coords = set()

    # add the origin
    coords.add(tuple(origin))

    for l in range(scope):
        combinations = itertools.combinations_with_replacement(moves, l + 1)

        for comb in combinations:
            flat = origin
            for move in comb:
                flat[0] += move[0]
                flat[1] += move[1]
            coords.add(tuple(flat))

    return coords