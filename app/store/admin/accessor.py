import typing
import os
import yaml

from hashlib import sha256
from sqlalchemy import select, delete

from app.admin.models import Admin, AdminModel
from app.base.base_accessor import BaseAccessor

if typing.TYPE_CHECKING:
    from app.web.app import Application


class AdminAccessor(BaseAccessor):
    async def connect(self, app: "Application"):
        await self.delete_admin(email=self.app.config.admin.email)
        await self.create_admin(
            email=app.config.admin.email, password=app.config.admin.password
        )

    async def get_by_email(self, email: str) -> typing.Optional[Admin]:
        async with self.app.database.session() as session:
            async with session.begin():
                stmt = select(AdminModel).where(AdminModel.email == email)
                result = await session.execute(stmt)
                curr = result.scalars()
                for admin in curr:
                    return Admin(admin.id, admin.email, admin.password)

    async def create_admin(self, email: str, password: str) -> Admin:
        async with self.app.database.session() as session:
            async with session.begin():
                password = sha256(password.encode()).hexdigest()
                admin = AdminModel(email=email, password=password)
                session.add(admin)

    async def delete_admin(self, email: str) -> Admin:
        async with self.app.database.session() as session:
            async with session.begin():
                stmt = delete(AdminModel).where(AdminModel.email == email)
                await session.execute(stmt)
