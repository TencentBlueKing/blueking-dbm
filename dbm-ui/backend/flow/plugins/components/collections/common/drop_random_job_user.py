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
from backend.db_meta.enums import ClusterType, TenDBClusterSpiderRole
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.get_mysql_sys_user import generate_mysql_tmp_user
from backend.flow.utils.mysql.mysql_version_parse import mysql_version_parse
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


# 定义控制节点的跳过行为，相关单据不需要执行具体回收单据内容，比如集群下架单据
skip_list = [
    TicketType.MYSQL_HA_DESTROY.value,
    TicketType.MYSQL_SINGLE_DESTROY.value,
    TicketType.TENDBCLUSTER_DESTROY.value,
    TicketType.TENDBCLUSTER_TEMPORARY_DESTROY.value,
    TicketType.TENDBCLUSTER_SPIDER_MNT_DESTROY.value,
    TicketType.TENDBCLUSTER_SPIDER_REDUCE_NODES.value,
    TicketType.TENDBCLUSTER_SPIDER_MNT_DESTROY.value,
]


class DropTempUserForClusterService(BaseService):
    """
    为单据删除job的临时本地账号，操作目标实例
    单据是以集群维度来删除
    """

    @staticmethod
    def _get_instance_for_cluster(cluster: Cluster) -> list:
        """
        根据cluster对象获取所有的cluster需要实例信息
        """
        objs = [{"ip_port": i.ip_port, "is_tdbctl": False} for i in list(cluster.storageinstance_set.all())]

        if cluster.cluster_type == ClusterType.TenDBCluster:
            # 如果是TenDB cluster集群，获取所有spider实例
            objs += [{"ip_port": i.ip_port, "is_tdbctl": False} for i in list(cluster.proxyinstance_set.all())]

            # 如果是tenDB cluster 集群类型，需要获取中控实例
            for spider in cluster.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
            ):

                objs.append({"ip_port": f"{spider.machine.ip}{IP_PORT_DIVIDER}{spider.admin_port}", "is_tdbctl": True})
        return objs

    def drop_jor_user(self, cluster: Cluster, root_id: str):
        """
        集群维度删除job的临时用户
        """
        # 拼接临时用户的名称
        user = generate_mysql_tmp_user(root_id)

        try:
            # 删除localhost和 local_ip用户
            for instance in self._get_instance_for_cluster(cluster=cluster):
                cmd = []
                if instance["is_tdbctl"]:
                    cmd.append("set tc_admin = 0;")
                self.log_info(f"the instance version is {instance.version}")
                if mysql_version_parse(instance.version) > mysql_version_parse("5.7"):
                    cmd += [
                        f"drop user if exists `{user}`@`localhost`;",
                        f"drop user if exists `{user}`@`{instance['ip_port'].split(':')[0]}`;",
                    ]
                else:
                    cmd += [
                        f"drop user `{user}`@`localhost`;",
                        f"drop user `{user}`@`{instance['ip_port'].split(':')[0]}`;",
                    ]

                resp = DRSApi.rpc(
                    {
                        "addresses": [instance["ip_port"]],
                        "cmds": cmd,
                        "force": False,
                        "bk_cloud_id": cluster.bk_cloud_id,
                    }
                )
                for info in resp:
                    if info["error_msg"]:
                        self.log_error(
                            f"The result [drop user if exists `{user}`] in {info['address']}"
                            f"is [{info['error_msg']}]"
                        )
                    else:
                        self.log_info(f"The result [drop user if exists `{user}`] in {info['address']} is [success]")

        except Exception as e:  # pylint: disable=broad-except
            self.log_error(f"drop user error in cluster [{cluster.name}]: {e}")
            return False

        self.log_info(f"drop user finish in cluster [{cluster.name}]")
        return True

    def _execute(self, data, parent_data, callback=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        for cluster_id in kwargs["cluster_ids"]:
            # 获取每个cluster_id对应的对象
            try:
                cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=global_data["bk_biz_id"])
            except Cluster.DoesNotExist:
                raise ClusterNotExistException(
                    cluster_id=cluster_id, bk_biz_id=global_data["bk_biz_id"], message=_("集群不存在")
                )
            self.drop_jor_user(cluster=cluster, root_id=global_data["job_root_id"])

        return True


class DropTempUserForClusterComponent(Component):
    name = __name__
    code = "drop_job_temp_user"
    bound_service = DropTempUserForClusterService
