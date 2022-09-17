import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.game_session.models import (
    GameSessionModel, GameSession,
    ChatModel, Chat,
    SessionStateModel, SessionState,
    PlayerModel, Player)


@pytest.fixture
async def player_1(db_session: AsyncSession) -> Player:
    name = "Шанкрес"
    player = PlayerModel(name=name, id=1)
    async with db_session.begin() as session:
        session.add(player)
    return Player(id=player.id, name=player.name)

@pytest.fixture
async def player_2(db_session: AsyncSession) -> Player:
    name = "Викей"
    player = PlayerModel(name=name, id=2)
    async with db_session.begin() as session:
        session.add(player)
    return Player(id=player.id, name=player.name)

@pytest.fixture
async def player_3(db_session: AsyncSession) -> Player:
    name = "Юниус"
    player = PlayerModel(name=name, id=3)
    async with db_session.begin() as session:
        session.add(player)
    return Player(id=player.id, name=player.name)

@pytest.fixture
async def creator_1(db_session: AsyncSession) -> Player:
    name = "Тринетт"
    player = PlayerModel(name=name, id=11)
    async with db_session.begin() as session:
        session.add(player)
    return Player(id=player.id, name=player.name)

@pytest.fixture
async def creator_2(db_session: AsyncSession) -> Player:
    name = "Иша"
    player = PlayerModel(name=name, id=12)
    async with db_session.begin() as session:
        session.add(player)
    return Player(id=player.id, name=player.name)

@pytest.fixture
async def chat_1(db_session: AsyncSession) -> Chat:
    chat = ChatModel(id=1)
    async with db_session.begin() as session:
        session.add(chat)
    return Chat(id=chat.id)

@pytest.fixture
async def chat_2(db_session: AsyncSession) -> Chat:
    chat = ChatModel(id=2)
    async with db_session.begin() as session:
        session.add(chat)
    return Chat(id=chat.id)

@pytest.fixture
async def game_session_1(db_session: AsyncSession, chat_1: Chat, creator_1: Player) -> GameSession:
    game_session = GameSessionModel(chat_id=chat_1.id, creator=creator_1.id)
    async with db_session.begin() as session:
        session.add(game_session)
    session_state = SessionStateModel(state_name=chat_1.id, session_id=game_session.id)
    async with db_session.begin() as session:
        session.add(session_state)

    return GameSession(id=game_session.id,
                       chat_id=game_session.chat_id,
                       creator=game_session.creator,
                       state=SessionState(
                           session_id=session_state.session_id,
                           state_name=session_state.state_name,
                           current_question=session_state.current_question,
                           last_answerer=session_state.last_answerer
                       )
                       )

@pytest.fixture
async def game_session_2(db_session: AsyncSession, chat_2: Chat, creator_2: Player) -> GameSession:
    game_session = GameSessionModel(chat_id=chat_2.id, creator=creator_2.id)
    async with db_session.begin() as session:
        session.add(game_session)
    session_state = SessionStateModel(state_name=chat_2.id, session_id=game_session.id)
    async with db_session.begin() as session:
        session.add(session_state)

    return GameSession(id=game_session.id,
                       chat_id=game_session.chat_id,
                       creator=game_session.creator,
                       state=SessionState(
                           session_id=session_state.session_id,
                           state_name=session_state.state_name,
                           current_question=session_state.current_question,
                           last_answerer=session_state.last_answerer
                       )
                       )

