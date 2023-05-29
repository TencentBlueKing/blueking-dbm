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
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from backend.homepage.views import HomeView, LoginSuccessView, LogOutView, VersionView

schema_view = get_schema_view(
    openapi.Info(
        title="BK-DBM API",
        default_version="v1",
    ),
    public=True,
    permission_classes=(permissions.IsAdminUser,),
)


api_patterns = [
    path("ipchooser/", include("backend.db_services.ipchooser.urls")),
    path("infras/", include("backend.db_services.infras.urls")),
    path("taskflow/", include("backend.db_services.taskflow.urls")),
    path("cmdb/", include("backend.db_services.cmdb.urls")),
    path("users/", include("backend.db_services.user.urls")),
    path("group/", include("backend.db_services.group.urls")),
    path("tickets/", include("backend.ticket.urls")),
    path("configs/", include("backend.db_services.dbconfig.urls")),
    path("dbresource/", include("backend.db_services.dbresource.urls")),
    path("partition/", include("backend.db_services.partition.urls")),
    path("packages/", include("backend.db_package.urls")),
    path("version/", include("backend.db_services.version.urls")),
    path("mysql/", include("backend.db_services.mysql.urls")),
    path("redis/", include("backend.db_services.redis.urls")),
    path("bigdata/", include("backend.db_services.bigdata.urls")),
    path("conf/", include("backend.configuration.urls")),
    path("v1/flow/", include("backend.flow.urls")),
    path("core/", include("backend.core.urls")),
    path("iam/", include("backend.iam_app.urls")),
    path("proxypass/", include("backend.db_proxy.urls")),
    path("monitor/", include("backend.db_monitor.urls")),
    path("event/", include("backend.db_event.urls")),
    path("redisdts/", include("backend.redis_dts.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("account/", include("blueapps.account.urls")),
    path("apis/", include(api_patterns)),
    path("db_meta/", include("backend.db_meta.urls")),
    # grafana访问地址, 需要和grafana前缀保持一致
    path("grafana/", include("backend.bk_dataview.grafana.urls")),
    # 版本日志
    path("version_log/", include("backend.version_log.urls")),
]

# TODO 正式环境屏蔽swagger访问路径，目前开发测试只使用了 prod
# if settings.ENVIRONMENT not in ["production", "prod"]:
if getattr(settings, "ENVIRONMENT", "") not in []:
    urlpatterns.append(path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"))
    urlpatterns.append(path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"))

vue_patterns = [
    path("login_success.html", LoginSuccessView.as_view()),
    path("logout/", LogOutView.as_view()),
    path("version/", VersionView.as_view()),
    re_path("", HomeView.as_view()),
]
urlpatterns += vue_patterns
