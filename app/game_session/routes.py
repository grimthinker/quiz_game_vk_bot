import typing


if typing.TYPE_CHECKING:
    from app.web.app import Application


def setup_routes(app: "Application"):
    from app.game_session.views import GameSessionListView

    app.router.add_view("/game-session.list", GameSessionListView)
