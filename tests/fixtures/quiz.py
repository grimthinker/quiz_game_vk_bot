import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.quiz.models import (
    Answer,
    AnswerModel,
    Question,
    QuestionModel,
    Theme,
    ThemeModel,
)


@pytest.fixture
def answers(store) -> list[Answer]:
    return [
        Answer(title="1", is_correct=True),
        Answer(title="2", is_correct=False),
        Answer(title="3", is_correct=False),
        Answer(title="4", is_correct=False),
    ]


@pytest.fixture
async def theme_1(db_session: AsyncSession) -> Theme:
    title = "web-development"
    new_theme = ThemeModel(title=title)
    async with db_session.begin() as session:
        session.add(new_theme)

    return Theme(id=new_theme.id, title=title)


@pytest.fixture
async def theme_2(db_session: AsyncSession) -> Theme:
    title = "backend"
    new_theme = ThemeModel(title=title)
    async with db_session.begin() as session:
        session.add(new_theme)

    return Theme(id=new_theme.id, title=title)


@pytest.fixture
async def question_1(db_session, theme_1: Theme) -> Question:
    title = "how are you?"
    async with db_session.begin() as session:
        question = QuestionModel(
            title=title,
            theme_id=theme_1.id,
            points=100,
            answers=[
                AnswerModel(
                    title="well",
                    is_correct=True,
                ),
                AnswerModel(
                    title="bad",
                    is_correct=False,
                ),
            ],
        )

        session.add(question)

    return Question(
        id=question.id,
        title=title,
        theme_id=theme_1.id,
        points=question.points,
        answers=[
            Answer(
                title=a.title,
                is_correct=a.is_correct,
            )
            for a in question.answers
        ],
    )


@pytest.fixture
async def question_2(db_session, theme_1: Theme) -> Question:
    title = "are you doing fine?"
    async with db_session.begin() as session:
        question = QuestionModel(
            title=title,
            theme_id=theme_1.id,
            points=200,
            answers=[
                AnswerModel(
                    title="yep",
                    is_correct=True,
                ),
                AnswerModel(
                    title="nop",
                    is_correct=False,
                ),
            ],
        )

        session.add(question)

    return Question(
        id=question.id,
        title=question.title,
        theme_id=theme_1.id,
        points=question.points,
        answers=[
            Answer(
                title=a.title,
                is_correct=a.is_correct,
            )
            for a in question.answers
        ],
    )


@pytest.fixture
async def fill_db_with_questions(db_session):
    for x in range(3):
        new_theme = ThemeModel(id=x + 1, title=f"theme {x+1}")
        async with db_session.begin() as session:
            session.add(new_theme)
        for q in range(3):
            question = QuestionModel(
                title=f"question {q+1} of theme {x+1}",
                theme_id=x + 1,
                points=(q + 1) * 100,
                answers=[
                    AnswerModel(title="answer 1", is_correct=False),
                    AnswerModel(title="answer 2", is_correct=True),
                    AnswerModel(title="answer 3", is_correct=False),
                ],
            )
            async with db_session.begin() as session:
                session.add(question)
    yield
