from functools import partial
import time
from typing import Callable

import game_logic as gl
from src.models import core as _c, game as _g
from src.core import ActionException
from src.sio import JobManager

# setup rust logger
try:
    gl.setup_logger()
except BaseException:
    pass


class Game:
    def __init__(
        self,
        gid: str,
        users: list[_c.User],
        job_manager: JobManager,
        config: _c.GameConfig,
        on_end_game: Callable[[_g.GameResult, bool], None],
    ):
        self.gid = gid
        self.users = users  # game players
        self.job_manager = job_manager
        self.config = config

        # map: python id -> rust id
        self._ids_map = {u.uid: abs(hash(u.uid)) for u in users}
        self._game = gl.Game(list(self._ids_map.values()), config.dict())

        # if the game is finished
        self._ended = False

        # function called when the game ends
        self._on_end_game = on_end_game

        self._job_flag = True

        self._dead_players: list[_c.User] = []

        job = self.job_manager.make_job("game_state", self.job_run)
        job.start()

    async def job_run(self, jb: JobManager):
        ct = time.time()
        frame_times = []
        while True:
            await self.job_manager.sleep(1 / 60)

            if not self._job_flag:
                break

            t = time.time()
            dt, ct = t - ct, t
            frame_times.append(dt)

            state = self._game.run(dt)
            if state is None:
                continue

            self._notice_dead_players(state)

            if state["game_ended"]:
                self.end_game()
                break

            self._cast_rs_model(state)
            yield _g.GameState(**state)

        m = sum(frame_times) / len(frame_times)
        print(f"Mean frame time: {m*1000:.4f} ms")

    def is_player(self, uid: str) -> bool:
        """
        Return the if the user with `uid` is part of the
        players in the game
        """
        return uid in self._ids_map.keys()

    def _get_user(self, rid: int) -> _c.User:
        """
        Return the user with the given rust id
        """
        for u in self.users:
            if self._ids_map[u.uid] == rid:
                return u

    def _cast_rs_model(self, raw: dict):
        raw["gid"] = self.gid

        for ps in raw["players"]:
            user = self._get_user(ps.pop("id"))
            ps["uid"] = user.uid
            ps["username"] = user.username

            probe_states = []
            for fs in ps["factories"]:
                probe_states += fs.pop("probes")
            ps["probes"] = probe_states

        _map = raw.get("map")
        if _map is not None:
            for _tile in _map["tiles"]:
                if "owner_id" in _tile.keys():
                    _tile["owner"] = self._get_user(_tile.pop("owner_id")).username

    def _notice_dead_players(self, state: dict):
        """
        Notice dead players
        """
        for ps in state["players"]:
            if ps.get("death", None):
                self._dead_players.append(self._get_user(ps["id"]))

    def end_game(self, aborted: bool = False, delay: float = 0.5):
        """
        End the game (Will only be done once)

        - Build GameResults
        - Call `on_end_game` (in separate job)
        """
        if self._ended:
            return
        self._ended = True
        self._job_flag = False

        # ranking
        ranking = [
            u for u in self.users if u not in self._dead_players
        ] + self._dead_players[::-1]

        # stats
        raw_stats = self._game.get_stats()
        stats: list[_g.GamePlayerStats] = []
        for user in self.users:
            rid = self._ids_map[user.uid]
            stats.append(_g.GamePlayerStats(username=user.username, **raw_stats[rid]))

        game_results = _g.GameResult(ranking=ranking, stats=stats)

        # call on_end_game after a delay (for last GameState to reach client)
        # on_end_game is responsible to notify client
        # and overall clean up of game in sio server
        self.job_manager.execute(
            partial(self._on_end_game, game_results, aborted),
            delay=delay,
        )

    def action_resign_game(self, uid: str) -> None:
        """
        Make one player die

        Raise: ActionException
        """
        rid = self._ids_map.get(uid)
        if rid is None:
            raise ActionException(f"Invalid uid: '{uid}'")

        try:
            self._game.action_resign_game(rid)
        except ValueError as e:
            raise ActionException(str(e))

    def action_build_factory(self, uid: str, coord: _c.Point) -> None:
        """
        Build a factory at the given coord for the given player is possible

        Raise: ActionException
        """
        rid = self._ids_map.get(uid)
        if rid is None:
            raise ActionException(f"Invalid uid: '{uid}'")

        try:
            self._game.action_build_factory(rid, int(coord.x), int(coord.y))
        except ValueError as e:
            raise ActionException(str(e))

    def action_build_turret(self, uid: str, coord: _c.Point) -> None:
        """
        Build a turret at the given coord for the given player is possible

        Raise: ActionException
        """
        rid = self._ids_map.get(uid)
        if rid is None:
            raise ActionException(f"Invalid uid: '{uid}'")

        try:
            self._game.action_build_turret(rid, int(coord.x), int(coord.y))
        except ValueError as e:
            raise ActionException(str(e))

    def action_move_probes(self, uid: str, ids: list[str], target: _c.Point) -> None:
        """
        Change the target of the probes with the given `ids`

        Raise: ActionException
        """
        rid = self._ids_map.get(uid)
        if rid is None:
            raise ActionException(f"Invalid uid: '{uid}'")

        try:
            self._game.action_move_probes(
                rid, [int(id) for id in ids], int(target.x), int(target.y)
            )
        except ValueError as e:
            raise ActionException(str(e))

    def action_explode_probes(self, uid: str, ids: list[str]) -> None:
        """
        Explode the probes with the given `ids`
        """
        rid = self._ids_map.get(uid)
        if rid is None:
            raise ActionException(f"Invalid uid: '{uid}'")

        try:
            self._game.action_explode_probes(rid, [int(id) for id in ids])
        except ValueError as e:
            raise ActionException(str(e))

    def action_probes_attack(self, uid: str, ids: list[str]) -> None:
        """
        Make the probes with the given `ids` attack the opponents
        """
        rid = self._ids_map.get(uid)
        if rid is None:
            raise ActionException(f"Invalid uid: '{uid}'")

        try:
            self._game.action_probes_attack(rid, [int(id) for id in ids])
        except ValueError as e:
            raise ActionException(str(e))

    @property
    def model(self) -> _g.GameState:
        """
        Return the model (pydantic) representation of the instance
        """
        state = self._game.get_state()
        self._cast_rs_model(state)

        return _g.GameState(config=self.config, **state)
