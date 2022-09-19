import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select

from app.game_session.models import (
    Chat,
    Player,
    GameSession,
    GameSessionModel,
    SessionStateModel,
    StatesEnum,
)
from app.store import Store
from tests.utils import check_empty_table_exists


class TestSessionsStore:
    async def test_table_exists(self, cli):
        await check_empty_table_exists(cli, "game_sessions")
        await check_empty_table_exists(cli, "session_states")
        await check_empty_table_exists(cli, "players")
        await check_empty_table_exists(cli, "chats")
        await check_empty_table_exists(cli, "association_players_sessions")
        await check_empty_table_exists(cli, "association_sessions_questions")

    async def test_create_session(
        self, cli, chat_1: Chat, creator_1: Player, store: Store
    ):
        async with cli.app.database.session.begin() as session:
            game_session = await store.game_sessions.create_game_session(
                db_session=session, chat_id=chat_1.id, creator_id=creator_1.id
            )
        assert type(game_session) is GameSession

        async with cli.app.database.session.begin() as session:
            res = await session.execute(select(GameSessionModel))
            game_sessions = res.scalars().all()

            res = await session.execute(select(SessionStateModel))
            session_states = res.scalars().all()

        assert len(game_sessions) == 1
        assert len(session_states) == 1
        db_session_state = session_states[0]
        db_game_session = game_sessions[0]

        assert db_session_state.session_id == db_game_session.id

        assert game_session.chat_id == chat_1.id
        assert game_session.creator == creator_1.id
        assert db_session_state.state_name == StatesEnum.PREPARING.value
        assert db_session_state.current_question is None
        assert db_session_state.last_answerer is None
