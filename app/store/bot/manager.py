import typing
from collections import defaultdict
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
        "choose_question": "nameplaceholder, выбирай вопрос!",
        "question": "Вопрос: questionplaceholder",
        "answered_correct": "nameplaceholder дал правильный ответ! Игрок получает pointsplaceholder очков, текущая сумма: curpntsplaceholder",
        "answered_wrong": "Неверный ответ! nameplaceholder теряет pointsplaceholder очков, текущая сумма: curpntsplaceholder",
        "game_ended": "Игра окончена игроком nameplaceholder",
        "no_players_left": "Все игроки ответили неверно, правильный ответ - answerplaceholder",
        "wrong_start": "Чтобы начать новую игру, завершите текущюю",
        "no_preparing_session": "Игра либо уже начата, либо ещё не начата, дождитесь начала новой",
        "no_running_session": "Сейчас нельзя выбирать/отвечать на вопросы",
        "not_last_answerer": "Выбирать вопрос сейчас может только nameplaceholder",
        "not_creator_to_run": "nameplaceholder, запустить игру может тот, кто нажал 'Старт' (сreatorplaceholder)",
        "not_creator_to_stop": "nameplaceholder, преждевременно завершить игру может тот, кто нажал 'Старт' (сreatorplaceholder)",
        "not_enough_players": "Слишком мало игроков!",
        "question_already_answered": "Этот вопрос уже был, выбери другой!",
        "can_not_answer": "nameplaceholder уже потратил свою попытку на ответ",
        "no_session_to_stop": "Нет идущих игровых сессий"
    }

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
            elif payload_cmd == "chosen_answer":
                await self.on_choosing_answer(chat_id=chat_id, is_correct=payload_txt, player_id=player_id)
            elif text == "Стоп":
                await self.on_stop(chat_id=chat_id, player_id=player_id)


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

        chats = await self.app.store.game_sessions.list_chats(id_only=True, req_cnd="waiting_question")
        for chat_id in chats:
            chat_sessions = await self.list_sessions(chat_id=chat_id, req_cnds=["waiting_question"])
            if chat_sessions:
                session_id = chat_sessions[0]
                session_state = await self.get_session_by_id(session_id, return_state=True)
                answerer = session_state.last_answerer
                questions = await self.get_questions_of_session(session_id)
                await self.send_message(peer_id=chat_id, type="choose_question", user_id=answerer, questions=questions)

        chats = await self.app.store.game_sessions.list_chats(id_only=True, req_cnd="question_asked")
        for chat_id in chats:
            chat_sessions = await self.list_sessions(chat_id=chat_id, req_cnds=["question_asked"])
            if chat_sessions:
                session_id = chat_sessions[0]
                session_state = await self.get_session_by_id(session_id, return_state=True)
                answerer = session_state.last_answerer
                question_id = session_state.current_question
                question = await self.app.store.quizzes.get_question_by_id(question_id)
                await self.send_message(peer_id=chat_id, type="question", question=question)

    # "on command" methods:

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
            await self.send_message(peer_id=chat_id,
                                    type="not_creator_to_run",
                                    user_id=player_id,
                                    creator_id=session.creator)
            return
        if len(session_players) < 2:
            await self.send_message(peer_id=chat_id, type="not_enough_players")
            return
        questions = await self.add_questions_to_session(session.id)
        answerer = await self.set_answerer(session_id, to_set=session_players)
        await self.set_session_state(session.id, "waiting_question")
        await self.send_message(peer_id=chat_id, type="start_quiz")
        await self.send_message(peer_id=chat_id, type="choose_question", user_id=answerer.id, questions=questions)

    async def on_choosing_question(self, chat_id: int, question_id: int, player_id: int) -> None:
        chat_sessions = await self.list_sessions(chat_id=chat_id, req_cnds=["just_started"])
        if chat_sessions:
            session_id = chat_sessions[0]
            session_state = await self.get_session_by_id(session_id, return_state=True)
        else:
            await self.send_message(peer_id=chat_id, type="no_running_session")
            return
        if not player_id == session_state.last_answerer:
            await self.send_message(peer_id=chat_id, type="not_last_answerer",  user_id=session_state.last_answerer)
            return
        is_answered = await self.check_if_question_already_answered(question_id, session_id)
        if is_answered:
            await self.send_message(peer_id=chat_id, type="question_already_answered")
            return
        question = await self.set_current_question(session_id, question_id)
        await self.set_session_state(session_id, "question_asked")
        await self.send_message(peer_id=chat_id, type="question", question=question)

    async def on_choosing_answer(self, chat_id: int, is_correct: str, player_id: int) -> None:
        chat_sessions = await self.list_sessions(chat_id=chat_id, req_cnds=["question_asked"])
        if chat_sessions:
            session_id = chat_sessions[0]
        else:
            await self.send_message(peer_id=chat_id, type="no_running_session")
            return
        players = await self.list_players(id_only=True, session_id=session_id, can_answer=True)
        if player_id not in players:
            await self.send_message(peer_id=chat_id, type="can_not_answer", user_id=player_id)
            return
        await self.question_answered(chat_id, player_id, session_id, is_correct.lower())

    async def question_answered(self, chat_id: int, player_id: int, session_id: int, is_correct: str):
        session_state = await self.get_session_by_id(session_id, return_state=True)
        current_question_id = session_state.current_question
        question = await self.app.store.quizzes.get_question_by_id(current_question_id)
        answer = next((x for x in question.answers if x.is_correct), 'No correct answer')
        questions = await self.get_questions_of_session(session_id)
        if is_correct == "true":
            current_points = await self.add_points_to_player(player_id, question.points)
            await self.restore_answering(session_id)
            await self.send_message(peer_id=chat_id,
                                    type="answered_correct",
                                    user_id=player_id,
                                    points=str(current_points),
                                    current_points=str(current_points))
            player = await self.set_answerer(session_id, to_set=player_id)
            has_unanswered = await self.check_if_some_questions_unanswered(session_id)
            if has_unanswered:
                await self.set_session_state(session_id, "waiting_question")
                await self.send_message(peer_id=chat_id, type="choose_question", user_id=player_id, questions=questions)
            else:
                results = await self.end_game_session(session_id)
                await self.send_message(peer_id=chat_id, type="session_ended", results=results)

        elif is_correct == "false":
            current_points = await self.add_points_to_player(player_id, -question.points)
            await self.send_message(peer_id=chat_id,
                                    type="answered_wrong",
                                    user_id=player_id,
                                    points=str(-current_points),
                                    current_points=str(current_points))
            await self.forbid_answering(session_id, player_id)

            no_players_left = await self.check_if_no_players_left(session_id)
            if no_players_left:
                print(2424242424)
                has_unanswered = await self.check_if_some_questions_unanswered()
                if has_unanswered:
                    await self.restore_answering()
                    await self.send_message(peer_id=chat_id, type="no_players_left", answer=answer)
                    await self.send_message(peer_id=chat_id, type="choose_question", user_id=player_id, questions=questions)
                else:
                    results = await self.end_game_session(session_id)
                    await self.send_message(peer_id=chat_id, type="session_ended", results=results)
            else:
                await self.send_message(peer_id=chat_id, type="question", question=question)

    async def on_stop(self, chat_id: int, player_id: int) -> None:
        chat_sessions = await self.list_sessions(chat_id=chat_id, req_cnds=["preparing",
                                                                            "waiting_question",
                                                                            "question_asked"])
        if chat_sessions:
            session_id = chat_sessions[0]
            session = await self.get_session_by_id(session_id)
        else:
            await self.send_message(peer_id=chat_id, type="no_session_to_stop")
            return
        if session.creator != player_id:
            await self.send_message(peer_id=chat_id,
                                    type="not_creator_to_stop",
                                    user_id=player_id,
                                    creator_id=session.creator)
            return
        await self.set_session_state(session.id, "ended")
        await self.send_message(peer_id=chat_id, type="start_quiz")

    # Helper methods:

    async def list_sessions(self, chat_id: int = None,
                            req_cnds: list[str] = None,
                            creator_id: int = None
                            ) -> list[int]:
        game_sessions = await self.app.store.game_sessions.list_sessions(id_only=True,
                                                                         creator_id=creator_id,
                                                                         chat_id=chat_id,
                                                                         req_cnds=req_cnds)
        return game_sessions

    async def list_players(self, id_only: bool = True,
                           session_id: Optional[int] = None,
                           can_answer: Optional[bool] = None) -> list[int]:
        players = await self.app.store.game_sessions.list_players(id_only=id_only,
                                                                  session_id=session_id,
                                                                  can_answer=can_answer)
        return players

    async def add_player_to_session(self, player_id: int, session_id: int) -> None:
        await self.app.store.game_sessions.add_player_to_session(player_id, session_id)

    async def set_answerer(self, session_id: int, to_set: Union[list[int], int]) -> Player:
        answerer = await self.app.store.game_sessions.set_answerer(session_id=session_id, to_set=to_set)
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

    async def get_questions_of_session(
            self, session_id: int,
            answered: Optional[bool] = None,
            id_only: bool = False,
            to_dict: bool = True,
    ) -> Union[list[Question], dict[str, dict[int, Question]]]:

        questions = await self.app.store.game_sessions.get_questions_of_session(session_id=session_id,
                                                                                id_only=id_only,
                                                                                answered=answered)
        if to_dict and not id_only:
            theme_ids = set([x.theme_id for x in questions])
            theme_ids_to_names = {}
            for theme_id in theme_ids:
                theme = await self.app.store.quizzes.get_theme_by_id(theme_id)
                theme_ids_to_names[theme_id] = theme.title
            questions_dict = defaultdict(dict)
            for x in questions:
                questions_dict[theme_ids_to_names[x.theme_id]][x.points] = x
            questions = questions_dict  # questions_dict ~ {theme1: {100: q1, 200: q2}, theme2: {100: q3, 200: q4},}
        return questions

    async def set_current_question(self, session_id: int, question_id: int) -> Question:
        question = await self.app.store.game_sessions.set_current_question(session_id, question_id)
        return question

    async def get_session_by_id(self, session_id: int, return_state: bool = False) -> Union[GameSession, SessionState]:
        if return_state:
            state = await self.app.store.game_sessions.get_session_state_by_id(session_id)
            return state
        session = await self.app.store.game_sessions.get_game_session_by_id(session_id)
        return session

    async def check_if_question_already_answered(self, question_id: id, session_id: id):
        answered_questions = await self.get_questions_of_session(session_id=session_id,
                                                                 answered=True,
                                                                 to_dict=False,
                                                                 id_only=True)
        return question_id in answered_questions

    async def check_if_some_questions_unanswered(self, session_id: id):
        unanswered_questions = await self.get_questions_of_session(session_id=session_id,
                                                                   answered=False,
                                                                   to_dict=False,
                                                                   id_only=True)
        return any(unanswered_questions)

    async def add_points_to_player(self, player_id: int, points: int) -> int:
        current_points = await self.app.store.game_sessions.add_points_to_player(player_id, points)
        return current_points

    async def restore_answering(self, session_id: int) -> None:
        print(111111111111111111111167)
        await self.app.store.game_sessions.restore_answering(session_id)

    async def forbid_answering(self, session_id: int, player_id: int) -> None:
        await self.app.store.game_sessions.forbid_answering(session_id, player_id)

    async def check_if_no_players_left(self, session_id: int) -> bool:
        await self.app.store.game_sessions.check_if_no_players_left(session_id)

    async def end_game_session(self, session_id):
        await self.set_session_state(session_id=session_id, state_name="ended")
        results = await self.app.store.game_sessions.get_session_results()
        return results

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
        if "points" in kwargs:
            points = kwargs["points"]
            params["message"] = params["message"].replace('pointsplaceholder', points)
        if "current_points" in kwargs:
            current_points = kwargs["current_points"]
            params["message"] = params["message"].replace('curpntsplaceholder', current_points)
        if "answer" in kwargs:
            answer = kwargs["answer"]
            params["message"] = params["message"].replace('answerplaceholder', answer)
        if "creator_id" in kwargs:
            name = await self.app.store.vk_api.get_user_name(kwargs["creator_id"])
            params["message"] = params["message"].replace('creatorplaceholder', answer)
        await self.app.store.vk_api.send_message(**params)