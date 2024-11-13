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
import logging

from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.mysql.mysql_delete_clear_db import (
    MysqlDeleteClearDBDetailSerializer,
    MysqlDeleteClearDBFlowBuilder,
    MysqlDeleteClearDBFlowParamBuilder,
)
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class TendbClusterDeleteClearDBDetailSerializer(MysqlDeleteClearDBDetailSerializer):
    pass


class TendbClusterDeleteClearDBFlowParamBuilder(MysqlDeleteClearDBFlowParamBuilder):
    controller = SpiderController.spider_sql_import_scene


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_DELETE_CLEAR_DB, is_sensitive=True)
class TendbClusterDeleteClearDBFlowBuilder(BaseTendbTicketFlowBuilder, MysqlDeleteClearDBFlowBuilder):
    serializer = TendbClusterDeleteClearDBDetailSerializer
    inner_flow_builder = TendbClusterDeleteClearDBFlowParamBuilder
    editable = False
