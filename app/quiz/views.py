from aiohttp_apispec import docs, request_schema, response_schema, querystring_schema
from app.web.mixins import AuthRequiredMixin
from app.quiz.schemes import (
    ListQuestionSchema,
    QuestionSchema,
    ThemeIdSchema,
    ThemeListSchema,
    ThemeSchema,
    AnswerSchema,
)
from app.web.app import View
from app.web.schemes import OkResponseSchema
from app.web.utils import json_response, check_answers


from aiohttp.web_exceptions import (
    HTTPConflict,
    HTTPUnauthorized,
    HTTPBadRequest,
    HTTPNotFound,
)


class ThemeAddView(AuthRequiredMixin, View):
    @request_schema(ThemeSchema)
    @response_schema(OkResponseSchema, 200)
    async def post(self):
        title = self.data["title"]
        existing_theme = await self.store.quizzes.get_theme_by_title(title=title)
        print(existing_theme)
        if existing_theme:
            raise HTTPConflict
        theme = await self.store.quizzes.create_theme(title=title)
        return json_response(data=ThemeSchema().dump(theme))


class ThemeListView(AuthRequiredMixin, View):
    @response_schema(ThemeListSchema)
    async def get(self):
        themes = await self.store.quizzes.list_themes()
        return json_response(data=ThemeListSchema().dump({"themes": themes}))


class QuestionAddView(AuthRequiredMixin, View):
    @request_schema(QuestionSchema)
    @response_schema(QuestionSchema)
    async def post(self):
        theme_id = self.data["theme_id"]
        existing_theme = await self.store.quizzes.get_theme_by_id(id=theme_id)
        if not existing_theme:
            raise HTTPNotFound

        title = self.data["title"]
        existing_question = await self.store.quizzes.get_question_by_title(title=title)
        if existing_question:
            raise HTTPConflict
        answers = self.data["answers"]
        if not check_answers(answers):
            raise HTTPBadRequest

        answers_list = await self.store.quizzes.create_answers_list(answers=answers)
        points = self.data["points"]
        question = await self.store.quizzes.create_question(
            title=title, theme_id=theme_id, points=points, answers=answers_list
        )
        raw_answers = [AnswerSchema().dump(answer) for answer in answers_list]
        return json_response(
            data={
                "id": question.id,
                "theme_id": theme_id,
                "points": question.points,
                "answers": raw_answers,
                "title": title,
            }
        )


class QuestionListView(AuthRequiredMixin, View):
    @querystring_schema(ThemeIdSchema)
    @response_schema(ListQuestionSchema)
    async def get(self):
        theme_id = None
        try:
            theme_id = int(self.request.query["id"])
        except:
            pass
        async with self.database.session.begin() as db_session:
            questions = await self.store.quizzes.list_questions(db_session, theme_id)
        data = {"questions": []}
        for q in questions:
            raw_answers = [AnswerSchema().dump(answer) for answer in q.answers]
            question = {
                "id": q.id,
                "theme_id": q.theme_id,
                "answers": raw_answers,
                "title": q.title,
                "points": q.points
            }
            data["questions"].append(question)
        return json_response(data=data)
