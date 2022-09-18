import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.game_session.models import Player, Chat
from app.store.bot.helpers import CmdEnum
from app.store.vk_api.dataclasses import Update, UpdateObject, UpdateMessage
from tests.fixtures import custom_update


@pytest.fixture
async def preparing_state(store, start_game_update):
    await store.bots_manager.handle_update(update=start_game_update)
    yield


@pytest.fixture
async def waiting_question_singleplayer_state(store, preparing_state, run_game_update, participate_update):
    await store.bots_manager.handle_update(update=run_game_update)
    yield


@pytest.fixture
async def waiting_answer_singleplayer_state(store, waiting_question_singleplayer_state, question_update):
    await store.bots_manager.handle_update(update=question_update)
    yield


@pytest.fixture
async def after_wrong_answer_singleplayer_state(store, waiting_answer_singleplayer_state, wrong_answer_update):
    await store.bots_manager.handle_update(update=wrong_answer_update)
    yield


@pytest.fixture
async def after_correct_answer_singleplayer_state(store, waiting_answer_singleplayer_state, correct_answer_update):
    await store.bots_manager.handle_update(update=correct_answer_update)
    yield


@pytest.fixture
async def waiting_question_state(store, preparing_state, run_game_update, participate_update):
    await store.bots_manager.handle_update(update=participate_update)
    await store.bots_manager.handle_update(update=run_game_update)
    yield

@pytest.fixture
async def after_wrong_answer_state(chat_1, store, run_game_update, question_update, creator_1, player_1,
                                   waiting_question_state):
    chat_sessions = await store.game_sessions.list_sessions(id_only=True, chat_id=chat_1.id)
    state = await store.game_sessions.get_session_state_by_id(chat_sessions[0])
    answerer_id = state.last_answerer
    if answerer_id == player_1.id:
        answerer, answerer_2 = player_1, creator_1
    else:
        answerer, answerer_2 = creator_1, player_1
    update = custom_update(peer_id=chat_1.id, from_id=answerer.id, payload_cmd=CmdEnum.QUESTION.value,
                           payload_txt="1")
    await store.bots_manager.handle_update(update=update)
    update = custom_update(peer_id=chat_1.id, from_id=player_1.id, payload_cmd=CmdEnum.ANSWER.value,
                           payload_txt=False)
    await store.bots_manager.handle_update(update=update)
