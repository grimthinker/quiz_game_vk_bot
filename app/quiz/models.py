from dataclasses import dataclass
from typing import Union

from sqlalchemy.orm import relationship

from app.store.database.sqlalchemy_base import db
from sqlalchemy import (
    Integer,
    Column,
    BigInteger,
    String,
    Boolean,
    ForeignKey,
)


@dataclass
class Theme:
    id: Union[int, None]
    title: str


@dataclass
class Question:
    id: Union[int, None]
    title: str
    theme_id: int
    points: int
    answers: list["Answer"]


@dataclass
class Answer:
    title: str
    is_correct: bool


class ThemeModel(db):
    __tablename__ = "themes"
    id = Column(BigInteger, primary_key=True)
    title = Column(String, nullable=False, unique=True)
    questions = relationship(
        "QuestionModel",
        backref="theme",
        cascade="all, delete",
        passive_deletes=True,
    )


class QuestionModel(db):
    __tablename__ = "questions"
    id = Column(BigInteger, primary_key=True)
    theme_id = Column(
        BigInteger,
        ForeignKey("themes.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String, nullable=False, unique=True)
    points = Column(Integer, nullable=False)
    answers = relationship(
        "AnswerModel",
        backref="question",
        cascade="all, delete",
        passive_deletes=True,
    )
    sessions = relationship(
        "SessionsQuestions",
        backref="questions",
        cascade="all, delete",
        passive_deletes=True,
    )


class AnswerModel(db):
    __tablename__ = "answers"
    id = Column(BigInteger, primary_key=True)
    question_id = Column(
        BigInteger,
        ForeignKey("questions.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String, nullable=False, unique=False)
    is_correct = Column(Boolean, nullable=False)
