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

from django.utils.translation import gettext_lazy as _

from blue_krill.data_types.enum import EnumField, StructuredEnum

MONITOR_QUERY_DORIS_TEMPLATE = {
    "range": 5,
    "master": """max by (cluster_domain, instance) (
        bkmonitor:pushgateway_dbm_doris_bkpull:node_info{type="is_master",%s})""",
    "remote_used": """sum by (cluster_domain)(
        bkmonitor:pushgateway_dbm_doris_bkpull:doris_be_disks_remote_used_capacity{%s})""",
}


class MonitorQueryType(str, StructuredEnum):
    """
    监控查询类型
    """

    MASTER = EnumField("master", _("Master节点"))
    REMOTE_USED = EnumField("remote_used", _("远程存储使用量"))
