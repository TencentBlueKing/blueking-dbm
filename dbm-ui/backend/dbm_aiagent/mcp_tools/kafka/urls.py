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

from backend.dbm_aiagent.mcp_tools.kafka.views.kafka_bill_mcp import KafkaBillMcpToolsViewSet
from backend.dbm_aiagent.mcp_tools.kafka.views.query_meta import KafkaQueryMetaMcpToolsViewSet

routers = DefaultRouter(trailing_slash=True)

# 与 元数据相关的 query
routers.register(r"", KafkaQueryMetaMcpToolsViewSet, basename="mcp-kafka-query-meta")
# 与 dbm 交互 创建单据类的 操作
routers.register(r"", KafkaBillMcpToolsViewSet, basename="mcp-kafka-bill")

urlpatterns = routers.urls
