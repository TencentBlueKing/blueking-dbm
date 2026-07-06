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
from backend.db_meta.enums import InstanceStatus
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.common.random_job_with_ticket_map import (
    TICKET_TYPE_SENSITIVE_LIST,
    get_instance_with_random_job,
)
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
        is_drop_success = True
        # 删除localhost和 local_ip用户
        payloads = []
        not_running_status_instances = []
        instance_list = get_instance_with_random_job(cluster=cluster, ticket_type=ticket_type)
        if not instance_list:
            self.log_error(_("当前集群没有查询到需要删临时账号的实例：集群域名：{}, 单据类型：{}".format(cluster.immute_domain, ticket_type)))
            return False

        for instance in instance_list:
            # 会话级开关说明（与 create_random_job_user.py 中授权语句对称）：
            #   1) set session sql_log_bin = 0
            #      关闭本会话 binlog 记录，避免临时账号的 drop 语句写入本机 binlog，
            #      从而流入下游 slave 或备份工具，产生"账号漂移"风险。
            #      注意：tc_admin=0 只影响 TDBCTL 路由，不影响本机 binlog 是否落盘，
            #            因此 sql_log_bin=0 是必需的，二者职责正交、不可省略。
            #   2) set tc_admin = 0
            #      仅对中控（TDBCTL/Spider）节点生效：让本次会话按"单机 MySQL"模式执行，
            #      不再通过 TDBCTL 路由层广播到后端 remote 集群，
            #      同时规避集群模式下的隐式一致性检查导致 drop user 失败。
            #      对普通 MySQL/Proxy 实例本条命令不生效；配合 force=true 兜底，非中控实例即使不识别该参数也不会中断整体流程。
            #   3) 最后 set session sql_log_bin = 1 恢复默认，避免连接被复用时污染后续语句。
            cmd = [
                "set session sql_log_bin = 0 ;",
                "set tc_admin = 0;",
                f"drop user `{user}`@`localhost`;",
                f"drop user `{user}`@`{instance['instance'].split(':')[0]}`;",
                "set session sql_log_bin = 1 ;",
            ]
            # 最后统一打开binlog, 避免复用异常
            payloads.append(
                {
                    "addresses": [instance["instance"]],
                    "cmds": cmd,
                    "force": True,  # 中间出错也要执行下去，保证重新打开binlog
                    "bk_cloud_id": cluster.bk_cloud_id,
                }
            )
            # 收集非running状态的实例信息
            if instance["cmdb_status"] != InstanceStatus.RUNNING:
                not_running_status_instances.append(instance["instance"])

        resp = DRSApi.mysql_complex_rpc(
            {
                "payloads": payloads,
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )
        for result in resp:
            if result["error_msg"]:
                # 如果是实例级别的失败，则判断下面，同时输出日志
                self.log_error(
                    f"The result [drop user `{user}`] in {result['address']} error is: [{result['error_msg']}]"
                )
                # 如果实例是running状态，应该记录错误，并且返回异常
                # 如果实例非running状态，且单据类型加入敏感队列，则需要记录错误，并且返回异常
                if result["address"] in not_running_status_instances and ticket_type not in TICKET_TYPE_SENSITIVE_LIST:
                    # 如果是非running状态，标记warning信息，但不作异常处理
                    self.log_warning(f"[{result['address']} is not running in dbm ,ignore]")

                is_drop_success = False
                continue

            # 如果drop user 过程中出现异常，先打印，但不报错，这里只是为打印命令异常的内容。
            # 一般情况基本都是账号不存在才有异常。
            if result["cmd_results"]:
                err_list = [i["error_msg"] for i in result["cmd_results"] if i["error_msg"]]
                if err_list:
                    error_log = "\n".join(err_list)
                    self.log_warning(f"The result [drop user `{user}`] in {result['address']} error is: [{error_log}]")

            self.log_info(f"The result [drop user `{user}`] in {result['address']} is [success]")

        if not is_drop_success:
            self.log_error(f"drop user error in cluster [{cluster.immute_domain}]")
            return False

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
