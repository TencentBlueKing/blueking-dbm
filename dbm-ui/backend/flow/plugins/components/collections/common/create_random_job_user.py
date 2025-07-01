"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import hashlib
import logging

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components import DBPrivManagerApi, DRSApi
from backend.db_meta.enums import InstanceStatus
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster
from backend.flow.consts import PrivRole
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.common.random_job_with_ticket_map import (
    TICKET_TYPE_SENSITIVE_LIST,
    get_instance_with_random_job,
)
from backend.flow.utils.mysql.get_mysql_sys_user import generate_mysql_tmp_user
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class AddTempUserForClusterService(BaseService):
    """
    为单据添加job的临时本地账号，操作目标实例
    单据是以集群维度来添加，如果单据涉及到集群，应该统一添加账号密码，以便后续操作方便
    """

    @staticmethod
    def mysql_pwd(pwd) -> str:
        """
        MySQL 4.1+ 的PASSWORD函数实现(SHA1双重哈希)
        @param pwd: 密码字符串
        """
        if isinstance(pwd, str):
            pwd = pwd.encode("utf-8")

        # 第一次SHA1哈希
        hash1 = hashlib.sha1(pwd).digest()
        # 第二次SHA1哈希
        hash2 = hashlib.sha1(hash1).hexdigest()

        # 添加MySQL的'*'前缀
        return "*" + hash2.upper()

    def __add_account_for_privilege_api(
        self, bk_biz_id, bk_cloud_id, job_root_id, created_by, failed_instance, priv_role
    ) -> bool:
        """
        添加临时账号的内置方法
        通过privilege api去添加临时账号
        这里用于出现“infodba_schema.dba_grant does not exist”类型异常的重试方式
        @param bk_biz_id: 业务id
        @param bk_cloud_id: 云区域id
        @param job_root_id: flow id
        @param created_by: 申请者
        @param failed_instance: 添加失败的实例，字符串格式"ip:port"
        @param priv_role: 添加失败的实例的授权角色，对应PrivRole类型
        """
        param = {
            "bk_cloud_id": bk_cloud_id,
            "bk_biz_id": int(bk_biz_id),
            "operator": created_by,
            "user": generate_mysql_tmp_user(job_root_id),
            "psw": job_root_id,
            "hosts": ["localhost", failed_instance.split(":")[0]],
            "dbname": "%",
            "dml_ddl_priv": "",
            "global_priv": "all privileges",
            "address": failed_instance,
            "role": priv_role,
        }
        try:
            DBPrivManagerApi.add_priv_without_account_rule(param)
            self.log_info(_("在[{}]重试创建添加账号成功").format(param["address"]))
        except Exception as e:  # pylint: disable=broad-except
            self.log_error(_("[{}]重试添加用户接口异常，相关信息: {}").format(param["address"], e))
            return False

        return True

    def __add_account_for_drs(self, cluster: Cluster, instance_list: list, user: str, pwd: str) -> (list, list):
        """
        添加临时账号的内置方法
        通过访问drs_api去调用存储过程dba_grant, 以此来添加临时账号
        @param cluster: 集群信息实例
        @param instance_list: 待授权实例列表，每个列表格式{"instance":"ip:port"...}
        @param user: 待添加账号
        @param pwd: 待添加密码
        """
        # 定义not_running状态的表
        not_running_status_instances = []
        # 定义传输参数列表
        payloads = []
        for i in instance_list:
            payloads.append(
                {
                    "addresses": [i["instance"]],
                    "cmds": self.__create_add_priv_cmds(i, user, pwd),
                    "bk_cloud_id": cluster.bk_cloud_id,
                }
            )
            if i["cmdb_status"] != InstanceStatus.RUNNING:
                not_running_status_instances.append(i["instance"])

        # 调用批量接口执行
        resp = DRSApi.mysql_complex_rpc(
            {
                "payloads": payloads,
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )
        return resp, not_running_status_instances

    @staticmethod
    def __create_add_priv_cmds(instance: dict, user: str, pwd_hash: str) -> list:
        """
        拼接临时账号的授权的
        通过dba_grant存储授权，提高授权效率
        每个临时账号给本地ip和localhost生成账号，同时给ALL PRIVILEGES和GRANT OPTION权限
        @param instance: 待授权实例，格式{"instance":"ip:port"...}
        @param user: 待添加账号
        @param pwd_hash: 密文
        """
        if instance["priv_role"] == PrivRole.TDBCTL.value:
            # 这里做差异化处理，如果是中控节点，拼接专属的授权语句
            return [
                "set tc_admin = 0;",
                f"""CREATE USER IF NOT EXISTS '{user}'@'localhost'
                IDENTIFIED WITH mysql_native_password AS '{pwd_hash}';""",
                f"""CREATE USER IF NOT EXISTS '{user}'@'{instance["instance"].split(":")[0]}'
                IDENTIFIED WITH mysql_native_password AS '{pwd_hash}';""",
                f"GRANT ALL PRIVILEGES ON *.* TO '{user}'@'localhost' WITH GRANT OPTION;",
                f"""GRANT ALL PRIVILEGES ON *.* TO '{user}'@'{instance["instance"].split(":")[0]}'
                WITH GRANT OPTION;""",
            ]

        return [
            f"""CALL infodba_schema.dba_grant('{user}', 'localhost,{instance["instance"].split(":")[0]}',
                        '*', '{pwd_hash}', '', '', 'all privileges') ;""",
            f"""GRANT ALL PRIVILEGES ON *.* TO '{user}'@'{instance["instance"].split(":")[0]}' WITH GRANT OPTION""",
            f"""GRANT ALL PRIVILEGES ON *.* TO '{user}'@'localhost' WITH GRANT OPTION""",
        ]

    def create_temp_user_for_cluster(
        self, cluster: Cluster, user: str, pwd: str, ticket_type: TicketType, job_root_id: str
    ) -> bool:
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
        # 标记位
        is_add_success = True

        # 按照集群维度，并发提交权限添加
        resp, not_running_status_instances = self.__add_account_for_drs(
            cluster=cluster, instance_list=instance_list, user=user, pwd=pwd
        )

        # 遍历判断每个实例的授权结果
        for result in resp:
            if result["error_msg"]:
                # 出现执行异常，判断实例状态以及自定义表
                self.log_error(_("在[{}]创建临时添加账号失败:[{}]").format(result["address"], result["error_msg"]))
                # 如果出现异常，通过privilege api接口重新尝试加一次
                self.log_info("retry via privilege_api ...")
                if self.__add_account_for_privilege_api(
                    bk_biz_id=cluster.bk_biz_id,
                    bk_cloud_id=cluster.bk_cloud_id,
                    failed_instance=result["address"],
                    priv_role=[item["priv_role"] for item in instance_list if item["instance"] == result["address"]][
                        0
                    ],
                    created_by=job_root_id,
                    job_root_id=job_root_id,
                ):
                    # 重试成功跳过
                    self.log_info("retry successful")
                    continue

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

        # 根据mysql4.1+的password函数算法加密
        pwd_hash = self.mysql_pwd(global_data["job_root_id"])

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
                user=generate_mysql_tmp_user(global_data["job_root_id"]),
                pwd=pwd_hash,
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
