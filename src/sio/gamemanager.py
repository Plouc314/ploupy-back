import uuid

from src.core import UserModel, GameModeModel
from src.game import Game, GameResultModel
from src.api import GameResultsAPI

from .client import client
from .models import GameResultsResponse, GameSioModel, UserSioModel
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

    def add_game(
        self, gid: str, game: Game, users: list[UserSioModel], mode: GameModeModel
    ) -> GameSioModel:
        """
        Build and add a new GameSioModel instance from the given game
        Return the GameSioModel
        """
        game_state = GameSioModel(gid=gid, mode=mode, game=game, users=users)
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

    async def create_game(self, users: list[UserSioModel], mode: GameModeModel):
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
            mode.config,
            lambda r, a: self.end_game(gid, r, a),
        )
        gs = self.add_game(gid, game, users, mode)

        # create room
        for user in users:
            self.link_user_to_game(gs, user)

        # broadcast start game event
        await sio.emit("start_game", game.model.dict(), to=gs.gid)

    async def end_game(self, gid: str, results: GameResultModel, aborted: bool):
        """
        - Post game results on api (if not aborted)
        - Broadcast game results to players
        - Remove the game state from State
        - Make all users leave the game room
        - Reset game's users gid
        """
        gs = self.get_game(gid=gid)

        if gs is None:
            return

        if aborted:
            mmrs = [0 for _ in results.ranking]
            mmr_diffs = [0 for _ in results.ranking]
        else:
            # notify api of game results
            response = client.post_game_result(
                    GameResultsAPI(gmid=gs.mode.id, ranking=[user.uid for user in results.ranking])
                )
            mmrs = response.mmrs
            mmr_diffs = response.mmr_diffs

        # build sio response (merge game/api data)
        response = GameResultsResponse(
            ranking=results.ranking,
            stats=results.stats,
            mmrs=mmrs,
            mmr_diffs=mmr_diffs,
        )

        # broadcast overall response
        await sio.emit("game_result", response.dict(), to=gid)

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
            game.game.end_game(aborted=True)
