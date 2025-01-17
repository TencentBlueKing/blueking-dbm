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

from backend.components.mysql_priv_manager.client import DBPrivManagerApi
from backend.db_meta.enums import InstanceStatus
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.common.random_job_with_ticket_map import (
    TICKET_TYPE_SENSITIVE_LIST,
    get_instance_with_random_job,
)
from backend.flow.utils.mysql.get_mysql_sys_user import generate_mysql_tmp_user

logger = logging.getLogger("flow")


class AddTempUserForClusterService(BaseService):
    """
    为单据添加job的临时本地账号，操作目标实例
    单据是以集群维度来添加，如果单据涉及到集群，应该统一添加账号密码，以便后续操作方便
    """

    def __add_priv(self, params):
        """
        定义添加临时账号的内置方法
        """

        try:
            DBPrivManagerApi.add_priv_without_account_rule(params)
            self.log_info(_("在[{}]创建添加账号成功").format(params["address"]))
        except Exception as e:  # pylint: disable=broad-except
            self.log_error(_("[{}]添加用户接口异常，相关信息: {}").format(params["address"], e))
            return False

        return True

    def _execute(self, data, parent_data, callback=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        encrypt_switch_pwd = global_data["job_root_id"]
        common_param = {
            "bk_cloud_id": -1,
            "bk_biz_id": int(global_data["bk_biz_id"]),
            "operator": global_data["created_by"],
            "user": generate_mysql_tmp_user(global_data["job_root_id"]),
            "psw": encrypt_switch_pwd,
            "hosts": [],
            "dbname": "%",
            "dml_ddl_priv": "",
            "global_priv": "all privileges",
            "address": "",
            "role": "",
        }

        err_num = 0
        for cluster_id in kwargs["cluster_ids"]:
            # 获取每个cluster_id对应的对象
            try:
                cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=global_data["bk_biz_id"])
            except Cluster.DoesNotExist:
                raise ClusterNotExistException(
                    cluster_id=cluster_id, bk_biz_id=global_data["bk_biz_id"], message=_("集群不存在")
                )

            # 获取每套集群的云区域id
            common_param["bk_cloud_id"] = cluster.bk_cloud_id

            # 获取每套集群的所有需要添加临时的账号
            instance_list = get_instance_with_random_job(
                cluster=cluster, ticket_type=global_data.get("ticket_type", "test")
            )

            # 开始遍历集群每个实例，添加临时账号
            for inst in instance_list:
                if not inst.get("priv_role"):
                    self.log_error(_("不支持改实例的主机类型授权[{}]: machine_type: {}").format(inst.ip_port, inst.machine_type))
                    err_num = err_num + 1
                    continue

                # 按照实例维度进行添加账号
                common_param["address"] = inst["instance"]
                common_param["hosts"] = ["localhost", inst["instance"].split(":")[0]]
                common_param["role"] = inst["priv_role"]
                if not self.__add_priv(common_param):
                    if inst["cmdb_status"] == InstanceStatus.RUNNING or (
                        inst["cmdb_status"] != InstanceStatus.RUNNING
                        and global_data.get("ticket_type", "test") in TICKET_TYPE_SENSITIVE_LIST
                    ):
                        # 如果实例是running状态，应该记录错误，并且返回异常
                        # 如果实例非running状态，且单据类型加入敏感队列，则需要记录错误，并且返回异常
                        err_num = err_num + 1
                    else:
                        # 如果是非running状态，默认标记warning信息，但不作异常处理
                        self.log_warning(f"[{inst['instance']} is not running in dbm [{inst['cmdb_status']}],ignore]")
                        continue

        if err_num > 0:
            # 有错误先返回则直接返回异常
            self.log_error("instances add priv failed")
            return False

        return True


class AddTempUserForClusterComponent(Component):
    name = __name__
    code = "add_job_temp_user"
    bound_service = AddTempUserForClusterService
