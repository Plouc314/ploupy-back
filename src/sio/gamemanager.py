import uuid

from src.core import UserModel, GameConfig
from src.game import Game

from .models import GameSioModel, UserSioModel
from .sio import sio
from .job import JobManager


class GameManager:
    def __init__(self):
        self._games: dict[str, GameSioModel] = {}

    def get_game(
        self, gid: str | None = None, user: UserModel | None = None
    ) -> GameSioModel | None:
        """
        Get a sio game either by gid or by a sid (not necessarily connected),
        return None if game not found
        """
        if gid is not None:
            return self._games.get(gid, None)
        if user is not None:
            for game in self._games.values():
                for player in game.game.players.values():
                    if player.user.uid == user.uid:
                        return game
            return None
        return None

    def add_game(self, gid: str, game: Game, users: list[UserSioModel]) -> GameSioModel:
        """
        Build and add a new GameSioModel instance from the given game
        Return the GameSioModel
        """
        game_state = GameSioModel(gid=gid, game=game, users=users)
        self._games[gid] = game_state
        return game_state

    def link_user_to_game(self, gs: GameSioModel, user: UserSioModel):
        """
        - Make user enters the game room
        - Set user `gid` attribute
        - If not socket-io user in GameSioModel, add it
        """
        if not user in gs.users:
            gs.users.append(user)
        user.gid = gs.gid
        sio.enter_room(user.sid, room=gs.gid)

    async def create_game(self, users: list[UserSioModel], config: GameConfig):
        """
        Create a new Game instance
        - Make all users enters the game room
        - Broadcast the start_game event
        """
        gid = uuid.uuid4().hex

        job_manager = JobManager(gid)

        # create game
        game = Game(
            [user.user for user in users],
            job_manager,
            config,
            lambda g: self.end_game(gid),
        )
        gs = self.add_game(gid, game, users)

        # create room
        for user in users:
            self.link_user_to_game(gs, user)

        # broadcast start game event
        await sio.emit("start_game", game.model.dict(), to=gs.gid)

    def end_game(self, gid: str):
        """
        - Remove the game state from State
        - Make all users leave the game room
        - Reset game's users gid
        """
        gs = self.get_game(gid=gid)

        if gs is None:
            return

        # remove game from games
        self._games.pop(gid, None)

        # leave room
        for user in gs.users:
            user.gid = None
            sio.leave_room(user.sid, room=gid)

    def disconnect(self, user: UserSioModel):
        """
        Disconnect the (socket-io) user from the game
        NOTE: do NOT RESIGN the game for the user

        In case nobody is connected to the game anymore,
        end the game
        """
        game = self.get_game(gid=user.gid)
        if game is None:
            return

        # remove user from game users (NOTE: references mismatch so use sid)
        for u in game.users:
            if u.sid == user.sid:
                game.users.remove(u)
                break
            
        if len(game.users) == 0:
            game.game.end_game(notify_client=False)
