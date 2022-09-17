import enum
from dataclasses import dataclass
from typing import Optional

from app.store.database.sqlalchemy_base import db
from sqlalchemy.orm import relationship, backref
from sqlalchemy import (
    Column,
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    Text,
    Table, DateTime, func
)


@dataclass
class Chat:
    id: int


@dataclass
class Player:
    id: int


@dataclass
class SessionState:
    session_id: int
    state_name: str
    current_question: Optional[int] = None
    last_answerer: Optional[int] = None
    time_updated: Optional[str] = None


@dataclass
class GameSession:
    id: int
    chat_id: Chat
    creator: Player
    state: SessionState


class ChatModel(db):
    __tablename__ = "chats"
    id = Column(BigInteger, primary_key=True)


class SessionStateModel(db):
    __tablename__ = "session_states"
    session_id = Column(BigInteger, ForeignKey("game_sessions.id", ondelete="CASCADE"), primary_key=True)
    state_name = Column(Integer, nullable=False)
    current_question = Column(BigInteger, ForeignKey("questions.id", ondelete="CASCADE"), nullable=True)
    last_answerer = Column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=True)
    time_updated = Column(DateTime(timezone=True), onupdate=func.now())

    session = relationship("GameSessionModel", back_populates="state", uselist=False)
    session_questions = relationship(
                            "SessionsQuestions",
                            back_populates="game_session_state",
                            cascade="all, delete",
                            passive_deletes=True,
                            )

    def to_dc(self) -> SessionState:
        return SessionState(session_id=self.session_id,
                            state_name=self.state_name,
                            current_question=self.current_question,
                            last_answerer=self.last_answerer,
                            time_updated=self.time_updated)


class StatesEnum(enum.Enum):
    PREPARING = 0
    WAITING_QUESTION = 2
    WAITING_ANSWER = 3
    ENDED = 9

    SESSION_NEEDED = 11 # not state, for chat filtering


class SessionsQuestions(db):
    __tablename__ = 'association_sessions_questions'
    session_state_id = Column(BigInteger, ForeignKey("session_states.session_id", ondelete="CASCADE"), primary_key=True)
    question_id = Column(BigInteger, ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True)
    is_answered = Column(Boolean, nullable=False)

    game_session_state = relationship(SessionStateModel, back_populates="session_questions")


class PlayersSessions(db):
    __tablename__ = 'association_players_sessions'
    player_id = Column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), primary_key=True)
    session_id = Column(BigInteger, ForeignKey("game_sessions.id", ondelete="CASCADE"), primary_key=True)
    points = Column(Integer, nullable=False, default=0)
    can_answer = Column(Boolean, nullable=False, default=True)
    can_choose_question = Column(Boolean, nullable=False, default=True)

    players = relationship("PlayerModel", back_populates="association_players_sessions")
    sessions = relationship("GameSessionModel", back_populates="association_players_sessions")


class PlayerModel(db):
    __tablename__ = "players"
    id = Column(BigInteger, primary_key=True)
    association_players_sessions = relationship(PlayersSessions, back_populates="players")


class GameSessionModel(db):
    __tablename__ = "game_sessions"
    id = Column(BigInteger, primary_key=True)
    chat_id = Column(BigInteger, ForeignKey('chats.id', ondelete="CASCADE"), nullable=False)
    creator = Column(BigInteger, ForeignKey('players.id', ondelete="CASCADE"), nullable=False)

    state = relationship(SessionStateModel, back_populates="session", uselist=False)
    association_players_sessions = relationship("PlayersSessions", back_populates="sessions")

    def to_dc(self, state) -> GameSession:
        return GameSession(id=self.id,
                           chat_id=Chat(self.chat_id),
                           creator=Player(self.creator),
                           state=state)
