import unittest

import numpy as np

from src.game.entity.factory import Factory


class EntityTest(unittest.TestCase):
    def test_position(self):

        pos = [1.3, 2]

        entity = Factory(None, pos)

        self.assertListEqual(entity.pos.tolist(), [1.3, 2])
        self.assertListEqual(entity.coord.tolist(), [1, 2])

        entity.coord = [1.3, 3]

        self.assertListEqual(entity.pos.tolist(), [1.3, 3])
        self.assertListEqual(entity.coord.tolist(), [1, 3])
