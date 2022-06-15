from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core import ResponseModel, UserModel, FirebaseException, ALLOWED_ORIGINS

import src.api.mmrsystem as mmrsystem
from .firebase import Firebase
from .models import (
    AllGameModeResponse,
    GameModeResponse,
    GameResultsAPI,
    GameResultsAPIResponse,
    UserResponse,
)

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
def user_data(uid: str | None = None, username: str | None = None) -> ResponseModel:
    """
    Return the user data corresponding to the given uid
    """
    print(f"{uid=} {username=}")

    user = firebase.get_user(uid=uid, username=username)
    if user is None:
        return ResponseModel(success=False, msg="User not found.")

    return UserResponse(
        success=True,
        user=user,
    )


@app.post("/api/create-user")
def create_user(data: UserModel) -> ResponseModel:
    """
    Create the user if possible and return if it was succesful
    """

    if firebase.get_user(uid=data.uid) is None:
        firebase.create_user(data)
        return ResponseModel(success=True)

    # user found
    return ResponseModel(success=False, msg=f"User already exists")


@app.get("/api/game-mode")
def game_mode(
    id: str | None = None, name: str | None = None, all: bool | None = None
) -> ResponseModel:
    """
    Return the game mode with the given id or name

    If `all=True`, return all the game modes
    """

    if all:
        return AllGameModeResponse(game_modes=firebase.get_game_modes())

    mode = firebase.get_game_mode(id=id, name=name)

    if mode is None:
        return ResponseModel(success=False, msg="Mode not found.")

    return GameModeResponse(game_mode=mode)


@app.post("/api/game-results")
def game_results(data: GameResultsAPI) -> GameResultsAPIResponse:
    """
    Update the stats and mmr of all player in the game

    Return the new mmrs and the mmr differences
    """
    mode = firebase.get_game_mode(id=data.gmid)

    if mode is None:
        return ResponseModel(success=False, msg="Mode not found.")

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

    return GameResultsAPIResponse(
        mmrs=mmrs,
        mmr_diffs=mmr_diffs,
    )
