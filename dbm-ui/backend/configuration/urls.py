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

from backend.configuration.views.dba import DBAdminViewSet
from backend.configuration.views.function_controller import FunctionControllerViewSet
from backend.configuration.views.ip_whitelist import IPWhitelistViewSet
from backend.configuration.views.password_policy import PasswordPolicyViewSet
from backend.configuration.views.profile import ProfileViewSet
from backend.configuration.views.system import SystemSettingsViewSet

routers = DefaultRouter(trailing_slash=True)

routers.register(r"system_settings", SystemSettingsViewSet, basename="system_settings")
routers.register(r"db_admin", DBAdminViewSet, basename="dba_settings")
routers.register(r"profile", ProfileViewSet, basename="profile")
routers.register(r"password_policy", PasswordPolicyViewSet, basename="password_policy")
routers.register(r"ip_whitelist", IPWhitelistViewSet, basename="ip_whitelist")
routers.register(r"function_controller", FunctionControllerViewSet, basename="function_controller")

urlpatterns = routers.urls
