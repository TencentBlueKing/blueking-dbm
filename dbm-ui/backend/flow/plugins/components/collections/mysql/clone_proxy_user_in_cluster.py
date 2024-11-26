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

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstanceStatus, MachineType
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.mysql.clone_user import CloneUserService

logger = logging.getLogger("flow")


class CloneProxyUsersInClusterService(CloneUserService):
    """
    场景化处理：集群内克隆proxy的用户白名单，同时给后端mysql对白名单授权，提供proxy替换和添加使用
    理论上某个状态点，集群的所有proxy的授权名单都是同等的。
    所以这里会即时计算running状态的proxy实例作为权限克隆源，保证克隆时集群的权限的最新可用的。
    """

    def _calc_running_status_in_cluster(self, cluster: Cluster):
        """
        计算集群可用的proxy实例，作为权限克隆源
        """
        proxys = cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING)
        if not proxys:
            # 如果在dbm系统找不到running状态的proxy实例，则报异常
            self.log_error(f"no running-status-proxys in cluster[{cluster.immute_domain}]")
            return None, 0
        for proxy in proxys:
            proxy_admin_instance = f"{proxy.machine.ip}{IP_PORT_DIVIDER}{proxy.admin_port}"
            res = DRSApi.proxyrpc(
                {
                    "addresses": [proxy_admin_instance],
                    "cmds": ["select version;"],
                    "force": False,
                    "bk_cloud_id": cluster.bk_cloud_id,
                }
            )
            if not res[0]["error_msg"]:
                self.log_info(f"get running proxy [{proxy_admin_instance}] is source ")
                return proxy.ip_port, proxy.port

        self.log_error(f"no running proxy in cluster [{cluster.immute_domain}] with drs-check")
        return None, 0

    def _execute(self, data, parent_data, callback=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        try:
            cluster = Cluster.objects.get(id=kwargs["cluster_id"])
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(
                cluster_id=kwargs["cluster_id"], bk_biz_id=int(global_data["bk_biz_id"]), message=_("集群不存在")
            )
        temp_proxy, proxy_port = self._calc_running_status_in_cluster(cluster)
        if not temp_proxy:
            return False

        # 执行clone-user接口
        data.get_one_of_inputs("kwargs")["clone_data"] = [
            {
                "source": temp_proxy,
                "target": f"{kwargs['target_proxy_host']}{IP_PORT_DIVIDER}{proxy_port}",
                "machine_type": MachineType.PROXY.value,
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        ]
        return super()._execute(data, parent_data)


class CloneProxyUsersInClusterComponent(Component):
    name = __name__
    code = "clone_proxy_users_in_cluster"
    bound_service = CloneProxyUsersInClusterService
