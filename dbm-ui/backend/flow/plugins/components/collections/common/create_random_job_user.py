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

from backend.components import DBPrivManagerApi
from backend.db_meta.enums import InstanceStatus
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.common.random_job_with_ticket_map import (
    TICKET_TYPE_SENSITIVE_LIST,
    get_instance_with_random_job,
)
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class AddTempUserForClusterService(BaseService):
    """
    为单据添加job的临时本地账号，操作目标实例
    单据是以集群维度来添加，如果单据涉及到集群，应该统一添加账号密码，以便后续操作方便
    """

    def create_temp_user_for_cluster(self, cluster: Cluster, ticket_type: TicketType, job_root_id: str) -> bool:
        """
        按照集群维度并发处理实例授权逻辑
        通过mysql_complex_rpc并发接口，拼接授权密码，异常达到并发效果，提高效率
        @param cluster: 集群信息实例
        @param user: 待添加账号
        @param pwd: 密码
        @param ticket_type: 触发此逻辑的单据类型
        @param job_root_id: 触发此逻辑的任务flow id
        """
        # 获取每套集群的所有需要添加临时的账号
        instance_list = get_instance_with_random_job(cluster=cluster, ticket_type=ticket_type)
        if not instance_list:
            self.log_error(_("当前集群没有查询到需要添加临时账号的实例：集群域名：{}, 单据类型：{}".format(cluster.immute_domain, ticket_type)))
            return False

        # 标记位
        is_add_success = True

        raw_resp = DBPrivManagerApi.add_mysql_temp_account_v2(
            {
                "bk_cloud_id": cluster.bk_cloud_id,
                "addresses": [i["instance"] for i in instance_list],
                "root_id": job_root_id,
            }
        )
        self.log_info(raw_resp)

        not_running_status_instances = [
            i["instance"] for i in instance_list if i["cmdb_status"] != InstanceStatus.RUNNING
        ]

        resp = []
        for i in instance_list:
            address = i["instance"]
            errors = raw_resp.get(address, [])
            resp.append({"address": address, "error_msg": ". ".join(errors)})

        # 遍历判断每个实例的授权结果
        for result in resp:
            if result["error_msg"]:
                # 出现执行异常，判断实例状态以及自定义表
                self.log_error(_("在[{}]创建临时添加账号失败:[{}]").format(result["address"], result["error_msg"]))

                if result["address"] in not_running_status_instances and ticket_type not in TICKET_TYPE_SENSITIVE_LIST:
                    # 如果是非running状态，默认标记warning信息，但不作异常处理
                    self.log_warning(_("[{} 在dbm平台状态非running ,忽略]".format(result["address"])))
                else:
                    # 如果实例是running状态，应该记录错误，并且返回异常
                    # 如果实例非running状态，且单据类型加入敏感队列，则需要记录错误，并且返回异常
                    is_add_success = False
                continue
            self.log_info(_("在[{}]创建临时添加账号成功").format(result["address"]))

        return is_add_success

    def _execute(self, data, parent_data, callback=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        err_num = 0
        for cluster_id in kwargs["cluster_ids"]:
            # 获取每个cluster_id对应的对象
            try:
                cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=global_data["bk_biz_id"])
            except Cluster.DoesNotExist:
                raise ClusterNotExistException(
                    cluster_id=cluster_id, bk_biz_id=global_data["bk_biz_id"], message=_("集群不存在")
                )
            if not self.create_temp_user_for_cluster(
                cluster=cluster,
                ticket_type=global_data.get("ticket_type", "test"),
                job_root_id=global_data["job_root_id"],
            ):
                # 如果授权不成功
                err_num = err_num + 1
                self.log_error(f"create temp-job-user in the cluster[{cluster.immute_domain}] failed")
                continue

            self.log_info(f"create temp-job-user in the cluster[{cluster.immute_domain}] successfully")

        if err_num > 0:
            # 有错误先返回则直接返回异常
            self.log_error("instances add temp job user failed")
            return False

        return True


class AddTempUserForClusterComponent(Component):
    name = __name__
    code = "add_job_temp_user"
    bound_service = AddTempUserForClusterService
