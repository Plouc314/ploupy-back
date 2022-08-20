from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..core.exceptions import BotCreationException, FirebaseException

from src.models import core as _c, api as _a
from src.core import AuthException, ALLOWED_ORIGINS

import src.api.mmrsystem as mmrsystem
from .firebase import Firebase
from .statistics import Statistics


# app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

firebase = Firebase()
statistics = Statistics(firebase)


@app.get("/ping")
def ping():
    return "Hello world!"


@app.get("/api/user-auth")
def user_auth(
    firebase_jwt: str | None = None, bot_jwt: str | None = None
) -> _a.responses.UserAuth:
    """
    Verify the given id token and if valid,
    return the corresponding uid
    """
    if firebase_jwt is not None:
        uid = firebase.auth_firebase_jwt(firebase_jwt)

        if uid is None:
            return _c.Response(success=False, msg="Invalid web client id token.")

    elif bot_jwt is not None:
        try:
            uid = firebase.auth_bot_jwt(bot_jwt)
        except AuthException as e:
            return _c.Response(success=False, msg=str(e))
    else:
        return _c.Response(success=False, msg="No id token given.")

    return _a.responses.UserAuth(uid=uid)


@app.get("/api/user-data")
def user_data(
    uid: str | None = None, username: str | None = None
) -> _a.responses.UserData:
    """
    Return the user data corresponding to the given uid
    """
    print(f"{uid=} {username=}")

    user = firebase.get_user(uid=uid, username=username)
    if user is None:
        return _c.Response(success=False, msg="User not found.")

    mmrs = statistics.get_user_mmrs(uid)

    return _a.responses.UserData(
        success=True,
        user=user,
        mmrs=mmrs,
    )


@app.post("/api/create-user")
def create_user(data: _a.args.CreateUser) -> _c.Response:
    """
    Create the user if possible and return if it was succesful
    """

    try:
        firebase.assert_username_valid(data.username)
    except FirebaseException as e:
        return _c.Response(success=False, msg=str(e))

    if firebase.get_user(uid=data.uid) is not None:
        return _c.Response(success=False, msg=f"User already exists")

    data.last_online = datetime.now(tz=timezone.utc)

    user = _c.User(**data.dict())

    firebase.create_user(user)
    return _c.Response(success=True)


@app.post("/api/create-bot")
def create_bot(data: _a.args.CreateBot) -> _a.responses.CreateBot:
    """
    Create the bot if possible and return if it was succesful
    """
    user = firebase.get_user(uid=data.creator_uid)
    if user is None:
        return _c.Response(success=False, msg=f"User not found.")

    try:
        bot, token = firebase.create_bot(user, data.username)
    except FirebaseException as e:
        return _c.Response(success=False, msg=str(e))

    return _a.responses.CreateBot(bot=bot, bot_jwt=token)


@app.post("/api/user-online")
def user_online(data: _a.args.UserOnline) -> _c.Response:
    """
    Update the last online datetime of the user.
    Set it as now.
    """
    if not firebase.auth_sio_client(data.siotk):
        return _c.Response(success=False, msg="Invalid socket-io token")

    date = datetime.now(tz=timezone.utc)
    firebase.update_last_online(data.uid, date)

    return _c.Response(success=True)


@app.get("/api/game-mode")
def game_mode(id: str | None = None, all: bool | None = None) -> _a.responses.GameMode:
    """
    Return the game mode with the given id or name

    If all = True, return all the game modes
    """
    if all:
        return _a.responses.GameMode(game_modes=firebase.get_game_modes())

    mode = firebase.get_game_mode(id=id)

    if mode is None:
        return _c.Response(success=False, msg="Mode not found.")

    return _a.responses.GameMode(game_modes=[mode])


@app.post("/api/game-results")
def game_results(data: _a.args.GameResults) -> _a.responses.GameResults:
    """
    Update the stats and mmr of all player in the game

    Return the new mmrs and the mmr differences
    """
    # handle auth -> requests should only come from sio client
    if not firebase.auth_sio_client(data.siotk):
        return _c.Response(success=False, msg="Invalid socket-io token")

    mode = firebase.get_game_mode(id=data.gmid)

    if mode is None:
        return _c.Response(success=False, msg="Mode not found.")

    date = datetime.now(tz=timezone.utc)
    mmrs = []
    mmr_diffs = []

    # update each user in the game
    for i, uid in enumerate(data.ranking):
        user = firebase.get_user(uid=uid)
        if user is None:
            # preserve ranking order
            mmrs.append(0)
            mmr_diffs.append(0)
            continue

        # get user mmrs
        ummrs = statistics.get_user_mmrs(uid)

        diff = mmrsystem.get_mmr_diff(mode, i)
        ummrs.mmrs[mode.id] += diff

        mmrs.append(ummrs.mmrs[mode.id])
        mmr_diffs.append(diff)

        # update db user mmrs
        statistics.update_user_mmrs(uid, ummrs)

        # build game stats
        gstats = _c.GameStats(date=date, mmr=ummrs.mmrs[mode.id], ranking=data.ranking)

        # push game on db
        statistics.push_game_stats(uid, mode.id, gstats)

    return _a.responses.GameResults(
        mmrs=mmrs,
        mmr_diffs=mmr_diffs,
    )


@app.get("/api/user-stats")
def user_stats(uid: str) -> _a.responses.UserStats:
    """
    Return the user stats
    """
    # get user from db -> assert it exists
    user = firebase.get_user(uid=uid)

    if user is None:
        return _c.Response(success=False, msg=f"Invalid user id '{uid}'")

    # get user stats
    ustats = statistics.get_user_stats(uid)

    # build response
    stats = []
    for gmhist in ustats.history.values():
        egmstats = statistics.get_game_mode_stats(uid, gmhist)
        stats.append(egmstats)

    return _a.responses.UserStats(
        stats=stats,
    )
