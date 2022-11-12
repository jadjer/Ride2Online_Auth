#  Copyright 2022 Pavel Suprunov
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from fastapi import APIRouter, Depends, Body
from neo4j import AsyncDriver

from app.api.dependencies.authentication import get_current_user_authorizer
from app.api.dependencies.database import get_db_driver
from app.database.repositories.profile_repository import ProfileRepository
from app.models.domain.user import User
from app.models.schemas.profile import ProfileResponse, ProfileUpdate

router = APIRouter()


@router.get("", response_model=ProfileResponse, name="user:get")
async def get_current_user(
        user: User = Depends(get_current_user_authorizer()),
) -> ProfileResponse:
    return ProfileResponse(user=user)


@router.patch("", response_model=ProfileResponse, name="user:update")
async def update_my_profile(
        profile_update: ProfileUpdate = Body(..., embed=True, alias="profile"),
        user: User = Depends(get_current_user_authorizer()),
        driver: AsyncDriver = Depends(get_db_driver),

) -> ProfileResponse:
    profile_repository: ProfileRepository = ProfileRepository()

    with driver.session() as session:
        profile = await profile_repository.update_profile(session, user.username)

    return ProfileResponse(profile=profile)
