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
import re

from backend import env
from backend.components import MySQLPrivManagerApi
from backend.constants import IP_RE_PATTERN
from backend.core.encrypt.constants import AsymmetricCipherConfigType
from backend.core.encrypt.handlers import AsymmetricHandler
from backend.db_proxy.constants import ExtensionType
from backend.db_proxy.models import DBExtension
from backend.flow.consts import DBM_JOB, DEFAULT_INSTANCE, MySQLPrivComponent, UserName
from backend.ticket.constants import TicketType

apply_list = [
    TicketType.MYSQL_SINGLE_APPLY.value,
    TicketType.MYSQL_HA_APPLY.value,
    TicketType.TENDBCLUSTER_APPLY.value,
]

logger = logging.getLogger("flow")


class PayloadHandler(object):
    def __init__(self, bk_cloud_id: int, ticket_data: dict, cluster: dict, cluster_type: str = None):
        """
        @param bk_cloud_id 操作的云区域
        @param ticket_data 单据信息
        @param cluster 需要操作的集群信息
        @param cluster_type 表示操作的集群类型，会决定到db_config获取配置的空间
        """
        self.bk_cloud_id = bk_cloud_id
        self.ticket_data = ticket_data
        self.cluster = cluster
        self.cluster_type = cluster_type
        self.account = self.get_mysql_account()
        self.proxy_account = self.get_proxy_account()

        # todo 后面可能优化这个问题
        if self.ticket_data.get("module"):
            self.db_module_id = self.ticket_data["module"]
        elif self.cluster and self.cluster.get("db_module_id"):
            self.db_module_id = self.cluster["db_module_id"]
        else:
            self.db_module_id = 0

    @staticmethod
    def get_proxy_account():
        """
        获取proxy实例内置帐户密码
        """
        data = MySQLPrivManagerApi.get_password(
            {
                "instances": [DEFAULT_INSTANCE],
                "users": [{"username": UserName.PROXY.value, "component": MySQLPrivComponent.PROXY.value}],
            }
        )
        return {"proxy_admin_pwd": data[0]["password"], "proxy_admin_user": data[0]["username"]}

    def get_mysql_account(self) -> dict:
        """
        获取mysql实例内置帐户密码
        """
        user_map = {}
        value_to_name = {member.value: member.name.lower() for member in UserName}
        data = MySQLPrivManagerApi.get_password(
            {
                "instances": [DEFAULT_INSTANCE],
                "users": [
                    {"username": UserName.BACKUP.value, "component": MySQLPrivComponent.MYSQL.value},
                    {"username": UserName.MONITOR.value, "component": MySQLPrivComponent.MYSQL.value},
                    {"username": UserName.MONITOR_ACCESS_ALL.value, "component": MySQLPrivComponent.MYSQL.value},
                    {"username": UserName.OS_MYSQL.value, "component": MySQLPrivComponent.MYSQL.value},
                    {"username": UserName.REPL.value, "component": MySQLPrivComponent.MYSQL.value},
                    {"username": UserName.YW.value, "component": MySQLPrivComponent.MYSQL.value},
                ],
            }
        )
        for user in data:
            user_map[value_to_name[user["username"]] + "_user"] = (
                "MONITOR" if user["username"] == UserName.MONITOR_ACCESS_ALL.value else user["username"]
            )
            user_map[value_to_name[user["username"]] + "_pwd"] = user["password"]

        if self.ticket_data["ticket_type"] in apply_list:
            # 部署类单据临时给个ADMIN初始化账号密码，部署完成会完成随机化
            user_map["admin_user"] = "ADMIN"
        else:
            # 获取非部署类单据的临时账号作为这次的ADMIN账号
            user_map["admin_user"] = f"{DBM_JOB}{self.ticket_data['uid']}"

        # 用job的root_id 作为这次的临时密码
        user_map["admin_pwd"] = self.ticket_data["job_root_id"]

        return user_map

    @staticmethod
    def __get_super_account_bypass():
        """
        旁路逻辑：获取环境变量中的access_hosts, 用户名和密码
        """
        access_hosts = env.TEST_ACCESS_HOSTS or re.compile(IP_RE_PATTERN).findall(env.DRS_APIGW_DOMAIN)
        drs_account_data = {
            "access_hosts": access_hosts,
            "user": env.DRS_USERNAME,
            "pwd": env.DRS_PASSWORD,
        }

        access_hosts = env.TEST_ACCESS_HOSTS or re.compile(IP_RE_PATTERN).findall(env.DBHA_APIGW_DOMAIN_LIST)
        dbha_account_data = {
            "access_hosts": access_hosts,
            "user": env.DBHA_USERNAME,
            "pwd": env.DBHA_PASSWORD,
        }

        return drs_account_data, dbha_account_data

    def get_super_account(self):
        """
        获取mysql机器系统管理账号信息
        """

        if env.DRS_USERNAME and env.DBHA_USERNAME:
            return self.__get_super_account_bypass()

        bk_cloud_name = AsymmetricCipherConfigType.get_cipher_cloud_name(self.bk_cloud_id)
        drs = DBExtension.get_latest_extension(bk_cloud_id=self.bk_cloud_id, extension_type=ExtensionType.DRS)
        drs_account_data = {
            "access_hosts": DBExtension.get_extension_access_hosts(
                bk_cloud_id=self.bk_cloud_id, extension_type=ExtensionType.DRS
            ),
            "pwd": AsymmetricHandler.decrypt(name=bk_cloud_name, content=drs.details["pwd"]),
            "user": AsymmetricHandler.decrypt(name=bk_cloud_name, content=drs.details["user"]),
        }

        dbha = DBExtension.get_latest_extension(bk_cloud_id=self.bk_cloud_id, extension_type=ExtensionType.DBHA)
        dbha_account_data = {
            "access_hosts": DBExtension.get_extension_access_hosts(
                bk_cloud_id=self.bk_cloud_id, extension_type=ExtensionType.DBHA
            ),
            "pwd": AsymmetricHandler.decrypt(name=bk_cloud_name, content=dbha.details["pwd"]),
            "user": AsymmetricHandler.decrypt(name=bk_cloud_name, content=dbha.details["user"]),
        }

        return drs_account_data, dbha_account_data
