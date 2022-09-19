import random
from typing import Optional, Union
from sqlalchemy import select, or_, and_, update, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import BooleanClauseList

from app.base.base_accessor import BaseAccessor
from app.game_session.models import (
    GameSession,
    GameSessionModel,
    Chat,
    ChatModel,
    Player,
    PlayerModel,
    SessionStateModel,
    PlayersSessions,
    SessionsQuestions,
    SessionState,
    StatesEnum,
)
from app.quiz.models import Question


class GameSessionAccessor(BaseAccessor):
    # Conditions for sqlalchemy filters
    chats_with_sessions = select(GameSessionModel.chat_id)
    filter_running_states = SessionStateModel.state_name != StatesEnum.ENDED.value
    chats_with_running_sessions = chats_with_sessions.join(SessionStateModel).filter(
        filter_running_states
    )
    chats_with_no_session = ChatModel.id.notin_(chats_with_sessions)
    chats_with_no_running_sessions = ChatModel.id.notin_(chats_with_running_sessions)
    chats_session_needed = or_(chats_with_no_session, chats_with_no_running_sessions)

    def filter_by_states(
        self,
        states: list[StatesEnum],
        logic: Union[or_, and_] = or_,
        selecting_chats: bool = None,
    ) -> BooleanClauseList:
        conditions_list = []
        for state in states:
            conditions_list.append(SessionStateModel.state_name == state.value)
        condition = logic(*conditions_list)
        if selecting_chats:
            condition = ChatModel.id.in_(
                self.chats_with_sessions.join(SessionStateModel).filter(condition)
            )

        return condition

    async def add_chat_to_db(self, db_session: AsyncSession, chat_id: int) -> Chat:
        chat = ChatModel(id=chat_id)
        db_session.add(chat)
        chat = Chat(id=chat.id)
        return chat

    async def add_player_to_db(self, db_session: AsyncSession, player_id: int) -> Player:
        name = await self.app.store.vk_api.get_user_name(player_id)
        player = PlayerModel(id=player_id, name=name)
        db_session.add(player)
        await db_session.flush()
        player = Player(id=player.id, name=player.name)
        return player

    async def create_game_session(self, db_session: AsyncSession, chat_id: int, creator_id: int) -> GameSession:
        creator = await self.get_player_by_id(db_session=db_session, id=creator_id, dc=False)
        if not creator:
            await self.app.store.game_sessions.add_player_to_db(
                db_session=db_session, player_id=creator_id
            )
        game_session = GameSessionModel(chat_id=chat_id, creator=creator_id)
        session_state = SessionStateModel(
            session=game_session, state_name=StatesEnum.PREPARING.value
        )
        db_session.add(game_session)
        db_session.add(session_state)
        await db_session.flush()
        game_session = GameSession(
            id=game_session.id,
            chat_id=game_session.chat_id,
            creator=game_session.creator,
            state=SessionState(
                session_id=session_state.session_id,
                state_name=session_state.state_name,
                current_question=session_state.current_question,
                last_answerer=session_state.last_answerer,
            ),
        )
        return game_session

    async def set_session_state(self, db_session: AsyncSession, session_id: int, new_state: StatesEnum) -> None:
        stmt = (
            update(SessionStateModel)
            .where(SessionStateModel.session_id == session_id)
            .values(state_name=new_state.value)
        )
        await db_session.execute(stmt)

    async def add_player_to_session(self, db_session: AsyncSession, player_id: int, session_id: int) -> None:
        player = await self.get_player_by_id(db_session=db_session, id=player_id, dc=False)
        if not player:
            await self.add_player_to_db(db_session=db_session, player_id=player_id)
        association = PlayersSessions(
            player_id=player_id, session_id=session_id
        )
        db_session.add(association)

    async def add_questions_to_session(
        self,
        db_session: AsyncSession,
        session_id: int,
        theme_limit: int,
        questions_points: list[int]
    ) -> dict[str, dict[int, Question]]:
        questions = {}
        themes = await self.app.store.quizzes.list_themes(limit=theme_limit)
        for theme in themes:
            questions[theme.title] = {}
            for req_points in questions_points:
                questions_list = await self.app.store.quizzes.list_questions(
                    db_session=db_session, theme_id=theme.id, points=req_points
                )
                question = random.choice(questions_list)

                questions[theme.title][req_points] = question
                association = SessionsQuestions(
                    session_state_id=session_id,
                    question_id=question.id,
                    is_answered=False,
                )
                db_session.add(association)
        return questions

    async def set_current_question(
            self, db_session: AsyncSession, session_id: int, question_id: int
    ) -> Question:
        stmt = (
            update(SessionStateModel)
            .where(SessionStateModel.session_id == session_id)
            .values(current_question=question_id)
        )
        await db_session.execute(stmt)
        question = await self.app.store.quizzes.get_question_by_id(
            db_session=db_session,
            id=question_id
        )
        return question

    async def get_questions_of_session(
        self,
        db_session: AsyncSession,
        session_id: int,
        answered: Optional[bool] = None,
        id_only: bool = False,
    ) -> Union[list[int], list[Question]]:
        questions_list = await self.app.store.quizzes.list_questions(
            db_session=db_session,
            session_id=session_id,
            answered=answered,
        )
        if id_only:
            return [q.id for q in questions_list]
        return questions_list

    async def set_answerer(
        self, db_session: AsyncSession, session_id: int, to_set: Union[list[int], int]
    ) -> Player:
        if type(to_set) == list:
            to_set = random.choice(to_set)
        answerer = await self.get_player_by_id(db_session=db_session, id=to_set)
        stmt = (
            update(SessionStateModel)
            .where(SessionStateModel.session_id == session_id)
            .values(last_answerer=answerer.id)
        )
        await db_session.execute(stmt)
        return answerer

    async def set_question_answered(self, db_session: AsyncSession, question_id: int) -> None:
        stmt = (
            update(SessionsQuestions)
            .where(SessionsQuestions.question_id == question_id)
            .values(is_answered=True)
        )
        await db_session.execute(stmt)

    def chat_filter_condition(
        self, req_cnd: Optional[StatesEnum] = None
    ) -> BooleanClauseList:
        if req_cnd == StatesEnum.SESSION_NEEDED:
            condition = self.chats_session_needed
        else:
            condition = self.filter_by_states([req_cnd], selecting_chats=True)
        return condition

    async def list_chats(
        self, db_session: AsyncSession, req_cnd: Optional[StatesEnum] = None
    ) -> Union[list[Chat], list[int]]:
        stmt = select(ChatModel)
        if req_cnd:
            condition = self.chat_filter_condition(req_cnd)
            stmt = stmt.filter(condition)
        result = await db_session.execute(stmt)
        curr = result.scalars()
        return [chat.id for chat in curr]

    async def get_chat(self, db_session: AsyncSession, id: int):
        stmt = select(ChatModel).filter(ChatModel.id == id)
        result = await db_session.execute(stmt)
        chat_id = result.scalars().first()
        return chat_id

    async def list_sessions(
        self,
        db_session: AsyncSession,
        id_only: bool = False,
        req_cnds: Optional[list[StatesEnum]] = None,
        chat_id: Optional[int] = None,
        creator_id: Optional[int] = None,
        last: bool = False,
    ) -> Union[list[GameSession], list[int]]:
        stmt = select(GameSessionModel, SessionStateModel).join(
            SessionStateModel
        )
        if req_cnds:
            condition = self.filter_by_states(req_cnds)
            stmt = stmt.filter(condition)
        if chat_id:
            stmt = stmt.filter(GameSessionModel.chat_id == chat_id)
        if creator_id:
            stmt = stmt.filter(GameSessionModel.creator == creator_id)
        if last:
            condition = self.filter_by_states(
                [
                    StatesEnum.ENDED,
                    StatesEnum.WAITING_QUESTION,
                    StatesEnum.WAITING_ANSWER,
                ]
            )
            stmt = (
                stmt.filter(condition)
                .order_by(desc(SessionStateModel.time_updated))
                .limit(1)
            )
        result = await db_session.execute(stmt)
        if id_only:
            return [game_session.id for game_session, state in result]
        else:
            return [
                GameSession(
                    id=game_session.id,
                    chat_id=game_session.chat_id,
                    creator=game_session.creator,
                    state=SessionState(
                        session_id=state.session_id,
                        state_name=state.state_name,
                        current_question=state.current_question,
                        last_answerer=state.last_answerer,
                    ),
                )
                for game_session, state in result
            ]

    async def list_players(
        self,
        db_session: AsyncSession,
        id_only: bool = False,
        session_id: Optional[int] = None,
        can_answer: Optional[bool] = None,
    ) -> Union[list[Player], list[int]]:
        stmt = select(PlayerModel)
        if session_id:
            stmt = stmt.filter(
                PlayerModel.association_players_sessions.any(
                    PlayersSessions.session_id == session_id
                )
            )
            if can_answer is not None:
                stmt = stmt.filter(
                    PlayerModel.association_players_sessions.any(
                        PlayersSessions.can_answer == can_answer
                    )
                )
        result = await db_session.execute(stmt)
        curr = result.scalars()
        if id_only:
            return [player.id for player in curr]
        else:
            return [Player(id=player.id, name=player.name) for player in curr]

    async def get_player_by_id(self, db_session: AsyncSession, id: int, dc=True) -> Union[Player, PlayerModel]:
        stmt = select(PlayerModel).filter(PlayerModel.id == id)
        result = await db_session.execute(stmt)
        player = result.scalars().first()
        if player:
            if not dc:
                return player
            else:
                return Player(id=player.id, name=player.name)

    async def get_game_session_by_id(
        self, db_session: AsyncSession, id: int, dc: bool = True
    ) -> Union[GameSession, GameSessionModel]:
        stmt = (
            select(GameSessionModel, SessionStateModel)
            .join(SessionStateModel)
            .filter(GameSessionModel.id == id)
        )
        rows = await db_session.execute(stmt)
        game_session, state = next(rows, None)
        if game_session:
            if not dc:
                return game_session
            else:
                return GameSession(
                    id=game_session.id,
                    chat_id=game_session.chat_id,
                    creator=game_session.creator,
                    state=SessionState(
                        session_id=state.session_id,
                        state_name=state.state_name,
                        current_question=state.current_question,
                        last_answerer=state.last_answerer,
                    ),
                )

    async def get_session_state_by_id(
        self, db_session: AsyncSession, id: int, dc: bool = True
    ) -> Union[SessionState, SessionStateModel]:
        stmt = select(SessionStateModel).filter(
            SessionStateModel.session_id == id
        )
        result = await db_session.execute(stmt)
        state = result.scalars().first()
        if state:
            if not dc:
                return state
            else:
                return SessionState(
                    session_id=state.session_id,
                    state_name=state.state_name,
                    last_answerer=state.last_answerer,
                    current_question=state.current_question,
                )

    async def add_points_to_player(
        self, db_session: AsyncSession, session_id: int, player_id: int, points: int
    ) -> int:
        stmt = select(PlayersSessions).where(
            and_(
                PlayersSessions.player_id == player_id,
                PlayersSessions.session_id == session_id,
            )
        )
        result = await db_session.execute(stmt)
        current_points = result.scalars().first().points
        current_points += points
        stmt = (
            update(PlayersSessions)
            .where(
                and_(
                    PlayersSessions.player_id == player_id,
                    PlayersSessions.session_id == session_id,
                )
            )
            .values(points=current_points)
        )
        await db_session.execute(stmt)
        return current_points

    async def restore_answering(self, db_session: AsyncSession, session_id: int) -> None:
        stmt = (
            update(PlayersSessions)
            .where(PlayersSessions.session_id == session_id)
            .values(can_answer=True)
        )
        await db_session.execute(stmt)

    async def forbid_answering(self, db_session: AsyncSession, session_id: int, player_id: int) -> None:
        stmt = (
            update(PlayersSessions)
            .where(
                and_(
                    PlayersSessions.session_id == session_id,
                    PlayersSessions.player_id == player_id,
                )
            )
            .values(can_answer=False)
        )
        await db_session.execute(stmt)

    async def check_if_no_players_left(self, db_session: AsyncSession, session_id: int) -> bool:
        stmt = select(PlayersSessions).where(
            PlayersSessions.session_id == session_id
        )
        result = await db_session.execute(stmt)
        session_players = result.scalars()
        for player in session_players:
            if player.can_answer:
                return False
        return True

    async def get_session_results(self, db_session: AsyncSession, session_id: int) -> dict[int, int]:
        to_return = {}
        stmt = select(PlayersSessions).where(
            PlayersSessions.session_id == session_id
        )
        result = await db_session.execute(stmt)
        session_players = result.scalars()
        for session_player in session_players:
            player = await self.get_player_by_id(db_session, session_player.player_id)
            to_return[player.name] = session_player.points
        return to_return
