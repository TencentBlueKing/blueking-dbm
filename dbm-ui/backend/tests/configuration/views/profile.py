# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from backend.configuration.models import Profile
from backend.configuration.views.profile import ProfileViewSet
from backend.ticket.constants import TicketType

pytestmark = pytest.mark.django_db

factory = APIRequestFactory()


class TestProfileViewSet:
    def test_get_profile(self, profile, bk_admin):
        request = factory.get("/apis/conf/profile/get_profile/")
        force_authenticate(request, user=bk_admin)
        data = ProfileViewSet.as_view({"get": "get_profile"})(request).data
        assert data["username"] == bk_admin.username
        assert data["profile"] == [
            {"label": "biz", "values": ["biz-1", "biz-2"]},
            {"label": "ticket_type", "values": [TicketType.MYSQL_SINGLE_APPLY, TicketType.MYSQL_HA_APPLY]},
        ]

    def test_upsert_profile(self, bk_admin):
        request = factory.post(
            "/apis/conf/profile/upsert_profile/", {"label": "ticket_type", "values": [TicketType.MYSQL_SINGLE_APPLY]}
        )
        force_authenticate(request, user=bk_admin)
        ProfileViewSet.as_view({"post": "upsert_profile"})(request)
        assert Profile.objects.filter(username=bk_admin.username).exists()
