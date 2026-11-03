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
from backend.db_meta.api.cluster_state.fields.common import CapacityField, DBHADisabledField, PortraitReportField
from backend.db_meta.api.cluster_state.registry import register_state_schema
from backend.db_meta.api.cluster_state.schemas.common import CommonClusterStateSchema
from backend.db_meta.enums import ClusterType


@register_state_schema(cluster_types=[ClusterType.TenDBSingle.value])
class TenDBSingleStateSchema(CommonClusterStateSchema):
    """TenDBSingle 集群状态"""


class MySQLHAStateSchema(CommonClusterStateSchema):
    """TenDBHA / TenDBCluster 共有的状态字段，不注册"""

    dbha_disabled = DBHADisabledField()
    capacity = CapacityField()
    portrait_report = PortraitReportField()


@register_state_schema(cluster_types=[ClusterType.TenDBHA.value])
class TenDBHAStateSchema(MySQLHAStateSchema):
    """TenDBHA 集群状态"""


@register_state_schema(cluster_types=[ClusterType.TenDBCluster.value])
class TenDBClusterStateSchema(MySQLHAStateSchema):
    """TenDBCluster 集群状态"""
