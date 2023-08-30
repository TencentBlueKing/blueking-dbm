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
from rest_framework.routers import DefaultRouter

from backend.db_monitor.views.grafana import MonitorGrafanaViewSet
from backend.db_monitor.views.policy import MonitorPolicyViewSet
from backend.db_monitor.views.notice_group import MonitorNoticeGroupViewSet

routers = DefaultRouter(trailing_slash=True)

routers.register(r"grafana", MonitorGrafanaViewSet, basename="grafana")
routers.register(r"policy", MonitorPolicyViewSet, basename="policy")
routers.register(r"notice_group", MonitorNoticeGroupViewSet, basename="notice_group")

urlpatterns = routers.urls
