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

from .tendbha.views import DBHAViewSet
from .tendbsingle.views import DBSingleViewSet
from .views import ListResourceViewSet, ResourceTreeViewSet

router = DefaultRouter(trailing_slash=True)

router.register(r"tendbha_resources", DBHAViewSet, basename="tendbha_resource")
router.register(r"tendbsingle_resources", DBSingleViewSet, basename="tendbsingle_resource")

urlpatterns = [
    # 提供资源(集群)通用属性的查询, 如集群名, 集群创建者等
    path("resources/", ListResourceViewSet.as_view({"get": "list"})),
    path("resource_tree/", ResourceTreeViewSet.as_view({"get": "get_resource_tree"})),
]

urlpatterns += router.urls
