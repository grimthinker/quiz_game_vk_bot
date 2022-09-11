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
        update_message = UpdateMessage(id=message_id,
                                       from_id=from_id,
                                       text=text,
                                       peer_id=peer_id,
                                       action_type=action_type)
        update_object = UpdateObject(message=update_message)
        update = Update(type=type, object=update_object)
        return update


def get_keyboard_json(type: str) -> str:
    def _button(label: str) -> dict:
        return {"action": {"type": "text", "label": label}}

    buttons = [[]]
    if type == "initial":
        buttons = [[_button("Старт")]]
    elif type == "preparing":
        buttons = [[_button("Участвовать")], [_button("Поехали")]]
    keyboard = {
        "one_time": False,
        "buttons": buttons,
        "inline": False
    }
    if buttons != [[]]:
        return json.dumps(keyboard)


def check_answers(answers: list) -> bool:
    return sum([a["is_correct"] for a in answers]) == 1 and len(answers) > 1
