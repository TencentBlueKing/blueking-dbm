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
from backend.db_meta.enums import MachineType
from backend.db_meta.models import Machine, ProxyInstance, StorageInstance
from backend.flow.consts import TDBCTL_USER, DBActuatorActionEnum, DBActuatorTypeEnum
from backend.flow.utils.mysql.act_payload.base.payload_base import PayloadBase
from backend.flow.utils.mysql.act_payload.mixed.account_mixed.mysql_account_mixed import MySQLAccountMixed


class CloneGrantsFromFilePayload(PayloadBase, MySQLAccountMixed):
    def dump_priv_on_source(self, **kwargs):
        """从文件中克隆授权"""
        ip = kwargs["ip"]
        port = self.cluster["port"]

        m = Machine.objects.get(ip=ip, bk_cloud_id=self.bk_cloud_id)
        if m.machine_type == MachineType.SPIDER:
            role = ProxyInstance.objects.get(machine=m, port=port).instance_role
            db_type = DBActuatorTypeEnum.Spider.value
        else:
            role = StorageInstance.objects.get(machine=m, port=port).instance_role
            db_type = DBActuatorTypeEnum.MySQL.value

        return {
            "db_type": db_type,
            "action": DBActuatorActionEnum.CloneGrantsDumpPriv.value,
            "payload": {
                "general": {
                    "runtime_account": {
                        **self.mysql_admin_account(self.ticket_data),
                        **self.mysql_static_account(),
                    }
                },
                "extend": {
                    "host": ip,
                    "port": int(port),
                    "role": role,
                    "backup_type": "logical",
                    "backup_gsd": ["grant"],
                    "backup_id": self.cluster["backup_id"],
                    "bill_id": str(self.ticket_data["uid"]),
                    "custom_backup_dir": "",
                    "shard_id": 0,
                    "backup_file_tag": "",
                    "db_patterns": ["*"],
                    "ignore_dbs": [],
                    "table_patterns": ["*"],
                    "ignore_tables": [],
                    "source_priv_file_path": self.cluster["source_priv_file_path"],
                },
            },
        }

    def on_dest(self, **kwargs):
        ip = kwargs["ip"]  # self.cluster["ip"]
        m = Machine.objects.get(ip=ip, bk_cloud_id=self.bk_cloud_id)
        if m.machine_type == MachineType.SPIDER:
            db_type = DBActuatorTypeEnum.Spider.value
        else:
            db_type = DBActuatorTypeEnum.MySQL.value

        static_accounts = self.mysql_static_account()
        system_users = list(
            {v for k, v in static_accounts.items() if k.endswith("_user")}
            | {
                self.mysql_drs_account(self.bk_cloud_id)["user"],
                self.mysql_dbha_account(self.bk_cloud_id)["user"],
                self.mysql_webconsole_account(self.bk_cloud_id)["user"],
                self.mysql_admin_account(self.ticket_data)["admin_user"],
            }
        )

        system_users.append(TDBCTL_USER)  # TenDBCluster 集群内部的账号不需要克隆

        return {
            "db_type": db_type,
            "action": self.cluster["action"],
            "payload": {
                "general": {
                    "runtime_account": {
                        **self.mysql_admin_account(self.ticket_data),
                        **self.mysql_static_account(),
                    }
                },
                "extend": {
                    "system_users": system_users,
                    "source_ip": self.cluster["source_ip"],
                    "source_port": int(self.cluster["source_port"]),
                    "source_raw_version": self.cluster["source_raw_version"],
                    "source_priv_file_path": self.cluster["source_priv_file_path"],
                    "target_ip": kwargs["ip"],
                    "target_port": int(self.cluster["dest_port"]),
                    "is_spider": self.cluster["is_spider"],
                },
            },
        }
