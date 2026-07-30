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

# HDFS 监控 PromQL 查询模板
# master: 通过 hadoop_namenode_State 指标筛出当前 active NameNode
# 取 5 分钟窗口内最后一次采样值（last_over_time），值为 1 即 active NN
# 返回值维度: (cluster_domain, instance)
MONITOR_QUERY_HDFS_TEMPLATE = {
    "range": 5,
    "master": """max by (cluster_domain, instance) (
        last_over_time(
            bkmonitor:exporter_dbm_hdfs_exporter:hadoop_namenode_State{
                instance_role="hdfs_namenode",%s
            }[5m]
        )
    ) == 1""",
}


class MonitorQueryType(str, StructuredEnum):
    """HDFS 监控查询类型"""

    MASTER = EnumField("master", _("Master(Active NameNode)节点"))
