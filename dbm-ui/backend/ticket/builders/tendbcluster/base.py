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

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterTenDBClusterStatusFlag
from backend.db_meta.models import Cluster
from backend.ticket.builders import TicketFlowBuilder
from backend.ticket.builders.common.base import MySQLTicketFlowBuilderPatchMixin, fetch_cluster_ids
from backend.ticket.builders.mysql.base import (
    MySQLBaseOperateDetailSerializer,
    MySQLBaseOperateResourceParamBuilder,
    MySQLClustersTakeDownDetailsSerializer,
)


class BaseTendbTicketFlowBuilder(MySQLTicketFlowBuilderPatchMixin, TicketFlowBuilder):
    group = DBType.TenDBCluster.value


class TendbBaseOperateDetailSerializer(MySQLBaseOperateDetailSerializer):
    """
    tendbcluster操作的基类，主要功能:
    1. 屏蔽序列化的to_representation
    2. 存放tendbcluster操作的各种校验逻辑
    """

    #  实例不可用时，还能正常提单类型的白名单
    SPIDER_UNAVAILABLE_WHITELIST = []
    REMOTE_MASTER_UNAVAILABLE_WHITELIST = []
    REMOTE_SLAVE_UNAVAILABLE_WHITELIST = []
    # 集群的flag状态与白名单的映射表
    unavailable_whitelist__status_flag = {
        ClusterTenDBClusterStatusFlag.SpiderUnavailable: SPIDER_UNAVAILABLE_WHITELIST,
        ClusterTenDBClusterStatusFlag.RemoteMasterUnavailable: REMOTE_MASTER_UNAVAILABLE_WHITELIST,
        ClusterTenDBClusterStatusFlag.RemoteSlaveUnavailable: REMOTE_SLAVE_UNAVAILABLE_WHITELIST,
    }


class TendbClustersTakeDownDetailsSerializer(MySQLClustersTakeDownDetailsSerializer):
    is_only_delete_slave_domain = serializers.BooleanField(help_text=_("是否只禁用只读集群"), required=False, default=False)
    is_only_add_slave_domain = serializers.BooleanField(help_text=_("是否只启用只读集群"), required=False, default=False)


class TendbBaseOperateResourceParamBuilder(MySQLBaseOperateResourceParamBuilder):
    pass
