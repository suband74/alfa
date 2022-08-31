from django.db.models import Q
from django.db import transaction
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from pydantic import BaseModel, Field
from typing import Optional
from callback.models import Player, Game

description = """
We use JWT for auth.
"""

app = FastAPI(title="Test Project API", description=description, version="0.0.1")


class User(BaseModel):
    username: str
    password: str


class LoginMessage(BaseModel):
    access_token: str


class UserMessage(BaseModel):
    user: str


class StatusMessage(BaseModel):
    status: str
    id: Optional[int] = None
    success: Optional[bool] = None


class ErrorMessage(BaseModel):
    status: str
    message: str


class PlayerItem(BaseModel):
    name: str = Field(regex="[0-9a-f]")
    email: str = Field(regex="^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$")


class GameItem(BaseModel):
    name: str


class Settings(BaseModel):
    authjwt_secret_key: str = "secret"


# callback to get your configuration
@AuthJWT.load_config
def get_config():
    return Settings()


# exception handler for auth-jwt
# in production, you can tweak performance using orjson response
@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


# provide a method to create access tokens. The create_access_token()
# function is used to actually generate the token to use authorization
# later in endpoint protected
@app.post("/login", tags=["Auth"], responses={200: {"model": LoginMessage}})
def login(user: User, Authorize: AuthJWT = Depends()):
    """
    Use username=test and password=test for now.
    This endpoint will response you with access_token
    to use in header like: "Authorization: Bearer $TOKEN" to get protected endpoints
    """
    if user.username != "test" or user.password != "test":
        raise HTTPException(status_code=401, detail="Bad username or password")

    # subject identifier for who this token is for example id or username from database
    access_token = Authorize.create_access_token(subject=user.username)
    return JSONResponse(status_code=200, content={"access_token": access_token})


# protect endpoint with function jwt_required(), which requires
# a valid access token in the request headers to access.
@app.get("/user", tags=["Auth"], responses={200: {"model": UserMessage}})
def user(Authorize: AuthJWT = Depends()):
    """
    Endpoint response with user that fits "Authorization: Bearer $TOKEN"
    """
    Authorize.jwt_required()

    current_user = Authorize.get_jwt_subject()
    return JSONResponse(status_code=200, content={"user": current_user})


@app.get("/protected_example", tags=["Auth"], responses={200: {"model": UserMessage}})
def protected_example(Authorize: AuthJWT = Depends()):
    """
    Just for test of Auth.

    Auth usage example:
    $ curl http://ip:8000/user

    {"detail":"Missing Authorization Header"}

    $ curl -H "Content-Type: application/json" -X POST \
    -d '{"username":"test","password":"test"}' http://localhost:8000/login

    {"access_token":"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0IiwiaWF0IjoxNjAzNjkyMjYxLCJuYmYiOjE2MDM2OTIyNjEsImp0aSI6IjZiMjZkZTkwLThhMDYtNDEzMy04MzZiLWI5ODJkZmI3ZjNmZSIsImV4cCI6MTYwMzY5MzE2MSwidHlwZSI6ImFjY2VzcyIsImZyZXNoIjpmYWxzZX0.ro5JMHEVuGOq2YsENkZigSpqMf5cmmgPP8odZfxrzJA"}

    $ export TOKEN=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0IiwiaWF0IjoxNjAzNjkyMjYxLCJuYmYiOjE2MDM2OTIyNjEsImp0aSI6IjZiMjZkZTkwLThhMDYtNDEzMy04MzZiLWI5ODJkZmI3ZjNmZSIsImV4cCI6MTYwMzY5MzE2MSwidHlwZSI6ImFjY2VzcyIsImZyZXNoIjpmYWxzZX0.ro5JMHEVuGOq2YsENkZigSpqMf5cmmgPP8odZfxrzJA

    $ curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/user

    {"user":"test"}

    $ curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/protected_example

    {"user":"test", "test": true}
    """
    Authorize.jwt_required()

    current_user = Authorize.get_jwt_subject()
    return JSONResponse(status_code=200, content={"user": current_user})


@app.post(
    "/new_player",
    tags=["Main"],
    responses={200: {"model": StatusMessage}, 400: {"model": ErrorMessage}},
)
def create_new_player(player: PlayerItem, Authorize: AuthJWT = Depends()):
    """
    Creates new player.
    """
    Authorize.jwt_required()

    with transaction.atomic():
        new_player = Player()
        new_player.name = player.name
        new_player.email = player.email
        if Player.objects.filter(Q(name=new_player.name) | Q(email=new_player.email)):
            raise HTTPException(
                status_code=400,
                detail="player with such name or email already exists",
                headers={"status": "error"},
            )
        else:
            new_player.save()

    return JSONResponse(
        content={"status": "success", "id": new_player.id, "success": True}
    )


@app.post(
    "/new_game",
    tags=["Main"],
    responses={200: {"model": StatusMessage}, 400: {"model": ErrorMessage}},
)
def create_new_game(game: GameItem, Authorize: AuthJWT = Depends()):
    """
    Creates new game.
    """
    Authorize.jwt_required()

    new_game = Game()
    new_game.name = game.name
    new_game.save()

    return JSONResponse(
        content={"status": "success", "id": new_game.id, "success": True}
    )


@app.post(
    "/add_player_to_game",
    tags=["Main"],
    responses={200: {"model": StatusMessage}, 400: {"model": ErrorMessage}},
)
def add_player_to_game(game_id: int, player_id: int, Authorize: AuthJWT = Depends()):
    """
    Adds existing player to existing game.
    """
    Authorize.jwt_required()

    with transaction.atomic():
        g = None
        p = None
        if Game.objects.filter(pk=game_id):
            g = Game.objects.get(pk=game_id)
        else:
            raise HTTPException(
                status_code=400,
                detail="Game matching query does not exist.",
                headers={"status": "error"},
            )

        if Player.objects.filter(pk=player_id):
            p = Player.objects.get(pk=player_id)
        else:
            raise HTTPException(
                status_code=400,
                detail="Player matching query does not exist.",
                headers={"status": "error"},
            )

        if g.players.count() >= 5:
            raise HTTPException(
                status_code=400,
                detail="The team cannot have more than five people",
                headers={"status": "error"},
            )
        else:
            g.players.add(p)

    return JSONResponse(content={"status": "success", "id": game_id, "success": True})
