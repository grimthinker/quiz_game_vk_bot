from app.game_session.models import Player
from app.store.vk_api.dataclasses import Update


class TestHandleUpdates:
    # async def test_no_messages(self, store):
    #     await store.bots_manager.handle_update(updates=[])
    #     assert store.vk_api.send_message.called is False

    async def test_handle_start_game(self, store, start_game_update: Update, creator_1: Player):
        await store.bots_manager.handle_update(update=start_game_update)
        assert store.vk_api.send_message.call_count == 2
        req_message = f"Игрок {creator_1.name} нажал 'Старт'! {creator_1.name}, дождись других игроков, прежде чем продолжить"
        assert store.vk_api.send_message.mock_calls[0].kwargs["message"] == req_message
