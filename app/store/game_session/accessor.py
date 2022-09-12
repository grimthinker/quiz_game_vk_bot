import random
from collections import defaultdict, Counter
from typing import Optional, Union, Dict
from sqlalchemy import select, join, delete, text, or_, and_, update
from sqlalchemy.sql.elements import BooleanClauseList

from app.base.base_accessor import BaseAccessor
from app.game_session.models import (
    GameSession, GameSessionModel,
    Chat, ChatModel,
    Player, PlayerModel,
    SessionStateModel,
    PlayersSessions,
    SessionsQuestions, SessionState
)
from app.quiz.models import Question


class GameSessionAccessor(BaseAccessor):

    # Conditions for sqlalchemy filters
    chats_with_sessions = select(GameSessionModel.chat_id)
    filter_running_states = SessionStateModel.state_name != SessionStateModel.states['ended']
    chats_with_running_sessions = chats_with_sessions.join(SessionStateModel).filter(filter_running_states)
    chats_with_no_session = (ChatModel.id.notin_(chats_with_sessions))
    chats_with_no_running_sessions = (ChatModel.id.notin_(chats_with_running_sessions))
    chats_session_needed = or_(chats_with_no_session, chats_with_no_running_sessions)

    def filter_by_states(self, states: list, logic: Union[or_, and_] = or_, selecting: str = "sessions"):
        """
        :param states: list of names of states for filtering game sessions by their states
        :param logic: sqlalchemy logical operator, or_ or and_
        :param selecting: if "chats", returns expression for filtering all chats with sessions having these states
        :return: expression for filter()
        """
        conditions_list = []
        for state_name in states:
            if state_name in SessionStateModel.states:
                conditions_list.append(SessionStateModel.state_name == SessionStateModel.states[state_name])
        condition = logic(*conditions_list)
        if selecting == "chats":
            condition = ChatModel.id.in_(self.chats_with_sessions.join(SessionStateModel).filter(condition))
        return condition

    async def add_chat_to_db(self, chat_id: int) -> Chat:
        async with self.app.database.session() as session:
            async with session.begin():
                chat = ChatModel(id=chat_id)
                session.add(chat)
        chat = Chat(id=chat.id)
        return chat

    async def add_player_to_db(self, player_id: int) -> Player:
        async with self.app.database.session() as session:
            async with session.begin():
                player = PlayerModel(id=player_id)
                session.add(player)
        player = Player(id=player.id)
        return player

    async def create_game_session(self, chat_id: int, creator_id: int) -> GameSession:
        async with self.app.database.session() as session:
            async with session.begin():
                creator = await self.get_player_by_id(id=creator_id, dc=False)
                if not creator:
                    await self.app.store.game_sessions.add_player_to_db(player_id=creator_id)
                game_session = GameSessionModel(chat_id=chat_id, creator=creator_id)
                session_state = SessionStateModel(session=game_session,
                                                  state_name=SessionStateModel.states["preparing"])
                session.add(game_session)
                session.add(session_state)
        game_session = GameSession(id=game_session.id,
                                   chat_id=game_session.chat_id,
                                   creator=game_session.creator)
        return game_session

    async def set_session_state(self, session_id: int, new_state: str) -> None:
        async with self.app.database.session() as session:
            async with session.begin():
                stmt = update(SessionStateModel).\
                    where(SessionStateModel.session_id == session_id).\
                    values(state_name=SessionStateModel.states[new_state])
                await session.execute(stmt)

    async def add_player_to_session(self, player_id: int, session_id: int) -> None:
        async with self.app.database.session() as session:
            async with session.begin():
                player = await self.get_player_by_id(id=player_id, dc=False)
                if not player:
                    await self.add_player_to_db(player_id=player_id)
                association = PlayersSessions(player_id=player_id, session_id=session_id)
                session.add(association)

    async def add_questions_to_session(self, session_id: int,
                                       theme_limit: int,
                                       questions_points: list[int]) -> dict[str, dict[int, Question]]:
        questions = {}
        async with self.app.database.session() as session:
            async with session.begin():
                themes = await self.app.store.quizzes.list_themes(limit=theme_limit)
                for theme in themes:
                    questions[theme.title] = {}
                    for req_points in questions_points:
                        questions_list = await self.app.store.quizzes.list_questions(theme_id=theme.id,
                                                                                     points=req_points)
                        question = random.choice(questions_list)

                        questions[theme.title][req_points] = question
                        association = SessionsQuestions(session_state_id=session_id,
                                                        question_id=question.id,
                                                        is_answered=False)
                        session.add(association)
        return questions

    async def set_current_question(self, session_id: int, question_id: int) -> Question:
        async with self.app.database.session() as session:
            async with session.begin():
                stmt = update(SessionStateModel). \
                    where(SessionStateModel.session_id == session_id). \
                    values(current_question=question_id)
                await session.execute(stmt)
        question = await self.app.store.quizzes.get_question_by_id(id=question_id)
        return question

    async def get_questions_of_session_dict(self, session_id: int) -> dict[str, dict[int, Question]]:
        questions_list = await self.app.store.quizzes.list_questions(session_id=session_id)
        theme_ids = set([x.theme_id for x in questions_list])
        theme_ids_to_names = {}
        for theme_id in theme_ids:
            theme = await self.app.store.quizzes.get_theme_by_id(theme_id)
            theme_ids_to_names[theme_id] = theme.title
        questions = defaultdict(dict)              # questions ~ {theme1: {100: q1, 200: q2}, theme2: {100: q3, 200: q4},}
        for x in questions_list:
            questions[theme_ids_to_names[x.theme_id]][x.points] = x
        return questions

    async def choose_answerer(self, session_id:int, session_players: list[int]) -> Player:
        answerer_id = random.choice(session_players)
        answerer = await self.get_player_by_id(answerer_id)
        async with self.app.database.session() as session:
            async with session.begin():
                stmt = update(SessionStateModel)\
                      .where(SessionStateModel.session_id == session_id)\
                      .values(current_answerer=answerer.id)
                await session.execute(stmt)
        return answerer

    def chat_filter_condition(self, req_cnd: Optional[str] = None) -> BooleanClauseList:
        condition = None
        if req_cnd == "chats_session_needed":
            condition = self.chats_session_needed
        if req_cnd in SessionStateModel.states:
            condition = self.filter_by_states([req_cnd], selecting="chats")
        return condition

    async def list_chats(self, id_only: bool = False,
                         req_cnd: Optional[str] = None,
                         id: Optional[int] = None) -> Union[list[Chat], list[int]]:
        async with self.app.database.session() as session:
            async with session.begin():
                stmt = select(ChatModel)
                if req_cnd:
                    condition = self.chat_filter_condition(req_cnd)
                    stmt = stmt.filter(condition)
                if id:
                    stmt = stmt.filter(ChatModel.id == id)
                result = await session.execute(stmt)
                curr = result.scalars()
                if id_only:
                    return [chat.id for chat in curr]
                else:
                    return [Chat(id=chat.id) for chat in curr]

    async def list_sessions(self, id_only: bool = False,
                            req_cnds: Optional[list[str]] = None,
                            chat_id: Optional[int] = None,
                            creator_id: Optional[int] = None) -> Union[list[GameSession], list[int]]:
        async with self.app.database.session() as session:
            async with session.begin():
                stmt = select(GameSessionModel)
                if req_cnds:
                    condition = self.filter_by_states(req_cnds)
                    stmt = stmt.filter(condition)
                if chat_id:
                    stmt = stmt.filter(GameSessionModel.chat_id == chat_id)
                if creator_id:
                    stmt = stmt.filter(GameSessionModel.creator == creator_id)
                result = await session.execute(stmt)
                curr = result.scalars()

                if id_only:
                    return [game_session.id for game_session in curr]
                else:
                    return [
                        GameSession(
                            id=game_session.id,
                            chat_id=game_session.chat_id,
                            creator=game_session.creator
                        )
                        for game_session in curr
                    ]

    async def list_players(self, id_only: bool = False,
                           session_id: Optional[int] = None) -> Union[list[Player], list[int]]:
        async with self.app.database.session() as session:
            async with session.begin():
                stmt = select(PlayerModel)
                if session_id:
                    stmt = stmt.filter(
                        PlayerModel.association_players_sessions.any(
                            PlayersSessions.session_id == session_id
                        )
                    )
                result = await session.execute(stmt)
                curr = result.scalars()
                if id_only:
                    return [player.id for player in curr]
                else:
                    return [Player(id=player.id) for player in curr]

    async def get_player_by_id(self, id: int, dc=True) -> Union[Player, PlayerModel]:
        async with self.app.database.session() as session:
            async with session.begin():
                stmt = select(PlayerModel).filter(PlayerModel.id == id)
                result = await session.execute(stmt)
                player = result.scalars().first()
                if player:
                    if not dc:
                        return player
                    else:
                        return Player(id=player.id)

    async def get_game_session_by_id(self, id: int, dc: bool = True) -> Union[GameSession, GameSessionModel]:
        async with self.app.database.session() as session:
            async with session.begin():
                stmt = select(GameSessionModel).filter(GameSessionModel.id == id)
                result = await session.execute(stmt)
                game_session = result.scalars().first()
                if game_session:
                    if not dc:
                        return game_session
                    else:
                        return GameSession(
                                id=game_session.id,
                                chat_id=game_session.chat_id,
                                creator=game_session.creator,
                        )

    async def get_session_state_by_id(self, id: int, dc: bool = True) -> Union[SessionState, SessionStateModel]:
        async with self.app.database.session() as session:
            async with session.begin():
                stmt = select(SessionStateModel).filter(SessionStateModel.session_id == id)
                result = await session.execute(stmt)
                state = result.scalars().first()
                if state:
                    if not dc:
                        return state
                    else:
                        return SessionState(
                            session_id=state.session_id,
                            state_name=state.state_name,
                            current_answerer=state.current_answerer,
                            current_question=state.current_question,
                            ended=state.ended
                        )
