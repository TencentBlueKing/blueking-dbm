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
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .bf.views import BFPluginViewSet
from .cluster.views import OpenClusterViewSet
from .monitor.views import MonitorPluginViewSet

routers = DefaultRouter(trailing_slash=True)

routers.register("cluster", OpenClusterViewSet, basename="cluster")
routers.register("monitor", MonitorPluginViewSet, basename="monitor")
routers.register("bf", BFPluginViewSet, basename="bfplugin")


urlpatterns = routers.urls + [
    path("cmdb/", include("backend.db_services.plugin.cmdb.urls")),
    path("bigdata/", include("backend.db_services.plugin.bigdata.urls")),
    path("mysql/", include("backend.db_services.plugin.mysql.urls")),
    path("redis/", include("backend.db_services.plugin.redis.urls")),
    path("sqlserver/", include("backend.db_services.plugin.sqlserver.urls")),
    path("conf/", include("backend.db_services.plugin.configuration.urls")),
    path("db_dirty/", include("backend.db_services.plugin.db_dirty.urls")),
    path("packages/", include("backend.db_services.plugin.db_package.urls")),
    path("dbbase/", include("backend.db_services.plugin.dbbase.urls")),
    path("dbresource/", include("backend.db_services.plugin.dbresource.urls")),
    path("iam/", include("backend.db_services.plugin.iam_app.urls")),
    path("ipchooser/", include("backend.db_services.plugin.ipchooser.urls")),
    path("partition/", include("backend.db_services.plugin.partition.urls")),
    path("taskflow/", include("backend.db_services.plugin.taskflow.urls")),
    path("tickets/", include("backend.db_services.plugin.ticket.urls")),
    path("cluster_entry/", include("backend.db_services.plugin.cluster_entry.urls")),
]
