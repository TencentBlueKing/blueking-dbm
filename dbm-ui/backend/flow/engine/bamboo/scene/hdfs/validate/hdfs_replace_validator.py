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
    get_hdfs_cluster,
    ticket_error,
)
from backend.flow.engine.validate.base_validate import BaseValidator


class HdfsReplaceValidator(BaseValidator):
    """
    HDFS 替换提单校验。
    集群必须是 HDFS，且只允许替换 datanode。old_nodes.datanode 不能为空，
    其中的 IP 必须属于该集群 DataNode。新旧数量仍由 BigDataReplaceDetailSerializer 校验。
    """

    def __call__(self):
        errors = []
        cluster, cluster_error = get_hdfs_cluster(self.data.get("cluster_id"))
        if cluster_error:
            errors.append(cluster_error)

        old_nodes = self.data.get("old_nodes") or {}
        role = HdfsRoleEnum.DataNode.value
        if set(old_nodes.keys()) != {role}:
            errors.append(ticket_error("old_nodes", _("HDFS 替换只支持 datanode 角色")))

        dn_nodes = old_nodes.get(role) or []
        # 为空时要等单据审批后才由 init_replace_data 抛 ReplaceMachineNullException，这里提前拦下
        if not dn_nodes:
            errors.append(ticket_error("old_nodes", _("替换 DataNode 不能为空")))
        elif cluster:
            errors.extend(check_datanode_ips_belong_to_cluster(cluster, dn_nodes, "old_nodes"))
        return errors or None
