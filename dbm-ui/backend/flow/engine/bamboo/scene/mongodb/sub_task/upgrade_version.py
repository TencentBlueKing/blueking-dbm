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
from typing import Optional

from django.utils.translation import gettext as _

from backend.flow.consts import MongoDBActuatorActionEnum, MongoDBClusterRole, MongoDBManagerUser
from backend.flow.engine.bamboo.scene.mongodb.sub_task.instance_op import InstanceOpSubTask
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job2 import ExecJobComponent2
from backend.flow.utils.mongodb.mongodb_dataclass import CommonContext
from backend.flow.utils.mongodb.mongodb_repo import MongoNode
from backend.flow.utils.mongodb.mongodb_util import MongoUtil


class MongoUpgradeVersionSubTask:
    """MongoDB version-upgrade atom actions for one node."""

    @classmethod
    def shield_dbmon_act(
        cls,
        file_path: str,
        exec_node: MongoNode,
        upgrade_phase: Optional[str] = None,
        dest_version: Optional[str] = None,
        instance_type: Optional[str] = None,
    ) -> dict:
        return {
            "act_name": _("MongoDB-屏蔽dbmon-{}:{}".format(exec_node.ip, exec_node.port)),
            "act_component_code": ExecJobComponent2.code,
            "kwargs": InstanceOpSubTask.make_kwargs(
                file_path=file_path,
                exec_node=exec_node,
                op="shield_dbmon",
                upgrade_phase=upgrade_phase,
                dest_version=dest_version,
                instance_type=instance_type,
            ),
        }

    @classmethod
    def unblock_dbmon_act(
        cls,
        file_path: str,
        exec_node: MongoNode,
        upgrade_phase: Optional[str] = None,
        dest_version: Optional[str] = None,
    ) -> dict:
        return {
            "act_name": _("MongoDB-解除屏蔽dbmon-{}:{}".format(exec_node.ip, exec_node.port)),
            "act_component_code": ExecJobComponent2.code,
            "kwargs": InstanceOpSubTask.make_kwargs(
                file_path=file_path,
                exec_node=exec_node,
                op="unblock_dbmon",
                upgrade_phase=upgrade_phase,
                dest_version=dest_version,
            ),
        }

    @classmethod
    def stop_act(
        cls,
        file_path: str,
        exec_node: MongoNode,
        upgrade_phase: Optional[str] = None,
        dest_version: Optional[str] = None,
    ) -> dict:
        return {
            "act_name": _("MongoDB-停实例-{}:{}".format(exec_node.ip, exec_node.port)),
            "act_component_code": ExecJobComponent2.code,
            "kwargs": InstanceOpSubTask.make_kwargs(
                file_path=file_path,
                exec_node=exec_node,
                op="stop",
                upgrade_phase=upgrade_phase,
                dest_version=dest_version,
            ),
        }

    @classmethod
    def backup_data_act(
        cls,
        file_path: str,
        exec_node: MongoNode,
        old_full_version: str,
        upgrade_phase: Optional[str] = None,
        dest_version: Optional[str] = None,
    ) -> dict:
        kwargs = InstanceOpSubTask.make_kwargs(
            file_path=file_path,
            exec_node=exec_node,
            op="backup_mongodata",
            upgrade_phase=upgrade_phase,
            dest_version=dest_version,
        )
        kwargs["db_act_template"]["payload"]["oldFullVersion"] = old_full_version
        return {
            "act_name": _("MongoDB-备份数据目录-{}:{}".format(exec_node.ip, exec_node.port)),
            "act_component_code": ExecJobComponent2.code,
            "kwargs": kwargs,
        }

    @classmethod
    def upgrade_binary_act(
        cls,
        file_path: str,
        exec_node: MongoNode,
        current_version: str,
        dest_version: str,
        instance_type: str,
        pkg: str,
        pkg_md5: str,
        upgrade_phase: Optional[str] = None,
    ) -> dict:
        return {
            "act_name": _("MongoDB-升级二进制-{}:{}".format(exec_node.ip, exec_node.port)),
            "act_component_code": ExecJobComponent2.code,
            "kwargs": InstanceOpSubTask.make_replace_package_kwargs(
                file_path=file_path,
                exec_node=exec_node,
                current_version=current_version,
                dest_version=dest_version,
                instance_type=instance_type,
                pkg=pkg,
                pkg_md5=pkg_md5,
                upgrade_phase=upgrade_phase,
            ),
        }

    @classmethod
    def start_act(
        cls,
        file_path: str,
        exec_node: MongoNode,
        upgrade_phase: Optional[str] = None,
        dest_version: Optional[str] = None,
    ) -> dict:
        return {
            "act_name": _("MongoDB-启实例-{}:{}".format(exec_node.ip, exec_node.port)),
            "act_component_code": ExecJobComponent2.code,
            "kwargs": InstanceOpSubTask.make_kwargs(
                file_path=file_path,
                exec_node=exec_node,
                op="start",
                upgrade_phase=upgrade_phase,
                dest_version=dest_version,
            ),
        }

    @classmethod
    def service_check_act(
        cls,
        file_path: str,
        exec_node: MongoNode,
        upgrade_phase: Optional[str] = None,
        dest_version: Optional[str] = None,
    ) -> dict:
        return {
            "act_name": _("MongoDB-服务检查-{}:{}".format(exec_node.ip, exec_node.port)),
            "act_component_code": ExecJobComponent2.code,
            "kwargs": InstanceOpSubTask.make_kwargs(
                file_path=file_path,
                exec_node=exec_node,
                op="service_status_check",
                upgrade_phase=upgrade_phase,
                dest_version=dest_version,
            ),
        }

    @classmethod
    def precheck_disk_upgrade_act(cls, file_path: str, exec_node: MongoNode, act_label: Optional[str] = None) -> dict:
        label = act_label if act_label is not None else "{}:{}".format(exec_node.ip, exec_node.port)
        return {
            "act_name": _("MongoDB-升级前磁盘空间检查-{}".format(label)),
            "act_component_code": ExecJobComponent2.code,
            "kwargs": InstanceOpSubTask.make_kwargs(
                file_path=file_path, exec_node=exec_node, op="precheck_disk_upgrade"
            ),
        }

    @classmethod
    def precheck_upgrade_act(
        cls, file_path: str, exec_node: MongoNode, current_version: str, act_prefix: str = None
    ) -> dict:
        act_prefix = act_prefix or _("升级前检查")
        instance_type = "mongos" if exec_node.role == MongoDBClusterRole.Mongos.value else "mongod"
        kwargs = InstanceOpSubTask.make_kwargs(
            file_path=file_path,
            exec_node=exec_node,
            op="precheck_upgrade",
            instance_type=instance_type,
        )
        kwargs["db_act_template"]["payload"]["currentVersion"] = current_version
        return {
            "act_name": _("MongoDB-{}-{}:{}".format(act_prefix, exec_node.ip, exec_node.port)),
            "act_component_code": ExecJobComponent2.code,
            "kwargs": kwargs,
        }

    @classmethod
    def _version_major_minor(cls, version: str) -> str:
        v = version.removeprefix("mongodb-")
        parts = v.split(".", 2)
        return ".".join(parts[:2]) if len(parts) >= 2 else v

    @classmethod
    def _fcv_supported(cls, major_minor: str) -> bool:
        try:
            return float(major_minor) >= 3.4
        except ValueError:
            return False

    @classmethod
    def upgrade_rs_protocol_act(
        cls,
        file_path: str,
        exec_node: MongoNode,
        rs_name: Optional[str] = None,
    ) -> dict:
        user, pwd = MongoUtil.get_mongo_user_password(
            exec_node.ip, exec_node.port, exec_node.bk_cloud_id, MongoDBManagerUser.DbaUser.value
        )
        label = rs_name or "{}:{}".format(exec_node.ip, exec_node.port)
        return {
            "act_name": _("MongoDB-升级复制协议版本-{}").format(label),
            "act_component_code": ExecJobComponent2.code,
            "kwargs": {
                "set_trans_data_dataclass": CommonContext.__name__,
                "get_trans_data_ip_var": None,
                "bk_cloud_id": exec_node.bk_cloud_id,
                "exec_ip": exec_node.ip,
                "db_act_template": {
                    "action": MongoDBActuatorActionEnum.MongoUpgradeRsProtocol,
                    "file_path": file_path,
                    "exec_account": "mysql",
                    "sudo_account": "mysql",
                    "payload": {
                        "ip": exec_node.ip,
                        "port": int(exec_node.port),
                        "adminUsername": user,
                        "adminPassword": pwd,
                        "instanceType": "mongod",
                        "targetProtocolVersion": 1,
                    },
                },
            },
        }

    @classmethod
    def postcheck_set_fcv_act(
        cls,
        file_path: str,
        exec_node: MongoNode,
        instance_type: str,
        current_version: str,
        dest_version: str,
    ) -> dict:
        user, pwd = MongoUtil.get_mongo_user_password(
            exec_node.ip, exec_node.port, exec_node.bk_cloud_id, MongoDBManagerUser.DbaUser.value
        )
        old_fcv = cls._version_major_minor(current_version)
        new_fcv = cls._version_major_minor(dest_version)
        if not cls._fcv_supported(new_fcv):
            return None
        return {
            "act_name": _("MongoDB-设置FCV-{}:{}".format(exec_node.ip, exec_node.port)),
            "act_component_code": ExecJobComponent2.code,
            "kwargs": {
                "set_trans_data_dataclass": CommonContext.__name__,
                "get_trans_data_ip_var": None,
                "bk_cloud_id": exec_node.bk_cloud_id,
                "exec_ip": exec_node.ip,
                "db_act_template": {
                    "action": MongoDBActuatorActionEnum.MongoSetFcv,
                    "file_path": file_path,
                    "exec_account": "mysql",
                    "sudo_account": "mysql",
                    "payload": {
                        "ip": exec_node.ip,
                        "port": int(exec_node.port),
                        "adminUsername": user,
                        "adminPassword": pwd,
                        "instanceType": instance_type,
                        "old_fcv": old_fcv,
                        "new_fcv": new_fcv,
                    },
                },
            },
        }
