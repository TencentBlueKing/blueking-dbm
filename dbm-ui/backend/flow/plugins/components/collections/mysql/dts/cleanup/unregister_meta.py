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

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.db_meta.api.cluster.mysqldts import decommission
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class MysqlDtsUnregisterClusterMetaService(BaseService):
    """下线 MySQL DTS 集群元数据。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        target_hosts = kwargs.get("target_hosts")
        if target_hosts:
            host_dicts = [{"ip": h["ip"], "bk_cloud_id": h["bk_cloud_id"]} for h in target_hosts]
        else:
            host_dicts = None

        decommission(
            dts_cluster_id=kwargs["dts_cluster_id"],
            recycle_hosts=kwargs.get("recycle_hosts", True),
            target_hosts=host_dicts,
            updater=kwargs.get("creator", ""),
        )
        self.log_info(_("MySQL DTS 集群元数据已下线: id={}").format(kwargs["dts_cluster_id"]))
        return True


class MysqlDtsUnregisterClusterMetaComponent(Component):
    name = __name__
    code = "mysql_dts_unregister_cluster_meta"
    bound_service = MysqlDtsUnregisterClusterMetaService
