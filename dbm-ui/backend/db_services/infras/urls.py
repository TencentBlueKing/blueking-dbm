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
from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

urlpatterns = [
    path("cities/", views.LogicalCityViewSet.as_view({"get": "list_cities"})),
    # TODO 机器类型目前与城市无关，待前端调整后删除
    path("cities/host_specs/", views.HostSpecViewSet.as_view({"get": "list_host_specs"})),
    path("cities/cap_specs/", views.CapSpecViewSet.as_view({"post": "list_cap_specs"})),
]

routers = DefaultRouter(trailing_slash=True)

routers.register("cities", views.LogicalCityViewSet, basename="logical_city")
routers.register("specs", views.HostSpecViewSet, basename="specs")
routers.register("dbtype", views.DBTypeViewSet, basename="dbtype")

urlpatterns.extend(routers.urls)
