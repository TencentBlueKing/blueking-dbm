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
from django.utils.translation import gettext as _

from backend.flow.consts import HdfsRoleEnum
from backend.flow.engine.bamboo.scene.hdfs.validate.common import (
    check_datanode_ips_belong_to_cluster,
    cluster_datanode_ips,
    get_hdfs_cluster,
    node_ips,
    ticket_error,
)
from backend.flow.engine.validate.base_validate import BaseValidator
from backend.ticket.builders.common import constants


class HdfsShrinkValidator(BaseValidator):
    """
    HDFS 缩容提单校验（规则权威位置）。
    1. 集群必须存在且是 HDFS；
    2. old_nodes.datanode 不能为空；
    3. old_nodes.datanode 里的 IP 都必须是该集群当前的 DataNode（即只支持缩容 DataNode）；
    4. 缩容后至少保留 HDFS_DATANODE_MIN 台 DataNode。
    """

    def __call__(self):
        cluster, cluster_error = get_hdfs_cluster(self.data.get("cluster_id"))
        if cluster_error:
            return [cluster_error]

        dn_nodes = ((self.data.get("old_nodes") or {}).get(HdfsRoleEnum.DataNode.value)) or []
        # 为空时 actuator 侧 data_node_hosts 必填校验才会失败，这里提前拦下；
        # 且归属校验与保留台数校验对空列表都会放过，必须先判空再往下走
        if not dn_nodes:
            return [ticket_error("old_nodes", _("缩容 DataNode 不能为空"))]

        errors = check_datanode_ips_belong_to_cluster(cluster, dn_nodes, "old_nodes")

        # 缩容后至少保留 HDFS_DATANODE_MIN 台 DataNode
        min_count = constants.HDFS_DATANODE_MIN
        remain_ips = cluster_datanode_ips(cluster) - set(node_ips(dn_nodes))
        if len(remain_ips) < min_count:
            errors.append(ticket_error("old_nodes", _("缩容后 DataNode 至少保留 {} 台").format(min_count)))
        return errors or None
