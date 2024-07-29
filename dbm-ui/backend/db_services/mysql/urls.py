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
from django.urls import include, path, re_path

from backend.db_services.mysql.sqlparse.views import parse_sql

urlpatterns = [
    path("bizs/<int:bk_biz_id>/", include("backend.db_services.mysql.resources.urls")),
    path("bizs/<int:bk_biz_id>/", include("backend.db_services.mysql.remote_service.urls")),
    path("bizs/<int:bk_biz_id>/", include("backend.db_services.mysql.permission.urls")),
    path("bizs/<int:bk_biz_id>/", include("backend.db_services.mysql.sql_import.urls")),
    path("bizs/<int:bk_biz_id>/", include("backend.db_services.mysql.cluster.urls")),
    path("bizs/<int:bk_biz_id>/", include("backend.db_services.mysql.instance.urls")),
    path("bizs/<int:bk_biz_id>/", include("backend.db_services.mysql.fixpoint_rollback.urls")),
    path("bizs/<int:bk_biz_id>/", include("backend.db_services.mysql.open_area.urls")),
    path("bizs/<int:bk_biz_id>/", include("backend.db_services.mysql.dumper.urls")),
    path("", include("backend.db_services.mysql.toolbox.urls")),
    re_path("^parse_sql/?$", parse_sql, name="parse_sql"),
]
