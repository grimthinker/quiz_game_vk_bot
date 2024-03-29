from dataclasses import dataclass
from hashlib import sha256
from typing import Optional
from app.store.database.sqlalchemy_base import db
from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Text,
)


@dataclass
class Admin:
    id: int
    email: str
    password: Optional[str] = None

    def is_password_valid(self, password: str):
        return self.password == sha256(password.encode()).hexdigest()

    @classmethod
    def from_session(cls, session: Optional[dict]) -> Optional["Admin"]:
        return cls(id=session["admin"]["id"], email=session["admin"]["email"])


class AdminModel(db):
    __tablename__ = "admins"
    id = Column(BigInteger, primary_key=True)
    email = Column(String(60), nullable=False)
    password = Column(Text, nullable=False)