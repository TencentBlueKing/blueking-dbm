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

urlpatterns = [
    path("bizs/<int:bk_biz_id>/", include("backend.db_services.bigdata.resources.urls")),
    path("bizs/<int:bk_biz_id>/es/", include("backend.db_services.bigdata.es.urls")),
    path("bizs/<int:bk_biz_id>/hdfs/", include("backend.db_services.bigdata.hdfs.urls")),
    path("bizs/<int:bk_biz_id>/kafka/", include("backend.db_services.bigdata.kafka.urls")),
    path("bizs/<int:bk_biz_id>/pulsar/", include("backend.db_services.bigdata.pulsar.urls")),
    path("bizs/<int:bk_biz_id>/influxdb/", include("backend.db_services.bigdata.influxdb.urls")),
    path("bizs/<int:bk_biz_id>/riak/", include("backend.db_services.bigdata.riak.urls")),
]
