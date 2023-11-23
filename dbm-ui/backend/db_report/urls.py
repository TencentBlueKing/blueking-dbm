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
from django.conf.urls import url

from backend.db_report import views

urlpatterns = [
    url("^meta_check/instance_belong$", views.MetaCheckReportInstanceBelongViewSet.as_view({"get": "list"})),
    url("^checksum_check/report$", views.ChecksumCheckReportViewSet.as_view({"get": "list"})),
    url("^checksum_check/instance$", views.ChecksumInstanceViewSet.as_view({"get": "list"})),
    url("^mysql_check/full_backup$", views.MysqlFullBackupCheckReportViewSet.as_view({"get": "list"})),
    url("^mysql_check/binlog_backup$", views.MysqlBinlogBackupCheckReportViewSet.as_view({"get": "list"})),
    url("^redis_check/full_backup$", views.RedisFullBackupCheckReportViewSet.as_view({"get": "list"})),
    url("^redis_check/binlog_backup$", views.RedisBinlogBackupCheckReportViewSet.as_view({"get": "list"})),
    url("^dbmon/heartbeat$", views.DbmonHeatbeartCheckReportBaseViewSet.as_view({"get": "list"})),
]
