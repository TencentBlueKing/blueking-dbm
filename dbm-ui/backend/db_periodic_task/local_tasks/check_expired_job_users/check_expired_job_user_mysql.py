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

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.flow.consts import DBM_MYSQL_JOB_TMP_USER_PREFIX
from backend.ticket.constants import TicketFlowStatus
from backend.ticket.models import Flow

logger = logging.getLogger("root")


class CheckExpiredJobUserForMysql(object):
    """
    构建检查mysql集群是否存在已过期的随机job用户
    如何判断是随机job用户，而且已过期：
    1：目前DBM系统所有的随机job用户名称前缀是一致的，可利用前缀过滤出实例存在job账号
    2：在job账号获取到流程flow的root_id，判断root_id对应的flow是否已中断或者注销的状态，如果是，则账号定义为已过期
    """

    def __init__(self, mysql_cluster_type: ClusterType):
        if mysql_cluster_type not in [ClusterType.TenDBHA, ClusterType.TenDBCluster, ClusterType.TenDBSingle]:
            raise Exception(
                f"the cluster_type does not belong to the mysql cluster type range: cluster_type:[{mysql_cluster_type}]"
            )
        self.mysql_cluster_type = mysql_cluster_type
        self.clusters = Cluster.objects.filter(cluster_type=mysql_cluster_type)

    @staticmethod
    def _get_storage_instance_for_cluster(cluster: Cluster):
        """
        获取集群mysql实例
        """
        proxy_instances = []
        if cluster.cluster_type == ClusterType.TenDBCluster:
            # 如果是TenDB Cluster集群，spider和中控节点需要检查
            proxy_instances = [p.ip_port for p in list(cluster.proxyinstance_set.all())]
            proxy_instances += [
                f"{p.machine.ip}{IP_PORT_DIVIDER}{p.admin_port}"
                for p in list(
                    cluster.proxyinstance_set.filter(
                        tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
                    )
                )
            ]

        storage_instances = [p.ip_port for p in list(cluster.storageinstance_set.all())]

        return storage_instances + proxy_instances

    def _get_job_users_for_cluster(self, cluster: Cluster) -> list:
        """
        遍历mysql集群列表，获取mysql实例中存在job随机账号
        """
        instances = self._get_storage_instance_for_cluster(cluster=cluster)
        get_job_users_sql = f"select user,host from mysql.user where user like '{DBM_MYSQL_JOB_TMP_USER_PREFIX}%' "

        resp = DRSApi.rpc(
            {
                "addresses": instances,
                "cmds": ["set tc_admin = 0;", get_job_users_sql],
                "force": True,
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )

        for info in resp:
            if info["error_msg"]:
                logger.error(f"get job_users failed in cluster [{cluster.name}] : [{info['error_msg']}]")

        return resp

    @staticmethod
    def _drop_expired_job_user_for_instance(cluster: Cluster, user_info: dict, address: str):
        """
        删除已过期的账号
        统一用drop user 命令删除临时账号
        如果处理drop异常，不捕捉，正常返回，等待下一个周期处理
        """

        DRSApi.rpc(
            {
                "addresses": [address],
                "cmds": [
                    "set session sql_log_bin = 0;",
                    "set tc_admin = 0;",
                    f"drop user `{user_info['user']}`@`{user_info['host']}`;",
                    "set session sql_log_bin = 1;",
                ],
                "force": True,
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )
        logger.info(f"drop user [{user_info['user']}@{user_info['host']} in instance : [{address}]")

        return

    def check_job_user_is_expired(self, cluster: Cluster):
        """
        判断账号是否过期
        """
        resp = self._get_job_users_for_cluster(cluster=cluster)
        for info in resp:
            if info["cmd_results"] is None:
                continue

            for cmd_result in info["cmd_results"]:
                if not cmd_result.get("table_data", None):
                    # 如果是空列表，则表示实例上没有job_user, 正常跳过处理。
                    continue
                else:
                    # 如果不是空，则逐个判断随机账号情况,判断已过期，则删除
                    for user_info in cmd_result.get("table_data"):
                        flow_rood_id = user_info["user"].replace(DBM_MYSQL_JOB_TMP_USER_PREFIX, "")
                        if Flow.objects.filter(
                            flow_obj_id=flow_rood_id,
                            status__in=[TicketFlowStatus.TERMINATED, TicketFlowStatus.REVOKED],
                        ).exists() and user_info["host"] in ["localhost", info["address"].split(":")[0]]:
                            """
                            如果对应的job_id存在，且状态已经是终止或者撤销状态，则认为单据已经停止，可删除临时账号
                            如果host不是localhost和local_ip, 则认为这不是dbm产生的临时账号
                            """
                            self._drop_expired_job_user_for_instance(
                                cluster=cluster, user_info=user_info, address=info["address"]
                            )
                        else:
                            # 匹配不到，则认为running状态，不作处理
                            pass

    def do_check(self):
        """
        遍历检查
        """
        for cluster in self.clusters:
            self.check_job_user_is_expired(cluster=cluster)
