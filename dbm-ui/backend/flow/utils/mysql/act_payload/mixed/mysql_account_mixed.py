# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import base64
import re
from typing import Dict, Optional

from backend import env
from backend.components import DBPrivManagerApi
from backend.constants import IP_RE_PATTERN
from backend.core.encrypt.constants import AsymmetricCipherConfigType
from backend.core.encrypt.handlers import AsymmetricHandler
from backend.db_proxy.constants import ExtensionType
from backend.db_proxy.models import DBExtension
from backend.flow.consts import DBM_MYSQL_JOB_TMP_USER_PREFIX, DEFAULT_INSTANCE, MySQLPrivComponent, UserName
from backend.ticket.constants import TicketType


class MySQLAccountMixed(object):
    @staticmethod
    def all_account(ticket_data):
        res = MySQLAccountMixed.static_account()
        if ticket_data.get("ticket_type", None) in [
            TicketType.MYSQL_SINGLE_APPLY,
            TicketType.MYSQL_HA_APPLY,
            TicketType.TENDBCLUSTER_APPLY,
            TicketType.TENDBCLUSTER_APPEND_DEPLOY_CTL,
        ]:
            res["admin_user"] = "ADMIN"
        else:
            res["admin_user"] = "{}{}".format(DBM_MYSQL_JOB_TMP_USER_PREFIX, ticket_data["job_root_id"])

        res["admin_pwd"] = ticket_data["job_root_id"]
        return res

    @staticmethod
    def static_account(*users: UserName):
        if not users:
            users = [
                UserName.BACKUP,
                UserName.MONITOR,
                UserName.MONITOR_ACCESS_ALL,
                UserName.OS_MYSQL,
                UserName.REPL,
                UserName.YW,
                UserName.PARTITION_YW,
            ]

        user_map = {}
        value_to_name = {member.value: member.name.lower() for member in UserName}

        data = DBPrivManagerApi.get_password(
            {
                "instances": [DEFAULT_INSTANCE],
                "users": [
                    {"username": username.value, "component": MySQLPrivComponent.MYSQL.value} for username in users
                ],
            }
        )
        for user in data["items"]:
            user_map[value_to_name[user["username"]] + "_user"] = (
                "MONITOR" if user["username"] == UserName.MONITOR_ACCESS_ALL else user["username"]
            )
            user_map[value_to_name[user["username"]] + "_pwd"] = base64.b64decode(user["password"]).decode("utf-8")

        return user_map

    @staticmethod
    def partition_yw_account():
        res = MySQLAccountMixed.static_account(UserName.PARTITION_YW)
        return {k.removeprefix("partition_yw_"): v for k, v in res.items()}

    @staticmethod
    def drs_account(bk_cloud_id) -> Dict:
        if env.DRS_USERNAME:
            access_hosts = env.TEST_ACCESS_HOSTS or re.compile(IP_RE_PATTERN).findall(env.DRS_APIGW_DOMAIN)
            return {
                "access_hosts": access_hosts,
                "user": env.DRS_USERNAME,
                "pwd": env.DRS_PASSWORD,
            }
        else:
            return MySQLAccountMixed.__extension_account(bk_cloud_id=bk_cloud_id, et=ExtensionType.DRS)

    @staticmethod
    def dbha_account(bk_cloud_id: int) -> Dict:
        if env.DBHA_USERNAME:
            access_hosts = env.TEST_ACCESS_HOSTS or re.compile(IP_RE_PATTERN).findall(env.DBHA_APIGW_DOMAIN_LIST)
            return {
                "access_hosts": access_hosts,
                "user": env.DBHA_USERNAME,
                "pwd": env.DBHA_PASSWORD,
            }
        else:
            return MySQLAccountMixed.__extension_account(bk_cloud_id=bk_cloud_id, et=ExtensionType.DBHA)

    @staticmethod
    def webconsole_account(bk_cloud_id: int):
        if env.WEBCONSOLE_USERNAME:
            access_hosts = env.TEST_ACCESS_HOSTS or re.compile(IP_RE_PATTERN).findall(env.DRS_APIGW_DOMAIN)
            return {
                "access_hosts": access_hosts,
                "user": env.WEBCONSOLE_USERNAME,
                "pwd": env.WEBCONSOLE_PASSWORD,
            }
        else:
            return MySQLAccountMixed.__extension_account(
                bk_cloud_id=bk_cloud_id,
                et=ExtensionType.DRS,
                alt_user_key="webconsole_user",
                alt_pwd_key="webconsole_pwd",
            )

    @staticmethod
    def __extension_account(
        bk_cloud_id: int, et: ExtensionType, alt_user_key: Optional[str] = None, alt_pwd_key: Optional[str] = None
    ) -> Dict:
        bk_cloud_name = AsymmetricCipherConfigType.get_cipher_cloud_name(bk_cloud_id)
        drs = DBExtension.get_latest_extension(bk_cloud_id=bk_cloud_id, extension_type=et)

        if not alt_user_key:
            alt_user_key = "user"
        if not alt_pwd_key:
            alt_pwd_key = "pwd"

        return {
            "access_hosts": DBExtension.get_extension_access_hosts(bk_cloud_id=bk_cloud_id, extension_type=et),
            "pwd": AsymmetricHandler.decrypt(name=bk_cloud_name, content=drs.details[alt_pwd_key]),
            "user": AsymmetricHandler.decrypt(name=bk_cloud_name, content=drs.details[alt_user_key]),
        }
