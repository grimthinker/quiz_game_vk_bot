from aiohttp.web import HTTPForbidden, HTTPUnauthorized
from aiohttp_apispec import request_schema, json_schema, response_schema, docs
from aiohttp_session import new_session, get_session
from hashlib import sha256

from app.admin.schemes import AdminSchema, AdminLoginSchema
from app.web.app import View
from app.web.utils import json_response
from app.web.mixins import AuthRequiredMixin


class AdminLoginView(View):
    @docs(tags=["admin"], summary="Login admin", description="Add new user to database")
    @request_schema(AdminSchema)
    @response_schema(AdminSchema, 200)
    async def post(self):
        email = self.data["email"]
        existed_admin = await self.store.admins.get_by_email(email)
        if not existed_admin:
            raise HTTPForbidden(reason="no admin with that email")

        password = self.data["password"]
        if not existed_admin.is_password_valid(password):
            raise HTTPForbidden(reason="wrong password")

        raw_admin = AdminSchema().dump(existed_admin)
        session = await new_session(request=self.request)
        session["admin"] = raw_admin
        return json_response(data=raw_admin)


class AdminCurrentView(AuthRequiredMixin, View):
    @response_schema(AdminSchema)
    async def get(self):
        return json_response(AdminSchema().dump(self.request.admin))
