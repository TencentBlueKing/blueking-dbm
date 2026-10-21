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

from backend.components import DRSApi
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.common.random_job_with_ticket_map import get_instance_with_random_job
from backend.flow.utils.mysql.get_mysql_sys_user import generate_mysql_tmp_user
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class DropTempUserForClusterService(BaseService):
    """
    为单据删除job的临时本地账号，操作目标实例
    单据是以集群维度来删除
    """

    def drop_jor_user(self, cluster: Cluster, root_id: str, ticket_type: TicketType):
        """
        集群维度删除job的临时用户
        """
        # 拼接临时用户的名称
        user = generate_mysql_tmp_user(root_id)
        instance_list = get_instance_with_random_job(cluster=cluster, ticket_type=ticket_type)

        if not instance_list:
            self.log_error(_("当前集群没有查询到需要删临时账号的实例：集群域名：{}, 单据类型：{}".format(cluster.immute_domain, ticket_type)))
            return False

        # ''@'' 的形式是MySQL官方推荐的, 用单引号
        cmds = [
            "set session sql_log_bin = 0 ;",
            "set tc_admin = 0;",
            f"drop user '{user}'@localhost;",
            f"drop user '{user}'@'%';",
            "set session sql_log_bin = 1 ;",
        ]

        resp = DRSApi.v2_mysql_rpc(
            {
                "bk_cloud_id": cluster.bk_cloud_id,
                "addresses": [i["instance"] for i in instance_list],
                "cmds": cmds,
                "query_timeout": 600,
                "force": True,
                "skip_set_names": True,
            }
        )
        for result in resp:
            if result["error_msg"]:
                # 如果是实例级别的失败，则判断下面，同时输出日志
                self.log_error(
                    f"The result [drop user `{user}`] in {result['address']} error is: [{result['error_msg']}]"
                )
                continue

            if result["cmd_results"]:
                for cr in result["cmd_results"][1:]:
                    if cr["error_msg"]:
                        self.log_error(cr["error_msg"])

        self.log_info(f"drop user finish in cluster [{cluster.immute_domain}]")
        return True

    def _execute(self, data, parent_data, callback=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        is_err = False
        for cluster_id in kwargs["cluster_ids"]:
            # 获取每个cluster_id对应的对象
            try:
                cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=global_data["bk_biz_id"])
            except Cluster.DoesNotExist:
                raise ClusterNotExistException(
                    cluster_id=cluster_id, bk_biz_id=global_data["bk_biz_id"], message=_("集群不存在")
                )
            if not self.drop_jor_user(
                cluster=cluster, root_id=global_data["job_root_id"], ticket_type=global_data.get("ticket_type", "test")
            ):
                # 删除账号不成功
                is_err = True

        if is_err:
            return False

        return True


class DropTempUserForClusterComponent(Component):
    name = __name__
    code = "drop_job_temp_user"
    bound_service = DropTempUserForClusterService
