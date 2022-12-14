#  Copyright 2022 Pavel Suprunov
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from typing import Optional
from loguru import logger

from neo4j import Record, AsyncResult
from neo4j.exceptions import ConstraintError

from app.database.repositories.base_repository import BaseRepository
from app.models.domain.user import User, UserInDB


class UserRepository(BaseRepository):
    async def create_user_by_phone(self, phone: str, *, username: str, password: str, **kwargs) -> Optional[UserInDB]:
        user = UserInDB(username=username, phone=phone)
        user.change_password(password)

        query = f"""
            MATCH (phone:Phone)
            WHERE phone.number = "{phone}"
            CREATE (phone)-[:Attached]->(user:User)
            SET user.username = "{user.username}"
            SET user.salt = "{user.salt}"
            SET user.password = "{user.password}"
            SET user.is_blocked = "{user.is_blocked}"
            RETURN id(user) AS user_id
        """

        result: AsyncResult = await self.session.run(query)

        try:
            record: Record | None = await result.single()
        except ConstraintError as exception:
            logger.warning(exception)
            return None

        if not record:
            logger.warning("Query result is empty")
            return None

        user.id = record["user_id"]

        return user

    async def get_user_by_id(self, user_id: int) -> Optional[UserInDB]:
        query = f"""
            MATCH (phone:Phone)-[:Attached]->(user:User)
            WHERE id(user) = {user_id}
            RETURN id(user) AS user_id, user, phone
        """

        result: AsyncResult = await self.session.run(query)
        record: Record | None = await result.single()
        user: UserInDB = self._get_user_from_record(record)

        return user

    async def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        query = f"""
            MATCH (phone:Phone)-[:Attached]->(user:User)
            WHERE user.username = "{username}"
            RETURN id(user) AS user_id, user, phone
        """

        result: AsyncResult = await self.session.run(query)
        record: Record | None = await result.single()
        user: UserInDB = self._get_user_from_record(record)

        return user

    async def get_user_by_phone(self, phone: str) -> Optional[UserInDB]:
        query = f"""
            MATCH (phone:Phone)-[:Attached]->(user:User)
            WHERE phone.number = "{phone}"
            RETURN id(user) AS user_id, user, phone
        """

        result: AsyncResult = await self.session.run(query)
        record: Record | None = await result.single()
        user: UserInDB = self._get_user_from_record(record)

        return user

    async def is_exists(self, username: str) -> bool:
        user: User | None = await self.get_user_by_username(username)
        if user:
            return True

        return False

    async def update_user_by_user_id(
            self,
            user_id: int,
            *,
            username: Optional[str] = None,
            password: Optional[str] = None,
            **kwargs
    ) -> Optional[UserInDB]:
        user = await self.get_user_by_id(user_id)
        if not user:
            return user

        user.username = username or user.username

        if password:
            user.change_password(password)

        query = f"""
            MATCH (user:User)
            WHERE id(user) = {user.id}
            SET user.username = "{user.username}"
            SET user.salt = "{user.salt}"
            SET user.password = "{user.password}"
        """

        await self.session.run(query)

        return await self.get_user_by_id(user.id)

    async def change_user_phone_by_user_id(
            self,
            user_id: int,
            *,
            phone: str,
            **kwargs
    ):
        query = f"""
            MATCH (phone:Phone)-[r:Attached]->(user:User)
            WHERE id(user) = {user_id}
            MATCH (newPhone:Phone)
            WHERE newPhone.number = "{phone}"
            CREATE (newPhone)-[:Attached]->(user)
            DELETE r
        """

        await self.session.run(query)

        return await self.get_user_by_id(user_id)

    @staticmethod
    def _get_user_from_record(record: Record) -> UserInDB | None:
        if not record:
            return None

        user = UserInDB(
            id=record["user_id"],
            phone=record["phone"]["number"],
            username=record["user"]["username"],
            password=record["user"]["password"],
            salt=record["user"]["salt"],
            is_blocked=record["user"]["is_blocked"],
        )

        return user
