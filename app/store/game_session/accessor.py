from typing import Optional, Union
import logging
from sqlalchemy import select, join, delete, text, or_, and_
from app.base.base_accessor import BaseAccessor
from app.game_session.models import (
    GameSession, GameSessionModel,
    Chat, ChatModel,
    Player, PlayerModel,
    SessionStateModel,
    PlayersSessions
)


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
                game_session = await self.get_game_session_by_id(id=session_id, dc=True)
                game_session

    async def add_player_to_game_session(self, player_id: int, session_id: int) -> None:
        async with self.app.database.session() as session:
            async with session.begin():
                player = await self.get_player_by_id(id=player_id, dc=False)
                if not player:
                    await self.app.store.game_sessions.add_player_to_db(player_id=player_id)
                game_session = await self.get_game_session_by_id(id=session_id, dc=False)
                if game_session:
                    association_players_sessions = PlayersSessions(player_id=player_id, session_id=session_id)
                    session.add(association_players_sessions)
                else:
                    self.logger.error("No session with that id")

    def chat_filter_condition(self, req_cnd: Optional[str] = None):
        """
        :param req_cnd: if "no_running_session", return condition for selecting chats that have no
        running game. That means, every chat in select either has no session or has only ended sessions.
        If req_cnd is in SessionStateModel.states.values, condition is being made with filter_by_states method

        :return: condition for chat filter function.
        """
        condition = None
        if req_cnd == "chats_session_needed":
            condition = self.chats_session_needed
        if req_cnd in SessionStateModel.states:
            condition = self.filter_by_states([req_cnd], selecting="chats")
        return condition

    async def list_chats(self, id_only: bool = False,
                         req_cnd: Optional[str] = None,
                         id: Optional[int] = None) -> Union[list[Chat], list[int]]:
        """
        :param: id_only: if True, function returns list with int IDs of chats, else list with Chat dataclass instances.
        :param: req_cnd: arg for make_chat_filter_condition function.

        :return: list with integer IDs of chats or list with Chat dataclass instances.
        """
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

    async def get_game_session_by_id(self, id: int, dc=True) -> Union[GameSession, GameSessionModel]:
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

    async def add_questions_to_session(self, session_id):
        session_id
