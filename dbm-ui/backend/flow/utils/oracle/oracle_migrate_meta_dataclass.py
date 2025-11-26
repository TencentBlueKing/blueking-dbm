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
from dataclasses import dataclass

from backend.configuration.constants import DBType
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.instance_role import InstanceRole
from backend.db_meta.enums.spec import SpecClusterType, SpecMachineType
from backend.db_meta.models.spec import Spec
from backend.flow.consts import DEFAULT_DB_MODULE_ID
from backend.flow.utils.oracle.migrate_meta import OracleMigrateMeta


@dataclass()
class MigrateActKwargs:
    """节点私有变量数据类"""

    def __init__(self):
        self.bk_biz_id: int = None
        # 流程id
        self.root_id: int = None

        # 源端cluster信息
        self.source_cluster_info: dict = None
        # 云区域id
        self.bk_cloud_id = 0
        # 实例角色
        self.instance_role = [
            InstanceRole.PRIMARY.value,
            InstanceRole.STANDBY.value,
        ]
        # 目标环境副本集oracle机型规格
        self.dest_machine_spec: dict = self.get_oracle_spec_info(
            cluster_type=SpecClusterType.Oracle.value, machine_type=SpecMachineType.ORACLE.value
        )

        # 源环境机器映射目标环境机器规格
        self.machine_spec: dict = None
        # 集群实例
        self.storages: list = []
        # 管理员用户
        self.manager_users: list = ["perfstat", "execute_user"]
        # 主域名
        self.immute_domain: str = None
        # 集群类型
        self.cluster_type: str = None

    @staticmethod
    def get_oracle_spec_info(cluster_type: str, machine_type: str) -> dict:
        """获取机器规格"""

        machine_specs = {}
        for spec in Spec.objects.filter(spec_cluster_type=cluster_type, spec_machine_type=machine_type):
            spec_info = {"spec_id": spec.spec_id, "spec_config": spec.get_spec_info()}
            for device in spec.device_class:
                machine_specs[device] = spec_info
        return machine_specs

    def get_storages(self):
        """获取实例信息"""

        if self.source_cluster_info.get("primary_ip"):
            self.storages.append(
                {
                    "ip": self.source_cluster_info.get("primary_ip"),
                    "port": self.source_cluster_info.get("port"),
                    "role": InstanceRole.PRIMARY.value,
                    "domain": self.source_cluster_info.get("primary_domain"),
                    "service_name": self.source_cluster_info.get("service_name"),
                }
            )
            self.immute_domain = self.source_cluster_info.get("primary_domain")
        if self.source_cluster_info.get("standby_ip"):
            self.storages.append(
                {
                    "ip": self.source_cluster_info.get("standby_ip"),
                    "port": self.source_cluster_info.get("port"),
                    "role": InstanceRole.STANDBY.value,
                    "domain": self.source_cluster_info.get("standby_domain"),
                    "service_name": self.source_cluster_info.get("service_name"),
                }
            )
        if self.source_cluster_info.get("primary_ip") and self.source_cluster_info.get("standby_ip"):
            self.cluster_type = ClusterType.OraclePrimaryStandby.value
        elif self.source_cluster_info.get("primary_ip") and not self.source_cluster_info.get("standby_ip"):
            self.cluster_type = ClusterType.OracleSingleNone.value

    def get_check_dest_cluster_info(self, cluster_name) -> dict:
        """检查cluster是否已经在目标端存在信息"""

        return {
            "bk_biz_id": self.bk_biz_id,
            "cluster_name": cluster_name,
            "meta_func_name": OracleMigrateMeta.check_dest_cluster.__name__,
        }

    def get_check_spec_info(self) -> dict:
        """检查目标端机器规格是否存在"""

        if self.source_cluster_info.get("machine_type") in self.dest_machine_spec:
            spec = self.dest_machine_spec.get(self.source_cluster_info.get("machine_type"))
        else:
            spec = {"spec_id": 0, "spec_config": ""}
        self.machine_spec = spec

        return {
            "spec": spec,
            "meta_func_name": OracleMigrateMeta.check_machine_spec.__name__,
        }

    def get_dba_info(self) -> dict:
        """获取dba信息"""

        return {
            "bk_biz_id": self.bk_biz_id,
            "db_admins": [
                {"db_type": DBType.Oracle.value, "users": self.source_cluster_info["oracle_dbas"].split(",")}
            ],
            "meta_func_name": OracleMigrateMeta.upsert_dba.__name__,
        }

    def get_migrate_info(self) -> dict:
        """获取迁移信息"""

        return {
            "meta_func_name": OracleMigrateMeta.migrate_cluster.__name__,
            "bk_biz_id": self.bk_biz_id,
            "name": self.source_cluster_info.get("name"),
            "immute_domain": self.immute_domain,
            "db_module_id": DEFAULT_DB_MODULE_ID,
            "alias": self.source_cluster_info.get("alias"),
            "major_version": self.source_cluster_info.get("major_version"),
            "storages": self.storages,
            "creator": self.source_cluster_info.get("oracle_dbas").split(",")[0],
            "bk_cloud_id": self.bk_cloud_id,
            "region": self.source_cluster_info.get("region"),
            "spec_id": self.machine_spec.get("spec_id"),
            "spec_config": self.machine_spec.get("spec_config"),
            "cluster_type": self.cluster_type,
            "disaster_tolerance_level": self.source_cluster_info.get("disaster_tolerance_level"),
        }

    def get_save_password_info(self) -> dict:
        """获取保存密码信息 perfstat execute_user"""

        info = {
            "usernames": self.manager_users,
            "operator": self.source_cluster_info.get("oracle_dbas").split(",")[0],
            "password_infos": [],
            "meta_func_name": OracleMigrateMeta.save_password.__name__,
        }

        info["password_infos"].append(
            {
                "nodes": [
                    {"ip": node.get("ip"), "port": node.get("port"), "bk_cloud_id": self.bk_cloud_id}
                    for node in self.storages
                ],
                "password": self.source_cluster_info.get("password"),
            }
        )
        return info

    def get_change_dns_app_info(self) -> dict:
        """获取修改dns的app字段信息"""

        return {
            "app": self.source_cluster_info.get("app"),
            "new_app": str(self.bk_biz_id),
            "bk_cloud_id": self.bk_cloud_id,
            "change_domain_app": [node.get("domain") for node in self.storages],
            "meta_func_name": OracleMigrateMeta.change_domain_app.__name__,
        }

    def get_install_plugin_info(self, plugin_name: str) -> dict:
        """安装蓝鲸插件"""

        ips = [host["ip"] for host in self.storages]
        return {
            "plugin_name": plugin_name,
            "ips": ips,
            "bk_cloud_id": self.bk_cloud_id,
        }
