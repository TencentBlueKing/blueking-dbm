"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import json
from dataclasses import dataclass

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import NormalTenDBFlowException
from backend.flow.plugins.components.collections.common.base_service import BaseService


@dataclass
class CheckTDBCTlSecondaryHealthKwarg:
    cluster_id: int


class CheckTDBCTlSecondaryHealthService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        """
        用rds校验中控从节点监控状态
        """
        kwargs = data.get_one_of_inputs("kwargs")

        # 获取cluster对象，包括中控实例、 spider端口等
        cluster = Cluster.objects.get(id=kwargs["cluster_id"])
        cluster_primary = cluster.tendbcluster_ctl_primary_address()

        res = DRSApi.rpc(
            {
                "addresses": [cluster_primary],
                "cmds": ["select * from information_schema.tdbctl_nodes where CLUSTER_ROLE = 'Secondary';"],
                "force": False,
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            raise NormalTenDBFlowException(message=_(f"exec tdbctl_nodes status failed: {res[0]['error_msg']}"))

        if len(res[0]["cmd_results"][0]["table_data"]) == 0:
            # 表示命令返回结果为空，则认为是同步异常
            self.log_error("information_schema.tdbctl_nodes is null where CLUSTER_ROLE = Secondary, skip")
            return True

        is_error = False
        for node in res[0]["cmd_results"][0]["table_data"]:
            if node["STATUS"] != "Online":
                self.log_error(f"check node error: {node['address']} is abnormal, the status is {node['STATUS']} ")
                continue

            replication_info = json.loads(node["REPLICATION_INFO"])
            if f"{replication_info['Master_Host']}:{replication_info['Master_Port']}" != cluster_primary:
                # 表示同步源，和当前集群的primary不一致，则认为是同步异常
                self.log_error(
                    f"check node error: {node['address']} is abnormal, "
                    f"Master_Host: {replication_info['Master_Host']},"
                    f"Master_Port: {replication_info['Master_Port']},"
                    f"current_primary: {cluster_primary}"
                )
                continue

            if replication_info["Slave_IO_Running"] != "Yes" or replication_info["Slave_SQL_Running"] != "Yes":
                self.log_error(
                    f"check node error: {node['address']} is abnormal, Slave_IO_Running: "
                    f"{node['Slave_IO_Running']}, "
                    f"Slave_SQL_Running: {node['Slave_SQL_Running']}"
                )
                continue

        if is_error:
            return False

        return True


class CheckTDBCTlSecondaryHealthComponent(Component):
    name = __name__
    code = "tendb_cluster_check_tdbctl_secondary_health"
    bound_service = CheckTDBCTlSecondaryHealthService
    kwargs = CheckTDBCTlSecondaryHealthKwarg
