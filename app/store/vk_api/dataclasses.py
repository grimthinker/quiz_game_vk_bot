from dataclasses import dataclass
from typing import Optional


@dataclass
class UpdateMessage:
    from_id: int
    text: str
    id: int
    peer_id: int
    action_type: Optional[str]
    payload_cmd: Optional[str]
    payload_txt: Optional[str]


@dataclass
class UpdateObject:
    message: UpdateMessage


@dataclass
class Update:
    type: str
    object: UpdateObject

