from typing import Optional, Union, Iterable
import logging
from sqlalchemy import select, delete, text, and_
from app.base.base_accessor import BaseAccessor
from app.game_session.models import SessionsQuestions
from app.quiz.models import (
    Answer, AnswerModel,
    Question, QuestionModel,
    Theme, ThemeModel
)


class QuizAccessor(BaseAccessor):
    async def create_theme(self, title: str) -> Theme:
        async with self.app.database.session() as session:
            async with session.begin():
                theme = ThemeModel(title=title)
                session.add(theme)

        theme = Theme(id=theme.id, title=theme.title)
        return theme


    async def get_theme_by_title(self, title: str) -> Optional[Theme]:
        async with self.app.database.session() as session:
            async with session.begin():
                stmt = select(ThemeModel).where(ThemeModel.title == title)
                result = await session.execute(stmt)
                curr = result.scalars()
                for theme in curr:
                    return Theme(id=theme.id, title=theme.title)


    async def get_theme_by_id(self, id: int) -> Optional[Theme]:
        async with self.app.database.session() as session:
            async with session.begin():
                stmt = select(ThemeModel).where(ThemeModel.id == id)
                result = await session.execute(stmt)
                curr = result.scalars()
                for theme in curr:
                    return Theme(id=theme.id, title=theme.title)


    async def list_themes(self, limit: Optional[int] = None) -> list[Theme]:
        async with self.app.database.session() as session:
            async with session.begin():
                stmt = select(ThemeModel)
                if limit:
                    stmt = stmt.limit(limit)
                result = await session.execute(stmt)
                curr = result.scalars()
                return [Theme(id=theme.id, title=theme.title) for theme in curr]


    async def create_answers_list(self, answers):
        return [Answer(title=a['title'], is_correct=a['is_correct']) for a in answers]


    async def create_answers(
        self, question_id: int, answers: list[Answer]
    ) -> list[Answer]:
        async with self.app.database.session() as session:
            async with session.begin():
                list_to_add = [AnswerModel(
                    question_id=question_id,
                    title=a.title,
                    is_correct=a.is_correct
                ) for a in answers]
                session.add_all(list_to_add)
        return answers


    async def create_question(
        self, title: str, theme_id: int, points: int, answers: list[Answer]
    ) -> Question:

        async with self.app.database.session() as session:
            async with session.begin():
                question = QuestionModel(title=title, points=points, theme_id=theme_id)
                session.add(question)

        await self.create_answers(question_id=question.id, answers=answers)
        question = Question(id=question.id,
                            title=question.title,
                            points=question.points,
                            theme_id=question.theme_id,
                            answers=answers)
        return question


    async def get_question_by_title(self, title: str) -> Optional[Question]:
        async with self.app.database.session() as session:
            async with session.begin():
                stmt = select(QuestionModel).where(QuestionModel.title == title)
                result = await session.execute(stmt)
                curr = result.scalars()
                for q in curr:
                    stmt = select(AnswerModel).where(AnswerModel.question_id == q.id)
                    result = await session.execute(stmt)
                    curr = result.scalars()
                    answers = [Answer(is_correct=a.is_correct, title=a.title) for a in curr]
                    return Question(id=q.id, title=q.title, points=q.points, theme_id=q.theme_id, answers=answers)


    async def get_question_by_id(self, id: int) -> Optional[Question]:
        async with self.app.database.session() as session:
            async with session.begin():
                stmt = select(QuestionModel).where(QuestionModel.id == id)
                result = await session.execute(stmt)
                curr = result.scalars()
                for q in curr:
                    stmt = select(AnswerModel).where(AnswerModel.question_id == q.id)
                    result = await session.execute(stmt)
                    curr = result.scalars()
                    answers = [Answer(is_correct=a.is_correct, title=a.title) for a in curr]
                    return Question(id=q.id, title=q.title, points=q.points, theme_id=q.theme_id, answers=answers)

    async def list_questions(self, theme_id: Optional[int] = None,
                             points: Optional[int] = None,
                             limit: Optional[int] = None,
                             session_id: Optional[int] = None,
                             answered: Optional[bool] = None) -> list[Question]:
        async with self.app.database.session() as session:
            async with session.begin():
                stmt = select(QuestionModel)
                if session_id:
                    sub_conditions = [(SessionsQuestions.session_state_id == session_id)]
                    if answered is not None:
                        sub_conditions.append((SessionsQuestions.is_answered == answered))
                    condition = QuestionModel.sessions.any(and_(*sub_conditions))
                    stmt = stmt.filter(condition)
                if theme_id:
                    stmt = stmt.where(QuestionModel.theme_id == theme_id)
                if points:
                    stmt = stmt.where(QuestionModel.points == points)
                if limit:
                    stmt = stmt.limit(limit)
                result = await session.execute(stmt)
                question_list = []
                curr = result.scalars()
                for q in curr:
                    stmt = select(AnswerModel).where(AnswerModel.question_id == q.id)
                    result = await session.execute(stmt)
                    curr = result.scalars()
                    answers = [Answer(is_correct=a.is_correct, title=a.title) for a in curr]

                    question_list.append(Question(title=q.title,
                                                  id=q.id,
                                                  points=q.points,
                                                  theme_id=q.theme_id,
                                                  answers=answers,
                                                  ))
                return question_list
