import typing
from collections import defaultdict
from logging import getLogger
from typing import Union, Optional

from app.game_session.models import GameSession, SessionState, StatesEnum
from app.quiz.models import Question
from app.store.bot.game_settings import *
from app.store.bot.helpers import CmdEnum, MessageHelper, KeyboardHelper
from app.store.vk_api.dataclasses import Update

if typing.TYPE_CHECKING:
    from app.web.app import Application


class BotManager:
    def __init__(self, app: "Application"):
        self.app = app
        self.logger = getLogger("handler")

    async def handle_update(self, update: Update) -> None:
        chat_id = update.object.message.peer_id
        player_id = update.object.message.from_id
        action_type = update.object.message.action_type
        payload_cmd = update.object.message.payload_cmd
        payload_txt = update.object.message.payload_txt
        if action_type == "chat_invite_user":
            await self.on_chat_inviting(chat_id=chat_id)
        elif payload_cmd == CmdEnum.START.value:
            await self.on_start(chat_id=chat_id, player_id=player_id)
        elif payload_cmd == CmdEnum.PARTICIPATE.value:
            await self.on_participate(chat_id=chat_id, player_id=player_id)
        elif payload_cmd == CmdEnum.RUN.value:
            await self.on_run(chat_id=chat_id, player_id=player_id)
        elif payload_cmd == CmdEnum.QUESTION.value:
            await self.on_choosing_question(
                chat_id=chat_id, question_id=int(payload_txt), player_id=player_id
            )
        elif payload_cmd == CmdEnum.ANSWER.value:
            await self.on_choosing_answer(
                chat_id=chat_id, is_correct=payload_txt, player_id=player_id
            )
        elif payload_cmd == CmdEnum.STOP.value:
            await self.on_stop(chat_id=chat_id, player_id=player_id)
        elif payload_cmd == CmdEnum.RESULTS.value:
            await self.on_show_results(chat_id=chat_id)

    async def on_bot_start(self, *_: list, **__: dict) -> None:
        chats = await self.app.store.game_sessions.list_chats()
        for chat_id in chats:
            await self.send_message(peer_id=chat_id, message=MessageHelper.restart)

        chats = await self.app.store.game_sessions.list_chats(
            req_cnd=StatesEnum.SESSION_NEEDED
        )
        for chat_id in chats:
            await self.send_message(
                peer_id=chat_id,
                message=MessageHelper.initial,
                keyboard=KeyboardHelper.generate_initial_keyboard(),
            )

        chats = await self.app.store.game_sessions.list_chats(
            req_cnd=StatesEnum.PREPARING
        )
        for chat_id in chats:
            await self.send_message(
                peer_id=chat_id,
                message=MessageHelper.preparing,
                keyboard=KeyboardHelper.generate_preparing_keyboard(),
            )

        chats = await self.app.store.game_sessions.list_chats(
            req_cnd=StatesEnum.WAITING_QUESTION
        )
        for chat_id in chats:
            chat_sessions = await self.app.store.game_sessions.list_sessions(
                id_only=True, chat_id=chat_id, req_cnds=[StatesEnum.WAITING_QUESTION]
            )
            if chat_sessions:
                session_id = chat_sessions[0]
                session_state = await self.get_session_by_id(
                    session_id, return_state=True
                )
                answerer = session_state.last_answerer
                questions = await self.get_questions_of_session(
                    session_id, answered=False
                )
                if not questions:
                    await self.send_message(
                        peer_id=chat_id, message=MessageHelper.no_question_in_db
                    )
                    continue
                await self.send_message(
                    peer_id=chat_id,
                    message=MessageHelper.choose_question(name=answerer),
                    keyboard=KeyboardHelper.generate_questions_keyboard(
                        questions=questions
                    ),
                )

        chats = await self.app.store.game_sessions.list_chats(
            req_cnd=StatesEnum.WAITING_ANSWER
        )
        for chat_id in chats:
            chat_sessions = await self.app.store.game_sessions.list_sessions(
                id_only=True, chat_id=chat_id, req_cnds=[StatesEnum.WAITING_ANSWER]
            )
            if chat_sessions:
                session_id = chat_sessions[0]
                session_state = await self.get_session_by_id(
                    session_id, return_state=True
                )
                question_id = session_state.current_question
                question = await self.app.store.quizzes.get_question_by_id(question_id)
                await self.send_message(
                    peer_id=chat_id,
                    message=MessageHelper.question(question=question),
                    keyboard=KeyboardHelper.generate_answers_keyboard(
                        question=question
                    ),
                )

    # "on command" methods:

    async def on_chat_inviting(self, chat_id: int) -> None:
        chat_id_from_db = await self.app.store.game_sessions.get_chat(id=chat_id)
        if chat_id != chat_id_from_db:
            chat = await self.app.store.game_sessions.add_chat_to_db(chat_id)
        await self.send_message(
            peer_id=chat_id, message=MessageHelper.bot_added_to_chat
        )
        await self.send_message(
            peer_id=chat_id,
            message=MessageHelper.initial,
            keyboard=KeyboardHelper.generate_initial_keyboard(),
        )

    async def on_start(self, chat_id: int, player_id: int) -> None:
        chat = await self.app.store.game_sessions.get_chat(chat_id)
        if not chat:
            self.logger.info("chat not in base! reinvite bot in this chat")
        chat_running_sessions = await self.app.store.game_sessions.list_sessions(
            id_only=True,
            chat_id=chat_id,
            creator_id=player_id,
            req_cnds=[
                StatesEnum.PREPARING,
                StatesEnum.WAITING_QUESTION,
                StatesEnum.WAITING_ANSWER,
            ],
        )
        if chat_running_sessions:
            await self.send_message(peer_id=chat_id, message=MessageHelper.wrong_start)
            return
        session = await self.app.store.game_sessions.create_game_session(
            chat_id, player_id
        )
        player = await self.app.store.game_sessions.get_player_by_id(player_id)
        await self.app.store.game_sessions.add_player_to_session(
            session.creator, session.id
        )
        await self.send_message(
            peer_id=chat_id, message=MessageHelper.started(name=player.name)
        )
        await self.send_message(
            peer_id=chat_id,
            message=MessageHelper.preparing,
            keyboard=KeyboardHelper.generate_preparing_keyboard(),
        )

    async def on_participate(self, chat_id: int, player_id: int) -> None:
        chat_sessions = await self.app.store.game_sessions.list_sessions(
            id_only=True, chat_id=chat_id, req_cnds=[StatesEnum.PREPARING]
        )
        if chat_sessions:
            session_id = chat_sessions[0]
            session_players = await self.app.store.game_sessions.list_players(
                id_only=True, session_id=session_id
            )
        else:
            await self.send_message(
                peer_id=chat_id, message=MessageHelper.no_preparing_session
            )
            return
        player = await self.app.store.game_sessions.get_player_by_id(player_id)
        if player_id in session_players:
            await self.send_message(
                peer_id=chat_id,
                message=MessageHelper.player_already_added(name=player.name),
            )
            return
        await self.app.store.game_sessions.add_player_to_session(player_id, session_id)
        await self.send_message(
            peer_id=chat_id, message=MessageHelper.new_player_added(name=player.name)
        )

    async def on_run(self, chat_id: int, player_id: int) -> None:
        chat_sessions = await self.app.store.game_sessions.list_sessions(
            id_only=True, chat_id=chat_id, req_cnds=[StatesEnum.PREPARING]
        )
        if chat_sessions:
            session_id = chat_sessions[0]
            session = await self.get_session_by_id(session_id)
        else:
            await self.send_message(
                peer_id=chat_id, message=MessageHelper.no_preparing_session
            )
            return
        player = await self.app.store.game_sessions.get_player_by_id(player_id)
        creator = await self.app.store.game_sessions.get_player_by_id(session.creator)
        if session.creator == player_id:
            session_players = await self.app.store.game_sessions.list_players(
                id_only=True, session_id=session_id
            )
        else:
            await self.send_message(
                peer_id=chat_id,
                message=MessageHelper.not_creator_to_run(
                    name=player.name, creator_name=creator.name
                ),
            )
            return
        if len(session_players) < MIN_PLAYERS:
            await self.send_message(
                peer_id=chat_id, message=MessageHelper.not_enough_players
            )
            return
        if len(session_players) > MAX_PLAYERS:
            await self.send_message(
                peer_id=chat_id, message=MessageHelper.too_many_players
            )
            return
        questions = await self.app.store.game_sessions.add_questions_to_session(
            session.id, theme_limit=QUIZ_THEME_AMOUNT, questions_points=QUESTIONS_POINTS
        )
        if not questions:
            await self.send_message(
                peer_id=chat_id, message=MessageHelper.no_question_in_db
            )
            return
        answerer = await self.app.store.game_sessions.set_answerer(
            session_id, to_set=session_players
        )
        await self.app.store.game_sessions.set_session_state(
            session.id, StatesEnum.WAITING_QUESTION
        )
        await self.send_message(peer_id=chat_id, message=MessageHelper.start_quiz)
        await self.send_message(
            peer_id=chat_id,
            message=MessageHelper.choose_question(name=answerer.name),
            keyboard=KeyboardHelper.generate_questions_keyboard(questions=questions),
        )

    async def on_choosing_question(
        self, chat_id: int, question_id: int, player_id: int
    ) -> None:
        chat_sessions = await self.app.store.game_sessions.list_sessions(
            id_only=True, chat_id=chat_id, req_cnds=[StatesEnum.WAITING_QUESTION]
        )
        if chat_sessions:
            session_id = chat_sessions[0]
            session_state = await self.get_session_by_id(session_id, return_state=True)
        else:
            await self.send_message(
                peer_id=chat_id, message=MessageHelper.no_running_session
            )
            return
        if not player_id == session_state.last_answerer:
            last_answerer = await self.app.store.game_sessions.get_player_by_id(
                session_state.last_answerer
            )
            await self.send_message(
                peer_id=chat_id,
                message=MessageHelper.not_last_answerer(name=last_answerer.name),
            )
            return
        is_answered = await self.check_if_question_already_answered(
            question_id, session_id
        )
        if is_answered:
            await self.send_message(
                peer_id=chat_id, message=MessageHelper.question_already_answered
            )
            return
        question = await self.app.store.game_sessions.set_current_question(
            session_id, question_id
        )
        await self.app.store.game_sessions.set_session_state(
            session_id, StatesEnum.WAITING_ANSWER
        )
        await self.send_message(
            peer_id=chat_id,
            message=MessageHelper.question(question=question.title),
            keyboard=KeyboardHelper.generate_answers_keyboard(question=question),
        )

    async def on_choosing_answer(
        self, chat_id: int, is_correct: bool, player_id: int
    ) -> None:
        chat_sessions = await self.app.store.game_sessions.list_sessions(
            id_only=True, chat_id=chat_id, req_cnds=[StatesEnum.WAITING_ANSWER]
        )
        player = await self.app.store.game_sessions.get_player_by_id(player_id)
        if chat_sessions:
            session_id = chat_sessions[0]
        else:
            await self.send_message(
                peer_id=chat_id, message=MessageHelper.no_running_session
            )
            return
        players = await self.app.store.game_sessions.list_players(
            id_only=True, session_id=session_id, can_answer=True
        )
        if player_id not in players:
            await self.send_message(
                peer_id=chat_id, message=MessageHelper.can_not_answer(name=player.name)
            )
            return
        await self.question_answered(chat_id, player_id, session_id, is_correct)

    async def question_answered(
        self, chat_id: int, player_id: int, session_id: int, is_correct: bool
    ) -> None:
        session_state = await self.get_session_by_id(session_id, return_state=True)
        current_question_id = session_state.current_question
        question = await self.app.store.quizzes.get_question_by_id(current_question_id)
        if is_correct:
            await self.on_correct_answer(
                chat_id, session_id, player_id, question, current_question_id
            )
        else:
            await self.on_wrong_answer(
                chat_id, session_id, player_id, question, current_question_id
            )

    async def on_correct_answer(
        self,
        chat_id: int,
        session_id: int,
        player_id: int,
        question: Question,
        question_id: int,
    ) -> None:
        current_points = await self.app.store.game_sessions.add_points_to_player(
            session_id, player_id, question.points
        )
        player = await self.app.store.game_sessions.get_player_by_id(player_id)
        await self.app.store.game_sessions.restore_answering(session_id)
        await self.send_message(
            peer_id=chat_id,
            message=MessageHelper.answered_correct(
                name=player.name,
                points=str(question.points),
                curpoints=str(current_points),
            ),
        )
        await self.app.store.game_sessions.set_answerer(session_id, to_set=player_id)
        await self.app.store.game_sessions.set_question_answered(question_id)
        await self.after_answering(chat_id, session_id, player_id)

    async def on_wrong_answer(
        self,
        chat_id: int,
        session_id: int,
        player_id: int,
        question: Question,
        question_id: int,
    ) -> None:
        current_points = await self.app.store.game_sessions.add_points_to_player(
            session_id, player_id, -question.points
        )
        player = await self.app.store.game_sessions.get_player_by_id(player_id)
        answer = next(
            (x for x in question.answers if x.is_correct), "No correct answer"
        )
        await self.send_message(
            peer_id=chat_id,
            message=MessageHelper.answered_wrong(
                name=player.name,
                points=str(-question.points),
                curpoints=str(current_points),
            ),
        )
        await self.app.store.game_sessions.forbid_answering(session_id, player_id)
        no_players_left = await self.app.store.game_sessions.check_if_no_players_left(
            session_id
        )
        if no_players_left:
            await self.send_message(
                peer_id=chat_id,
                message=MessageHelper.no_players_left(answer=answer.title),
            )
            await self.app.store.game_sessions.set_question_answered(question_id)
            await self.after_answering(chat_id, session_id, player_id)
        else:
            await self.send_message(
                peer_id=chat_id,
                message=MessageHelper.question(question=question.title),
                keyboard=KeyboardHelper.generate_answers_keyboard(question=question),
            )

    async def after_answering(
        self, chat_id: int, session_id: int, player_id: int
    ) -> None:
        has_unanswered = await self.check_if_some_questions_unanswered(session_id)
        player = await self.app.store.game_sessions.get_player_by_id(player_id)
        if has_unanswered:
            questions = await self.get_questions_of_session(session_id, answered=False)
            await self.app.store.game_sessions.restore_answering(session_id)
            await self.app.store.game_sessions.set_session_state(
                session_id, StatesEnum.WAITING_QUESTION
            )
            await self.send_message(
                peer_id=chat_id,
                message=MessageHelper.choose_question(name=player.name),
                keyboard=KeyboardHelper.generate_questions_keyboard(
                    questions=questions
                ),
            )
        else:
            results = await self.end_game_session(session_id)
            await self.send_message(
                peer_id=chat_id,
                message=MessageHelper.quiz_ended(results=results),
                keyboard=KeyboardHelper.generate_initial_keyboard(),
            )

    async def on_stop(self, chat_id: int, player_id: int) -> None:
        chat_sessions = await self.app.store.game_sessions.list_sessions(
            id_only=True,
            chat_id=chat_id,
            req_cnds=[
                StatesEnum.PREPARING,
                StatesEnum.WAITING_QUESTION,
                StatesEnum.WAITING_ANSWER,
            ],
        )
        if chat_sessions:
            session_id = chat_sessions[0]
            session = await self.get_session_by_id(session_id)
        else:
            await self.send_message(
                peer_id=chat_id, message=MessageHelper.no_session_to_stop
            )
            return
        player = await self.app.store.game_sessions.get_player_by_id(player_id)
        creator = await self.app.store.game_sessions.get_player_by_id(session.creator)
        if session.creator != player_id:
            await self.send_message(
                peer_id=chat_id,
                message=MessageHelper.not_creator_to_stop(
                    name=player.name, creator_name=creator.name
                ),
            )
            return
        results = await self.end_game_session(session_id)
        await self.send_message(
            peer_id=chat_id,
            message=MessageHelper.quiz_ended_on_stop(name=player.name, results=results),
            keyboard=KeyboardHelper.generate_initial_keyboard(),
        )

    async def on_show_results(self, chat_id: int):
        last_session_id = await self.last_session(chat_id=chat_id)
        if not last_session_id:
            await self.send_message(peer_id=chat_id, message=MessageHelper.no_results)
            return
        results = await self.app.store.game_sessions.get_session_results(
            last_session_id[0]
        )
        await self.send_message(
            peer_id=chat_id, message=MessageHelper.just_show_results(results=results)
        )

    async def last_session(self, chat_id: int) -> list[int]:
        game_session_id = await self.app.store.game_sessions.list_sessions(
            id_only=True, chat_id=chat_id, last=True
        )
        return game_session_id

    async def get_questions_of_session(
        self,
        session_id: int,
        answered: Optional[bool] = None,
        id_only: bool = False,
        to_dict: bool = True,
    ) -> Union[list[Question], dict[str, dict[int, Question]], None]:
        questions = await self.app.store.game_sessions.get_questions_of_session(
            session_id=session_id,
            id_only=id_only,
            answered=answered,
        )
        if to_dict and not id_only:
            theme_ids = set([x.theme_id for x in questions])
            theme_ids_to_names = {}
            for theme_id in theme_ids:
                theme = await self.app.store.quizzes.get_theme_by_id(theme_id)
                theme_ids_to_names[theme_id] = theme.title
            questions_dict = defaultdict(dict)
            for x in questions:
                questions_dict[theme_ids_to_names[x.theme_id]][x.points] = x
            questions = questions_dict  # questions_dict ~ {theme1: {10: (qst1, is_answered), 20: (qst2, is_answered)},
        return questions  # theme2: {10: (qst1, is_answered), 20: (qst2, is_answered)}}

    async def get_session_by_id(
        self, session_id: int, return_state: bool = False
    ) -> Union[GameSession, SessionState]:
        if return_state:
            state = await self.app.store.game_sessions.get_session_state_by_id(
                session_id
            )
            return state
        session = await self.app.store.game_sessions.get_game_session_by_id(session_id)
        return session

    async def check_if_question_already_answered(
        self, question_id: id, session_id: id
    ) -> bool:
        answered_questions = await self.get_questions_of_session(
            session_id=session_id, answered=True, to_dict=False, id_only=True
        )

        return question_id in answered_questions

    async def check_if_some_questions_unanswered(self, session_id: id) -> bool:
        unanswered_questions = await self.get_questions_of_session(
            session_id=session_id, answered=False, to_dict=False, id_only=True
        )
        return any(unanswered_questions)

    async def end_game_session(self, session_id) -> dict[int, int]:
        await self.app.store.game_sessions.set_session_state(
            session_id, StatesEnum.ENDED
        )
        results = await self.app.store.game_sessions.get_session_results(session_id)
        return results

    async def send_message(
        self, peer_id: int, message: str, keyboard: Optional[str] = None
    ) -> None:
        params = {"peer_id": peer_id, "message": message, "keyboard": keyboard}
        await self.app.store.vk_api.send_message(**params)
