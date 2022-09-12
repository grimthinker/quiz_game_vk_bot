import typing
from logging import getLogger
from typing import Union, Optional

from app.game_session.models import GameSession, Player, SessionState
from app.quiz.models import Question
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
        "new_answerer": "nameplaceholder, выбирай вопрос!",
        "question": "questionplaceholder",
        "wrong_start": "Чтобы начать новую игру, завершите текущюю",
        "no_preparing_session": "Игра либо уже начата, либо ещё не начата, дождитесь начала новой",
        "no_running_session": "Нельзя выбирать/отвечать на вопросы, дождитесь начала новой игры",
        "not_current_answerer": "Выбирать/отвечать на вопросы сейчас может только nameplaceholder",
        "not_creator_to_run": "nameplaceholder, запустить игру может тот, кто нажал 'Старт'",
        "not_enough_players": "Слишком мало игроков!",}

    def __init__(self, app: "Application"):
        self.app = app
        self.logger = getLogger("handler")

    async def handle_updates(self, updates: list[Update]) -> None:
        for update in updates:
            chat_id = update.object.message.peer_id
            text = update.object.message.text.split()
            if len(text) > 1:
                text = text[1]
            player_id = update.object.message.from_id
            action_type = update.object.message.action_type
            payload_cmd = update.object.message.payload_cmd
            payload_txt = update.object.message.payload_txt

            if action_type == "chat_invite_user":
                await self.on_chat_inviting(chat_id=chat_id)
            elif text == 'Старт':
                await self.on_start(chat_id=chat_id, player_id=player_id)
            elif text == 'Участвовать':
                await self.on_participate(chat_id=chat_id, player_id=player_id)
            elif text == 'Поехали':
                await self.on_run(chat_id=chat_id, player_id=player_id)
            elif payload_cmd == "chosen_question":
                await self.on_choosing_question(chat_id=chat_id, question_id=int(payload_txt), player_id=player_id)

    async def do_things_on_start(self):
        chats = await self.app.store.game_sessions.list_chats(id_only=True)
        for chat_id in chats:
            await self.send_message(peer_id=chat_id, type="restart")

        chats = await self.app.store.game_sessions.list_chats(id_only=True, req_cnd="chats_session_needed")
        for chat_id in chats:
            await self.send_message(peer_id=chat_id, type="initial")

        chats = await self.app.store.game_sessions.list_chats(id_only=True, req_cnd="preparing")
        for chat_id in chats:
            await self.send_message(peer_id=chat_id, type="preparing")

        chats = await self.app.store.game_sessions.list_chats(id_only=True, req_cnd="just_started")
        for chat_id in chats:
            chat_sessions = await self.list_sessions(chat_id=chat_id, req_cnds=["just_started"])
            if chat_sessions:
                session_id = chat_sessions[0]
                session_state = await self.get_session_by_id(session_id, return_state=True)
                answerer = session_state.current_answerer

                questions = await self.get_questions_of_session_dict(session_id)
                await self.send_message(peer_id=chat_id, type="new_answerer", user_id=answerer, questions=questions)


    async def on_chat_inviting(self, chat_id: int) -> None:
        chat_ids = await self.app.store.game_sessions.list_chats(id_only=True, id=chat_id)
        if chat_id not in chat_ids:
            chat = await self.app.store.game_sessions.add_chat_to_db(chat_id)
        else:
            chat = chat_ids[0]
        await self.send_message(peer_id=chat.id, type="bot_added_to_chat")
        await self.send_message(peer_id=chat.id, type="initial")

    async def on_start(self, chat_id: int, player_id: int) -> None:
        chat_running_sessions = await self.list_sessions(chat_id=chat_id,
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
        await self.app.store.game_sessions.add_player_to_session(session.creator, session.id)
        await self.send_message(peer_id=chat_id, type="started", user_id=player_id)
        await self.send_message(peer_id=chat_id, type="preparing")

    async def on_participate(self, chat_id: int, player_id: int) -> None:
        chat_sessions = await self.list_sessions(chat_id=chat_id, req_cnds=["preparing"])
        if chat_sessions:
            session_id = chat_sessions[0]
            session_players = await self.list_players(session_id=session_id)
        else:
            await self.send_message(peer_id=chat_id, type="no_preparing_session")
            return
        if player_id in session_players:
            await self.send_message(peer_id=chat_id, type="player_already_added", user_id=player_id)
            return
        await self.add_player_to_session(player_id, session_id)
        await self.send_message(peer_id=chat_id, type="new_player_added", user_id=player_id)

    async def on_run(self, chat_id: int, player_id: int) -> None:
        chat_sessions = await self.list_sessions(chat_id=chat_id, req_cnds=["preparing"])
        if chat_sessions:
            session_id = chat_sessions[0]
            session = await self.get_session_by_id(session_id)
        else:
            await self.send_message(peer_id=chat_id, type="no_preparing_session")
            return
        if session.creator == player_id:
            session_players = await self.list_players(session_id=session.id)
        else:
            await self.send_message(peer_id=chat_id, type="not_creator_to_run", user_id=player_id)
            return
        if len(session_players) < 2:
            await self.send_message(peer_id=chat_id, type="not_enough_players")
            return
        questions = await self.add_questions_to_session(session.id)
        answerer = await self.choose_answerer(session, session_players)
        await self.set_session_state(session.id, "just_started")
        await self.send_message(peer_id=chat_id, type="start_quiz")
        await self.send_message(peer_id=chat_id, type="new_answerer", user_id=answerer.id, questions=questions)

    async def on_choosing_question(self, chat_id: int, question_id: int, player_id: int) -> None:
        chat_sessions = await self.list_sessions(chat_id=chat_id, req_cnds=["just_started"])
        if chat_sessions:
            session_id = chat_sessions[0]
            session_state = await self.get_session_by_id(session_id, return_state=True)
        else:
            await self.send_message(peer_id=chat_id, type="no_running_session")
            return
        if not player_id == session_state.current_answerer:
            await self.send_message(peer_id=chat_id, type="not_current_answerer",  user_id=session_state.current_answerer)
            return
        question = await self.set_current_question(session_state.session_id, question_id)
        await self.send_message(peer_id=chat_id, type="question", question=question)
        await self.set_session_state(session_state.session_id, "question_asked")

    async def list_sessions(self, chat_id: int = None,
                            req_cnds: list[str] = None,
                            creator_id: int = None
                            ) -> list[int]:
        game_sessions = await self.app.store.game_sessions.list_sessions(id_only=True,
                                                                         creator_id=creator_id,
                                                                         chat_id=chat_id,
                                                                         req_cnds=req_cnds)
        return game_sessions

    async def list_players(self, session_id: Optional[int] = None) -> list[int]:
        players = await self.app.store.game_sessions.list_players(id_only=True, session_id=session_id)
        return players

    async def add_player_to_session(self, player_id: int, session_id: int) -> None:
        await self.app.store.game_sessions.add_player_to_session(player_id, session_id)

    async def choose_answerer(self, session: GameSession, session_players: list[int]) -> Player:
        answerer = await self.app.store.game_sessions.choose_answerer(session.id, session_players)
        return answerer

    async def set_session_state(self, session_id: int, state_name: str) -> None:
        await self.app.store.game_sessions.set_session_state(session_id, state_name)

    async def add_questions_to_session(self, session_id: int) -> dict[str, dict[int, Question]]:
        themes_limit = 3
        questions_points = [100, 200, 300]
        questions = await self.app.store.game_sessions.add_questions_to_session(session_id,
                                                                                themes_limit,
                                                                                questions_points)
        return questions

    async def get_questions_of_session_dict(self, session_id: int) -> dict[str, dict[int, Question]]:
        questions = await self.app.store.game_sessions.get_questions_of_session_dict(session_id)
        return questions

    async def set_current_question(self, session_id: int, question_id: int) -> Question:
        question = await self.app.store.game_sessions.set_current_question(session_id, question_id)
        return question

    async def send_message(self, peer_id: int, type: str, **kwargs) -> None:
        params = {"peer_id": peer_id, "message": self.messagetext[type]}
        keyboard = get_keyboard_json(type=type, **kwargs)
        if keyboard:
            params["keyboard"] = keyboard
        if "user_id" in kwargs:
            name = await self.app.store.vk_api.get_user_name(kwargs["user_id"])
            params["message"] = params["message"].replace('nameplaceholder', name)
        if "question" in kwargs:
            question = kwargs["question"]
            params["message"] = params["message"].replace('questionplaceholder', question.title)
        await self.app.store.vk_api.send_message(**params)

    async def get_session_by_id(self, session_id: int, return_state: bool = False) -> Union[GameSession, SessionState]:
        if return_state:
            state = await self.app.store.game_sessions.get_session_state_by_id(session_id)
            return state
        session = await self.app.store.game_sessions.get_game_session_by_id(session_id)
        return session



