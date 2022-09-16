import json
from typing import Any, Optional

from aiohttp.web import json_response as aiohttp_json_response
from aiohttp.web_response import Response
from app.store.vk_api.dataclasses import Update, UpdateObject, UpdateMessage


def json_response(data: Any = None, status: str = "ok") -> Response:
    if data is None:
        data = {}
    return aiohttp_json_response(
        data={
            "status": status,
            "data": data,
        }
    )


def error_json_response(
    http_status: int,
    status: str = "error",
    message: Optional[str] = None,
    data: Optional[dict] = None,
):
    if data is None:
        data = {}
    return aiohttp_json_response(
        status=http_status,
        data={
            "status": status,
            "message": str(message),
            "data": data,
        },
    )


def make_update_from_raw(raw_update: dict) -> Update:
    type = raw_update["type"]
    object = raw_update["object"]
    message = object["message"]
    message_id = message["id"]
    text = message["text"]
    peer_id = message["peer_id"]
    from_id = message["from_id"]
    action = message.get("action", None)
    action_type = action["type"] if action else None
    payload_cmd = payload_txt = None
    payload = message.get("payload", None)
    if isinstance(payload, str):
        payload = payload.strip('[]""')
        payload = payload.split()
        if len(payload) == 2:
            payload_txt = payload[1]
        payload_cmd = payload[0]
    update_message = UpdateMessage(id=message_id,
                                   from_id=from_id,
                                   text=text,
                                   peer_id=peer_id,
                                   action_type=action_type,
                                   payload_cmd=payload_cmd,
                                   payload_txt=payload_txt)
    update_object = UpdateObject(message=update_message)
    update = Update(type=type, object=update_object)
    return update


def get_keyboard_json(type: str, **kwargs) -> str:

    def _button(label: str, payload: Optional[str] = None, color: Optional[str] = None) -> dict:
        button = {"action": {"type": "text", "label": label}}
        if payload:
            button["action"]["payload"] = [payload]
        if color:
            button["color"] = color
        return button

    buttons = []
    if type in ["initial", "quiz_ended", "quiz_ended_on_stop"]:
        buttons = [[_button("Старт", payload="START")]]
    elif type in ["preparing", "player_already_added", "not_enough_players", "not_creator_to_run", "new_player_added"]:
        buttons = [[_button("Участвовать", payload="PARTICIPATE")], [_button("Поехали", payload="RUN")]]
    elif type in ["question"]:
        if "question" in kwargs:
            answers = kwargs["question"].answers
            for answer in answers:
                payload = " ".join(["ANSWER", str(answer.is_correct)])
                buttons.append([_button(label=answer.title, payload=payload)])
            buttons.append([_button("Завершить игру", payload="STOP")])
    elif type == "choose_question":
        if "questions" in kwargs:
            questions = kwargs["questions"]     # questions ~ {theme1: {100: q1, 200: q2}, theme2: {100: q3, 200: q4},}
            for theme_name, theme_questions in questions.items():
                line = []
                for points, question in theme_questions.items():
                    text = " ".join([theme_name, str(points)])
                    payload = " ".join(["QUESTION", str(question.id)])
                    line.append(_button(label=text, payload=payload))
                buttons.append(line)
            buttons.append([_button("Завершить игру", payload="STOP")])
    keyboard = {
        "one_time": False,
        "buttons": buttons,
        "inline": False
    }
    if buttons:
        return json.dumps(keyboard)


def check_answers(answers: list) -> bool:
    return sum([a["is_correct"] for a in answers]) == 1 and len(answers) > 1
