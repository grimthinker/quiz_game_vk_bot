from typing import Union

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.game_session.models import Player, Chat
from app.store.bot.helpers import CmdEnum
from app.store.vk_api.dataclasses import Update, UpdateObject, UpdateMessage


@pytest.fixture
def start_game_update(creator_1, chat_1) -> Update:
    return Update(
        type="message_new",
        object=UpdateObject(
            message=UpdateMessage(
                from_id=creator_1.id,
                text="Старт",
                id=1,
                peer_id=chat_1.id,
                action_type=None,
                payload_cmd=CmdEnum.START.value,
                payload_txt=None,
            )
        ),
    )


@pytest.fixture
def participate_update(player_1, chat_1) -> Update:
    return Update(
        type="message_new",
        object=UpdateObject(
            message=UpdateMessage(
                from_id=player_1.id,
                text="Участвовать",
                id=1,
                peer_id=chat_1.id,
                action_type=None,
                payload_cmd=CmdEnum.PARTICIPATE.value,
                payload_txt=None,
            )
        ),
    )


@pytest.fixture
def run_game_update(creator_1, chat_1) -> Update:
    return Update(
        type="message_new",
        object=UpdateObject(
            message=UpdateMessage(
                from_id=creator_1.id,
                text="Поехали",
                id=1,
                peer_id=chat_1.id,
                action_type=None,
                payload_cmd=CmdEnum.RUN.value,
                payload_txt=None,
            )
        ),
    )


@pytest.fixture
def question_update(creator_1, chat_1) -> Update:
    return Update(
        type="message_new",
        object=UpdateObject(
            message=UpdateMessage(
                from_id=creator_1.id,
                text="Some question",
                id=1,
                peer_id=chat_1.id,
                action_type=None,
                payload_cmd=CmdEnum.QUESTION.value,
                payload_txt="1",
            )
        ),
    )


@pytest.fixture
def wrong_answer_update(creator_1, chat_1) -> Update:
    return Update(
        type="message_new",
        object=UpdateObject(
            message=UpdateMessage(
                from_id=creator_1.id,
                text="Some question",
                id=1,
                peer_id=chat_1.id,
                action_type=None,
                payload_cmd=CmdEnum.ANSWER.value,
                payload_txt=False,
            )
        ),
    )


@pytest.fixture
def correct_answer_update(creator_1, chat_1) -> Update:
    return Update(
        type="message_new",
        object=UpdateObject(
            message=UpdateMessage(
                from_id=creator_1.id,
                text="Some question",
                id=1,
                peer_id=chat_1.id,
                action_type=None,
                payload_cmd=CmdEnum.ANSWER.value,
                payload_txt=True,
            )
        ),
    )


@pytest.fixture
def stop_game_update(creator_1, chat_1) -> Update:
    return Update(
        type="message_new",
        object=UpdateObject(
            message=UpdateMessage(
                from_id=creator_1.id,
                text="Стоп",
                id=1,
                peer_id=chat_1.id,
                action_type=None,
                payload_cmd=CmdEnum.STOP.value,
                payload_txt=None,
            )
        ),
    )


def custom_update(
    from_id: int,
    peer_id: int,
    payload_cmd: str,
    payload_txt: Union[str, bool, None],
    text: Union[str, None] = "",
    action_type: Union[str, None] = None,
) -> Update:
    return Update(
        type="message_new",
        object=UpdateObject(
            message=UpdateMessage(
                from_id=from_id,
                text=text,
                id=1,
                peer_id=peer_id,
                action_type=action_type,
                payload_cmd=payload_cmd,
                payload_txt=payload_txt,
            )
        ),
    )
