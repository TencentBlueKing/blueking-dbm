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
import uuid

from backend.components import DRSApi
from backend.flow.consts import MYSQL_SYS_USER, DBActuatorActionEnum, DBActuatorTypeEnum, UserName
from backend.flow.utils.mysql.act_payload.base.payload_base import PayloadBase
from backend.flow.utils.mysql.act_payload.mixed.account_mixed.mysql_account_mixed import MySQLAccountMixed
from backend.flow.utils.mysql.act_payload.mixed.account_mixed.proxy_account_mixed import ProxyAccountMixed
from backend.flow.utils.mysql.get_mysql_sys_user import get_mysql_sys_users


class CloneGrantsPayload(PayloadBase, MySQLAccountMixed, ProxyAccountMixed):
    def dump_mysql_grants(self, **kwargs):
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.MySQLBackupDemand.value,
            "payload": {
                "general": {"runtime_account": self.mysql_static_account()},
                "extend": {
                    "host": self.cluster["host"],
                    "port": int(self.cluster["port"]),
                    "role": self.cluster["role"],
                    "backup_type": "logical",
                    "backup_gsd": ["grant"],
                    "backup_id": uuid.uuid1().__str__(),
                    "bill_id": self.cluster["bill_id"],
                    "shard_id": 0,
                    "backup_file_tag": "",
                    "db_patterns": ["*"],
                    "ignore_dbs": [],
                    "table_patterns": ["*"],
                    "ignore_tables": [],
                },
            },
        }

    def import_grants_file(self, **kwargs):
        source_address = self.cluster["source_address"]
        res = DRSApi.rpc({"addresses": [source_address], "cmds": ["select @@version as version"]})
        if not res:
            raise

        if res[0]["error_msg"]:
            raise

        if "cmd_results" not in res[0]:
            raise

        if res[0]["cmd_results"][0]["error_msg"]:
            raise

        if not res[0]["cmd_results"][0]["table_data"]:
            raise

        version = res[0]["cmd_results"][0]["table_data"][0]["version"]

        admin_user_name_list = [
            UserName.ADMIN.value,
            UserName.BACKUP.value,
            UserName.MONITOR.value,
            UserName.REPL.value,
            UserName.YW.value,
            UserName.PARTITION_YW,
            self.mysql_drs_account(bk_cloud_id=self.bk_cloud_id)["user"],
            self.mysql_dbha_account(bk_cloud_id=self.bk_cloud_id)["user"],
            self.mysql_webconsole_account(bk_cloud_id=self.bk_cloud_id)["user"],
            UserName.MONITOR_ACCESS_ALL,
        ] + [v for k, v in self.mysql_static_account().items() if k.endswith("_user")]

        other_inner_username = [
            "gcs_admin",
            "gcs_dba",
            "monitor",
            "gm",
            "admin",
            "spider",
            "gcs_spider",
            "mariadb.sys",
            "PUBLIC",
            "mysql",
            "mysql.session",
            "mysql.sys",
            "mysql.infoschema",
            "MONITOR_ALL",
            "proxy",
            "default",
            "root",
        ]

        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.ImportGrantsFile.value,
            "payload": {
                "general": {"runtime_account": self.mysql_admin_account(self.ticket_data)},
                "extend": {
                    "bill_id": str(self.ticket_data.get("uid")),
                    "source_ip": source_address.split(":")[0],
                    "source_version": version,
                    "dest_address": self.cluster["dest_address"],
                    "filename": kwargs["trans_data"]["priv_filename"],
                    "ignore_users": list(
                        set(
                            MYSQL_SYS_USER
                            + get_mysql_sys_users(int(self.bk_cloud_id))
                            + admin_user_name_list
                            + other_inner_username
                        )
                    ),
                    "machine_type": self.cluster["machine_type"],
                },
            },
        }
