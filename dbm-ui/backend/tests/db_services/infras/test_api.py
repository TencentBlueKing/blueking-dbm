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

from backend.db_services.infras.views import HostSpecViewSet, LogicalCityViewSet

pytestmark = pytest.mark.django_db

factory = APIRequestFactory()


def test_list_cities(bk_user, create_city):
    request = factory.get(
        "/apis/infras/cities/",
    )
    force_authenticate(request, user=bk_user)
    view = LogicalCityViewSet.as_view({"get": "list_cities"})
    response = view(request)
    data = response.data
    assert len(data) == 2


def test_list_host_specs(bk_user, create_city):
    request = factory.get(
        "/apis/infras/cities/sh/host_specs/",
    )
    force_authenticate(request, user=bk_user)
    view = HostSpecViewSet.as_view({"get": "list_host_specs"})
    response = view(request)
    data = response.data
    assert len(data) == 6
    assert data[0]["spec"] == "SA2.SMALL4"
