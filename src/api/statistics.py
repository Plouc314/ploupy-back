from datetime import datetime

from firebase_admin import db

from src.models import core as _c
from src.core import FirebaseException

from .firebase import Firebase


class Statistics:
    """
    Manage statistics related operations
    """

    def __init__(self, firebase: Firebase):

        self._firebase = firebase
        self._cache_mmrs: dict[str, _c.UserMMRs] = {}
        self._cache_stats: dict[str, _c.UserStats] = {}

    def _cast_date(self, date: datetime) -> str:
        """
        Cast a datetime instance to db format
        
        With only HH:MM:SS and no timezone information
        (date should still be in utc timezone)
        """
        return date.isoformat(timespec="seconds")

    def _build_user_mmrs(self, data: dict) -> _c.UserMMRs:
        """
        Build a UserMMRs instance

        Args:
            - data: (`schemas.d.ts`): UserStats.mmrs
        """
        default_mmr = 100
        for mode in self._firebase.get_game_modes():
            if not mode.id in data.keys():
                data[mode.id] = default_mmr

        return _c.UserMMRs(mmrs=data)

    def _cast_user_mmrs(self, mmrs: _c.UserMMRs) -> dict:
        """
        Cast UserMMRs instance to db format (`UserStats.mmrs`)
        """
        return mmrs.mmrs

    def _build_game_stats(self, date: str, data: dict) -> _c.GameStats:
        """
        Build a GameStats instance

        Args:
            - date (`schemas.d.ts`): Datetime
            - data (`schemas.d.ts`): GameStats
        """
        try:
            date = datetime.fromisoformat(date)
        except ValueError as e:
            raise FirebaseException(f"Invalid date: '{date}'")

        return _c.GameStats(date=date, mmr=data["mmr"], ranking=data["ranking"])

    def _cast_game_stats(self, gstats: _c.GameStats) -> dict:
        """
        Cast GameStats instance to db format (`GameStats`)
        """
        return {"mmr": gstats.mmr, "ranking": gstats.ranking}

    def _build_game_mode_history(self, gmid: str, data: dict) -> _c.GameModeHistory:
        """
        Build a GameModeHistory instance

        Args:
            - gmid: game mode id
            - data: (`schemas.d.ts`): GameHistory
        """
        mode = self._firebase.get_game_mode(id=gmid)

        if mode is None:
            raise FirebaseException(f"Invalid gmid: '{gmid}'")

        history: _c.GameStats = []

        for date, raw_gstats in data.items():

            gstats = self._build_game_stats(date, raw_gstats)
            history.append(gstats)

        return _c.GameModeHistory(mode=mode, history=history)

    def _cast_game_mode_history(self, gmhist: _c.GameModeHistory) -> dict:
        """
        Cast GameStats instance to db format (`GameHistory`)
        """
        data = {}
        for gstats in gmhist.history:
            date = self._cast_date(gstats.date)
            data[date] = self._cast_game_stats(gstats)

        return data

    def _build_user_stats(self, data: dict) -> _c.UserStats:
        """
        Build a UserStats instance

        Args:
            - data (`schemas.d.ts`): UserStats
        """
        mmrs = self._build_user_mmrs(data["mmrs"])

        stats: dict[str, _c.GameModeHistory] = {}

        for gmid, data in data["history"].items():
            gmhist = self._build_game_mode_history(gmid, data)
            stats[gmid] = gmhist

        # add default values for missing game histories
        for mode in self._firebase.get_game_modes():
            if not mode.id in stats.keys():
                stats[mode.id] = self._build_game_mode_history(mode.id, {})

        return _c.UserStats(mmrs=mmrs, history=stats)

    def _cast_user_stats(self, ustats: _c.UserStats) -> dict:
        """
        Cast UserStats instance to db format (`UserStats`)
        """
        return {
            "mmrs": self._cast_user_mmrs(ustats.mmrs),
            "history": {
                gmid: self._cast_game_mode_history(gmhist)
                for gmid, gmhist in ustats.history.items()
            },
        }

    def get_user_mmrs(self, uid: str) -> _c.UserMMRs:
        """
        Get the user current MMRs from the db

        Assuming the uid is valid.
        """
        # look in cache
        if uid in self._cache_mmrs.keys():
            return self._cache_mmrs[uid]

        # fetch data
        data: dict = db.reference(f"/stats/{uid}/mmrs").get()

        # case: the user has no stored mmr
        if data is None:
            data = {}

        mmrs = self._build_user_mmrs(data)

        # update cache
        self._cache_mmrs[uid] = mmrs

        return mmrs

    def update_user_mmrs(self, uid: str, mmrs: _c.UserMMRs):
        """
        Update the user MMRs of the user on the db

        Assuming the uid is valid.
        """
        data = self._cast_user_mmrs(mmrs)

        # push to db
        db.reference(f"/stats/{uid}/mmrs").set(data)

        # update cache
        self._cache_mmrs[uid] = mmrs

    def get_user_stats(self, uid: str) -> _c.UserStats:
        """
        Get the user stats from the db

        Assuming the uid is valid.
        """
        # look in cache
        if uid in self._cache_stats.keys():
            return self._cache_stats[uid]

        # fetch data
        data: dict = db.reference(f"/stats/{uid}").get()

        if data is None:
            data = {}

        # add necessary default values
        data["mmrs"] = data.get("mmrs", {})
        data["history"] = data.get("history", {})

        ustats = self._build_user_stats(data)

        # update cache
        self._cache_stats[uid] = ustats
        self._cache_mmrs[uid] = ustats.mmrs

        return ustats

    def push_game_stats(self, uid: str, gmid: str, gstats: _c.GameStats):
        """
        Add the given game stats to the db.
        In case the game already exists, override it.

        Note: do NOT update the user mmr

        Assuming the uid is valid.
        """
        mode = self._firebase.get_game_mode(id=gmid)

        if mode is None:
            raise FirebaseException(f"Invalid gmid: '{gmid}'")

        date = self._cast_date(gstats.date)
        gdata = self._cast_game_stats(gstats)

        # push to db
        db.reference(f"/stats/{uid}/history/{gmid}/{date}").set(gdata)

        # update cache
        if uid in self._cache_stats.keys():

            # only had game if not existing in the history
            gmhist = self._cache_stats[uid].history[gmid]
            for _gstats in gmhist.history:
                if _gstats.date == gstats.date:
                    break
            else:
                gmhist.history.append(gstats)

    def get_game_mode_stats(
        self, uid: str, gmhist: _c.GameModeHistory
    ) -> _c.ExtendedGameModeStats:
        """
        Build the ExtendedGameModeStats instance given a GameModeHistory

        Note: return an instance with default values in case `uid` is invalid
        """
        # initialize position occurences at 0
        scores = [0 for i in range(gmhist.mode.config.n_player)]

        dates: list[str] = []
        mmr_hist: list[int] = []

        for gstats in gmhist.history:

            if not uid in gstats.ranking:
                continue

            score_idx = gstats.ranking.index(uid)
            date = self._cast_date(gstats.date)
            mmr = gstats.mmr

            scores[score_idx] += 1
            dates.append(date)
            mmr_hist.append(mmr)

        return _c.ExtendedGameModeStats(
            mode=gmhist.mode,
            scores=scores,
            dates=dates,
            mmr_hist=mmr_hist,
        )
