import enum
import json
from typing import Union, Optional

from app.quiz.models import Question


def _to_json(cmd):
    return json.dumps([cmd.value])


class CmdEnum(enum.Enum):
    START = 0
    RUN = 1
    PARTICIPATE = 2
    QUESTION = 3
    ANSWER = 4
    RESULTS = 9
    STOP = 5


class MessageHelper:
    initial = "Игра пока не начата. Чтобы начать игру, нажмите кнопку 'Старт'"
    restart = "Бот был перезагружен"
    bot_added_to_chat = "Бот был добавлен в чат"
    preparing = "Для участия в игре нажмите кнопку 'Участвовать'\n Когда все будут готовы, нажмите 'Поехали'"
    start_quiz = "Игра началась!"
    wrong_start = "Чтобы начать новую игру, завершите текущюю"
    no_preparing_session = "Игра либо уже начата, либо ещё не начата, дождитесь начала новой"
    no_running_session = "Сейчас нельзя выбирать/отвечать на вопросы, сначала начните игру"
    not_enough_players = "Слишком мало игроков!"
    question_already_answered = "Этот вопрос уже был, выбери другой!"
    no_session_to_stop = "Нет идущих игровых сессий"
    too_many_players = "Слишком много игроков!"
    no_results = "В базе нет результатов для этого чата!"
    no_question_in_db = "В базе не найдено вопросов! Сообщите администратору!"

    @classmethod
    def started(cls, name):
        return f"Игрок {name} нажал 'Старт'! {name}, дождись других игроков, прежде чем продолжить"

    @classmethod
    def new_player_added(cls, name):
        return f"Добавлен игрок {name}"

    @classmethod
    def player_already_added(cls, name):
        return f"Игрок {name} уже добавлен"

    @classmethod
    def choose_question(cls, name):
        return f"{name}, выбирай вопрос!"

    @classmethod
    def question(cls, question):
        return f"Вопрос: {question}"

    @classmethod
    def answered_correct(cls, name, points, curpoints):
        return f"{name} дал правильный ответ! Игрок получает {points} очков, текущая сумма: {curpoints}"

    @classmethod
    def answered_wrong(cls, name, points, curpoints):
        return f"Неверный ответ! {name} теряет {points} очков, текущая сумма: {curpoints}"

    @classmethod
    def quiz_ended(cls, results):
        return f"Игра окончена, результаты: {cls.to_str(results)}"

    @classmethod
    def quiz_ended_on_stop(cls, name, results):
        return f"Игра окончена игроком {name}, результаты: {cls.to_str(results)}"

    @classmethod
    def just_show_results(cls, results):
        return f"Результаты крайней игры: {cls.to_str(results)}"

    @classmethod
    def no_players_left(cls, answer):
        return f"Все игроки ответили неверно, правильный ответ - {answer}"

    @classmethod
    def not_last_answerer(cls, name):
        return f"Выбирать вопрос сейчас может только {name}"

    @classmethod
    def not_creator_to_run(cls, name, creator_name):
        return f"{name}, запустить игру может тот, кто нажал 'Старт' ({creator_name})"

    @classmethod
    def not_creator_to_stop(cls, name, creator_name):
        return f"{name}, преждевременно завершить игру может тот, кто нажал 'Старт' ({creator_name})"

    @classmethod
    def can_not_answer(cls, name):
        return f"{name} уже потратил свою попытку на ответ"

    @classmethod
    def to_str(cls, results_dict: dict):
        results_list = []
        for name, points in results_dict.items():
            results_list.append((name, points))
        results = ". ".join([f"{name}: {points}" for name, points in results_list])
        return results


class KeyboardHelper:
    @classmethod
    def _button(cls, label: str, payload: Union[int, str, None] = None, color: Optional[str] = None) -> dict:
        button = {"action": {"type": "text", "label": label}}
        if payload:
            button["action"]["payload"] = payload
        if color:
            button["color"] = color
        return button

    @classmethod
    def _keyboard(cls, buttons: list[list[dict]]) -> str:
        keyboard = {
            "one_time": False,
            "buttons": buttons,
            "inline": False
        }
        return json.dumps(keyboard)


    @classmethod
    def generate_initial_keyboard(cls):
        buttons = [[cls._button("Старт", payload=_to_json(CmdEnum.START))],
                   [cls._button("Предыдущие результаты", payload=_to_json(CmdEnum.RESULTS))]]
        return cls._keyboard(buttons=buttons)

    @classmethod
    def generate_preparing_keyboard(cls):
        buttons = [[cls._button("Участвовать", payload=_to_json(CmdEnum.PARTICIPATE))],
                   [cls._button("Поехали", payload=_to_json(CmdEnum.RUN))],
                   [cls._button("Завершить игру", payload=_to_json(CmdEnum.STOP)),
                    cls._button("Предыдущие результаты", payload=_to_json(CmdEnum.RESULTS))]]
        return cls._keyboard(buttons=buttons)

    @classmethod
    def generate_questions_keyboard(cls, questions: dict):
        buttons = []
        for theme_name, theme_questions in questions.items():
            line = []
            for points, question in theme_questions.items():
                text = " ".join([theme_name, str(points)])
                payload = json.dumps([CmdEnum.QUESTION.value, question.id])
                line.append(cls._button(label=text, payload=payload))
            buttons.append(line)
        buttons.append([cls._button("Завершить игру", payload=_to_json(CmdEnum.STOP)),
                        cls._button("Текущие результаты", payload=_to_json(CmdEnum.RESULTS))])
        return cls._keyboard(buttons=buttons)

    @classmethod
    def generate_answers_keyboard(cls, question: Question):
        buttons = []
        for answer in question.answers:
            text = answer.title
            payload = json.dumps([CmdEnum.ANSWER.value, answer.is_correct])
            buttons.append([cls._button(label=text, payload=payload)])
        buttons.append([cls._button("Завершить игру", payload=_to_json(CmdEnum.STOP)),
                        cls._button("Текущие результаты", payload=_to_json(CmdEnum.RESULTS))])
        return cls._keyboard(buttons=buttons)
