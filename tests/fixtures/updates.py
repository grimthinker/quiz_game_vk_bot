import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.game_session.models import Player, Chat
from app.store.bot.helpers import CmdEnum
from app.store.vk_api.dataclasses import Update, UpdateObject, UpdateMessage


@pytest.fixture
async def start_game_update(db_session: AsyncSession, creator_1: Player, chat_1: Chat) -> Update:
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
            )
        )

@pytest.fixture
async def participate_update(db_session: AsyncSession, player_1: Player, chat_1: Chat) -> Update:
    return Update(
            type="message_new",
            object=UpdateObject(
                message=UpdateMessage(
                    from_id=player_1.id,
                    text="Старт",
                    id=1,
                    peer_id=chat_1.id,
                    action_type=None,
                    payload_cmd=CmdEnum.START.value,
                    payload_txt=None,
                )
            )
        )