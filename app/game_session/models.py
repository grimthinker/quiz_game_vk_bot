from dataclasses import dataclass
from app.store.database.sqlalchemy_base import db
from sqlalchemy.orm import relationship, backref
from sqlalchemy import (
    Column,
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    Text,
    Table
)


@dataclass
class Chat:
    id: int


@dataclass
class Player:
    id: int


@dataclass
class GameSession:
    id: int
    chat_id: int
    creator: Player


class ChatModel(db):
    __tablename__ = "chats"
    id = Column(BigInteger, primary_key=True)


class SessionStateModel(db):
    __tablename__ = "session_states"
    session_id = Column(BigInteger, ForeignKey("game_sessions.id", ondelete="CASCADE"), primary_key=True)
    state_name = Column(Integer, nullable=False)
    current_question = Column(BigInteger, ForeignKey("questions.id", ondelete="CASCADE"), nullable=True)
    current_answerer = Column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=True)
    ended = Column(Text, nullable=True)

    session = relationship("GameSessionModel", back_populates="state", uselist=False)
    session_questions = relationship(
                            "SessionsQuestions",
                            back_populates="game_session_state",
                            cascade="all, delete",
                            passive_deletes=True,
                            )

    states = {"preparing": 0,
              "just_started": 2,
              "question_asked": 3,
              "answered_wrong": 4,
              "answered_right": 5,
              "ended": 9}


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

