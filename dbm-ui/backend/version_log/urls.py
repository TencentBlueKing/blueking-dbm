# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community
Edition) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.conf.urls import url

from backend.version_log import views

app_name = "version_log"

urlpatterns = (
    # 获取版本日志列表
    url(r"^version_logs_list/$", views.version_logs_list, name="version_logs_list"),
    # 获取版本日志详情
    url(r"^version_log_detail/", views.get_version_log_detail, name="version_log_detail"),
    # 查询当前用户是否看过最新版本日志
    url(r"^has_user_read_latest/", views.has_user_read_latest, name="has_user_read_latest"),
)
