import uuid

from src.models import core, game as _g, sio as _s, api as _a

from src.game import Game

from .manager import Manager
from ..client import client
from ..sio import sio
from ..job import JobManager


class GameManager(Manager):
    """
    Manager of active games
    """

    def __init__(self):
        self._games: dict[str, _s.Game] = {}

    def _get_game_state(self, game: _s.Game, active: bool = True) -> _s.GameState:
        """
        Return the sio.Game casted to GameState
        """
        return _s.GameState(
            gid=game.gid,
            active=active,
            gmid=game.mode.id,
            users=[player.user for player in game.players],
        )

    def _is_user(self, users: list[_s.User], user: _s.User) -> bool:
        """
        Return if the `user` is in the list of `users`,
        based on their uids
        """
        for u in users:
            if u.user.uid == user.user.uid:
                return True
        return False

    def get_game(
        self, gid: str | None = None, user: core.User | None = None
    ) -> _s.Game | None:
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
        self, gid: str, game: Game, users: list[_s.User], mode: core.GameMode
    ) -> _s.Game:
        """
        Build and add a new sio.Game instance from the given game
        Return the sio.Game
        """
        game_state = _s.Game(
            gid=gid, mode=mode, game=game, players=users, spectators=[]
        )
        self._games[gid] = game_state
        return game_state

    async def connect(self):
        """
        Pass
        """

    def link_user_to_game(self, gs: _s.Game, user: _s.User):
        """
        Link a user to a game, the user may be a player of the game
        or not (a spectator)

        - Make user enters the game room
        - Set user `gid` attribute
        - If not socket-io user in sio.Game, add it
        """
        if gs.game.get_player(user.user.username) is not None:
            # link player
            if not self._is_user(gs.players, user):
                gs.players.append(user)
        else:
            # link spectator
            if not self._is_user(gs.spectators, user):
                gs.spectators.append(user)

        user.gid = gs.gid
        sio.enter_room(user.sid, room=gs.gid)

    async def create_game(self, users: list[_s.User], mode: core.GameMode):
        """
        Create a new Game instance
        - Make all users enters the game room
        - Broadcast the start_game event
        - Broadcast game state (GameManagerState)
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
        await sio.emit(
            "start_game", _s.responses.StartGame(gid=gs.gid).json(), to=gs.gid
        )

        # broadcast game state
        await sio.emit(
            "man_game_state",
            _s.responses.GameManagerState(games=[self._get_game_state(gs)]).json(),
        )

    async def end_game(self, gid: str, results: _g.GameResult, aborted: bool):
        """
        - Post game results on api (if not aborted)
        - Broadcast game results to players
        - Remove the game state from State
        - Make all users leave the game room
        - Reset game's users gid
        - Broadcast game state (GameManagerState)
        """
        gs = self.get_game(gid=gid)

        if gs is None:
            return

        mmrs = [0 for _ in results.ranking]
        mmr_diffs = [0 for _ in results.ranking]

        if not aborted:
            # notify api of game results
            response = await client.post_game_result(
                gmid=gs.mode.id, ranking=[user.uid for user in results.ranking]
            )
            if response is not None:
                mmrs = response.mmrs
                mmr_diffs = response.mmr_diffs

        # build sio response (merge game/api data)
        response = _s.responses.GameResults(
            ranking=results.ranking,
            stats=results.stats,
            mmrs=mmrs,
            mmr_diffs=mmr_diffs,
        )

        # broadcast overall response
        await sio.emit("game_result", response.json(), to=gid)

        # remove game from src.games
        self._games.pop(gid, None)

        # leave room
        for user in gs.players:
            user.gid = None
            sio.leave_room(user.sid, room=gid)
        for user in gs.spectators:
            user.gid = None
            sio.leave_room(user.sid, room=gid)

        # broadcast game state
        await sio.emit(
            "man_game_state",
            _s.responses.GameManagerState(
                games=[self._get_game_state(gs, active=False)]
            ).json(),
        )

    async def disconnect(self, user: _s.User):
        """
        Disconnect the sio.User from the game
        NOTE: do NOT RESIGN the game for the user

        In case nobody is connected to the game anymore,
        end the game
        """
        gs = self.get_game(gid=user.gid)
        if gs is None:
            return

        # NOTE: references mismatch so use sid
        # remove players user
        for u in gs.players:
            if u.sid == user.sid:
                gs.players.remove(u)
                break
        # remove spectator user
        for u in gs.spectators:
            if u.sid == user.sid:
                gs.spectators.remove(u)
                break

        if len(gs.players) == 0 and len(gs.spectators) == 0:
            gs.game.end_game(aborted=True)

    @property
    def state(self) -> _s.responses.GameManagerState:
        return _s.responses.GameManagerState(
            games=[self._get_game_state(game) for game in self._games.values()]
        )
