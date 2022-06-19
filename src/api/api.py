from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.models import core
from src.models.api import args, responses
from src.core import FirebaseException, ALLOWED_ORIGINS

import src.api.mmrsystem as mmrsystem
from .firebase import Firebase


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


@app.get("/ping")
def ping():
    return "Hello world!"


@app.get("/api/user-data")
def user_data(data: args.UserData) -> responses.UserData:
    """
    Return the user data corresponding to the given uid
    """
    print(f"{data.uid=} {data.username=}")

    user = firebase.get_user(uid=data.uid, username=data.username)
    if user is None:
        return core.Response(success=False, msg="User not found.")

    return responses.UserData(
        success=True,
        user=user,
    )


@app.post("/api/create-user")
def create_user(data: args.CreateUser) -> responses.CreateUser:
    """
    Create the user if possible and return if it was succesful
    """

    if firebase.get_user(uid=data.uid) is None:
        firebase.create_user(data)
        return core.Response(success=True)

    # user found
    return core.Response(success=False, msg=f"User already exists")


@app.get("/api/game-mode")
def game_mode(data: args.GameMode) -> responses.GameMode:
    """
    Return the game mode with the given id or name

    If all = True, return all the game modes
    """

    if data.all:
        return responses.GameMode(game_modes=firebase.get_game_modes())

    mode = firebase.get_game_mode(id=data.id)

    if mode is None:
        return core.Response(success=False, msg="Mode not found.")

    return responses.GameMode(game_modes=[mode])


@app.post("/api/game-results")
def game_results(data: args.GameResults) -> responses.GameResults:
    """
    Update the stats and mmr of all player in the game

    Return the new mmrs and the mmr differences
    """
    mode = firebase.get_game_mode(id=data.gmid)

    if mode is None:
        return core.Response(success=False, msg="Mode not found.")

    mmrs = []
    mmr_diffs = []

    for i, uid in enumerate(data.ranking):
        user = firebase.get_user(uid=uid)
        if user is None:
            # preserve ranking order
            mmrs.append(0)
            mmr_diffs.append(0)
            continue

        # update mode stats
        stats = firebase.get_user_stats(user.uid)
        genstats = stats.stats[mode.name]
        genstats.scores[i] += 1

        diff = mmrsystem.get_mmr_diff(genstats, mode, i)
        genstats.mmr += diff

        mmrs.append(genstats.mmr)
        mmr_diffs.append(diff)

        try:
            firebase.update_user_stats(
                uid=uid,
                gmid=mode.id,
                stats=genstats,
            )
        except FirebaseException as e:
            continue

    return responses.GameResults(
        mmrs=mmrs,
        mmr_diffs=mmr_diffs,
    )


@app.get("/api/user-stats")
def user_stats(data: args.UserStats) -> responses.UserStats:
    '''
    Return the user stats
    '''
    # get user from db -> assert it exists
    user = firebase.get_user(uid=data.uid)

    if user is None:
        return core.Response(success=False, msg=f"Invalid user id '{data.uid}'")

    # get stats
    stats = firebase.get_user_stats(data.uid)

    return responses.UserStats(
        stats=list(stats.stats.values()),
    )