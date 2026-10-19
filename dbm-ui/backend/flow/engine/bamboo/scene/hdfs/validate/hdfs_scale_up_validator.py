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

from backend.db_services.dbbase.constants import IpSource
from backend.flow.consts import HdfsRoleEnum
from backend.flow.engine.bamboo.scene.hdfs.validate.common import get_hdfs_cluster, ticket_error
from backend.flow.engine.validate.base_validate import BaseValidator


class HdfsScaleUpValidator(BaseValidator):
    """
    HDFS 扩容提单校验。
    集群必须是 HDFS。手工录入时 nodes.datanode 不能为空；资源池此时还没有 IP，数量仍由 serializer 校验。
    """

    def __call__(self):
        errors = []
        _cluster, cluster_error = get_hdfs_cluster(self.data.get("cluster_id"))
        if cluster_error:
            errors.append(cluster_error)

        if self.data.get("ip_source") == IpSource.RESOURCE_POOL:
            return errors or None

        dn_nodes = (self.data.get("nodes") or {}).get(HdfsRoleEnum.DataNode.value) or []
        if not dn_nodes:
            errors.append(ticket_error("nodes", _("扩容 DataNode 不能为空")))
        return errors or None
