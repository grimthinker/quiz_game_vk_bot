import typing
import json
from functools import partial
from logging import getLogger
from sqlalchemy.exc import IntegrityError

from app.store.vk_api.dataclasses import Update
from app.web.utils import get_keyboard_json

if typing.TYPE_CHECKING:
    from app.web.app import Application



class BotManager:
    messagetext = {
        "initial": "Игра пока не начата. Чтобы начать игру, нажмите кнопку 'Старт'",
        "started": "Игрок nameplaceholder нажал 'Старт'! nameplaceholder, дождись других игроков, прежде чем продолжить",
        "restart": "Бот был перезагружен",
        "bot_added_to_chat": "Бот был добавлен в чат",
        "preparing": "Для участия в игре нажмите кнопку 'Участвовать'\n Когда все будут готовы, нажмите 'Поехали'",
        "new_player_added": "Добавлен игрок nameplaceholder",
        "player_already_added": "Игрок nameplaceholder уже добавлен",
        "start_quiz": "Игра началась!",
        "wrong_start": "Чтобы начать новую игру, завершите текущюю",
        "no_preparing_session":  "Игра либо уже начата, либо ещё не начата, дождитесь начала новой",
        "not_creator_to_run": "nameplaceholder, запустить игру может тот, кто нажал 'Старт'",
        "not_enough_players": "Слишком мало игроков!"}

    def __init__(self, app: "Application"):
        self.app = app
        self.logger = getLogger("handler")


    async def on_chat_inviting(self, chat_id: int) -> None:
        chat_ids = await self.app.store.game_sessions.list_chats(id_only=True, id=chat_id)
        if chat_id not in chat_ids:
            chat = await self.app.store.game_sessions.add_chat_to_db(chat_id)
        else:
            self.logger.info("bot added to an already existed in DB chat")
        await self.send_message(peer_id=chat.id, type="bot_added_to_chat")
        await self.send_message(peer_id=chat.id, type="initial")

    async def on_start(self, chat_id: int, player_id: int) -> None:
        chat_running_sessions = await self.app.store.game_sessions.list_sessions(chat_id=chat_id,
                                                                                 creator_id=player_id,
                                                                                 req_cnds=["preparing",
                                                                                           "just_started",
                                                                                           "question_asked",
                                                                                           "answered_wrong",
                                                                                           "answered_right"])
        if chat_running_sessions:
            await self.send_message(peer_id=chat_id, type="wrong_start")
            return
        session = await self.app.store.game_sessions.create_game_session(chat_id, player_id)
        await self.app.store.game_sessions.add_player_to_game_session(session.creator, session.id)
        await self.send_message(peer_id=chat_id, type="started", user_id=player_id)
        await self.send_message(peer_id=chat_id, type="preparing")

    async def on_participate(self, chat_id: int, player_id: int) -> None:
        chat_sessions = await self.app.store.game_sessions.list_sessions(chat_id=chat_id, req_cnds=["preparing"])
        if chat_sessions:
            session = chat_sessions[0]
            session_players = await self.app.store.game_sessions.list_players(id_only=True, session_id=session.id)
        else:
            await self.send_message(peer_id=chat_id, type="no_preparing_session")
            return
        if player_id in session_players:
            await self.send_message(peer_id=chat_id, type="player_already_added", user_id=player_id)
            return
        await self.app.store.game_sessions.add_player_to_game_session(player_id, session.id)
        await self.send_message(peer_id=chat_id, type="new_player_added", user_id=player_id)
        await self.send_message(peer_id=chat_id, type="preparing")

    async def on_run(self, chat_id: int, player_id: int) -> None:
        chat_sessions = await self.app.store.game_sessions.list_sessions(chat_id=chat_id, req_cnds=["preparing"])
        if chat_sessions:
            session = chat_sessions[0]
        else:
            await self.send_message(peer_id=chat_id, type="no_preparing_session")
            await self.send_message(peer_id=chat_id, type="preparing")
            return
        if session.creator == player_id:
            session_players = await self.app.store.game_sessions.list_players(id_only=True, session_id=session.id)
        else:
            await self.send_message(peer_id=chat_id, type="not_creator_to_run", user_id=player_id)
            await self.send_message(peer_id=chat_id, type="preparing")
            return
        if len(session_players) < 2:
            await self.send_message(peer_id=chat_id, type="not_enough_players")
            await self.send_message(peer_id=chat_id, type="preparing")
            return
        await self.app.store.game_sessions.set_session_state(session.id, "just_started")
        await self.send_message(peer_id=chat_id, type="start_quiz")
        await self.app.store.game_sessions.add_questions_to_session(session.id)
        await self.choose_answerer(session, session_players)

    async def send_message(self, peer_id: int, type: str, **kwargs) -> None:
        params = {"peer_id": peer_id, "message": self.messagetext[type]}
        keyboard = get_keyboard_json(type=type)
        if keyboard:
            params["keyboard"] = keyboard
        if "user_id" in kwargs:
            name = await self.app.store.vk_api.get_user_name(kwargs["user_id"])
            params["message"] = params["message"].replace('nameplaceholder', name)
        await self.app.store.vk_api.send_message(**params)

    async def handle_updates(self, updates: list[Update]) -> None:
        for update in updates:

            chat_id = update.object.message.peer_id
            text = update.object.message.text.split()
            if len(text) > 1:
                text = text[1]
            player_id = update.object.message.from_id

            if update.object.message.action_type == "chat_invite_user": # If true, the bot has been added to a new chat
                await self.on_chat_inviting(chat_id=chat_id)

            elif text == 'Старт':
                await self.on_start(chat_id=chat_id, player_id=player_id)

            elif text == 'Участвовать':
                await self.on_participate(chat_id=chat_id, player_id=player_id)

            elif text == 'Поехали':
                await self.on_run(chat_id=chat_id, player_id=player_id)

    async def do_things_on_start(self):
        # Firstly, send to all message that bot was restarted

        chats = await self.app.store.game_sessions.list_chats(id_only=True)
        for chat_id in chats:
            await self.send_message(peer_id=chat_id, type="restart")

        chats = await self.app.store.game_sessions.list_chats(id_only=True, req_cnd="chats_session_needed")
        print(chats)
        for chat_id in chats:
            await self.send_message(peer_id=chat_id, type="initial")

        chats = await self.app.store.game_sessions.list_chats(id_only=True, req_cnd="preparing")
        print(chats)
        for chat_id in chats:
            await self.send_message(peer_id=chat_id, type="preparing")

    def choose_answerer(self, session_id, session_players):
        pass
