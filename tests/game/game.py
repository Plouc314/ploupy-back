import unittest

import numpy as np


from src.core import UserModel, PointModel
from src.game import Game, GameConfig, ActionException


class GameTest(unittest.TestCase):

    def test_game(self):
        
        config = GameConfig(dim=PointModel(x=20, y=20), initial_money=10, factory_price=3)

        # create game
        users = [UserModel(username="bob"), UserModel(username="paul")]
        game = Game(users, config)

        for user in users:
            player = game.players.get(user.username, None)
            self.assertIsNotNone(player)
            self.assertEqual(user, player.user)
        
        p1, p2 = list(game.players.values())

        model = game.build_factory(p1, PointModel(x=0, y=0))
        self.assertIsNotNone(model)

        self.assertEqual(len(p1.factories), 1)
        factory = p1.factories[0]
        self.assertListEqual(factory.coord.tolist(), [0,0])
        
        try:
            model = game.build_factory(p2, PointModel(x=0, y=0))

            self.assertTrue(False, "Should have raise ActionException")
        except ActionException:
            pass

        