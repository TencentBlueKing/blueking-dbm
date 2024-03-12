"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import copy
import logging

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_package.models import Package
from backend.flow.consts import DBActuatorTypeEnum, MediumEnum, SqlserverActuatorActionEnum, SqlserverBackupMode
from backend.flow.utils.sqlserver.payload_handler import PayloadHandler
from backend.flow.utils.sqlserver.sqlserver_bk_config import get_module_infos, get_sqlserver_config

logger = logging.getLogger("flow")


class SqlserverActPayload(PayloadHandler):
    @staticmethod
    def system_init_payload(**kwargs) -> dict:
        """
        系统初始化payload
        """

        return {
            "db_type": DBActuatorTypeEnum.Default.value,
            "action": SqlserverActuatorActionEnum.SysInit.value,
            "payload": PayloadHandler.get_init_system_account(),
        }

    def get_install_sqlserver_payload(self, **kwargs) -> dict:
        """
        拼接安装sqlserver的payload参数, 分别兼容集群申请、集群实例重建、集群实例添加单据的获取方式
        """
        # 获取对应DB模块的信息
        db_module = get_module_infos(
            bk_biz_id=int(self.global_data["bk_biz_id"]),
            db_module_id=int(self.global_data["db_module_id"]),
            cluster_type=self.global_data["cluster_type"],
        )
        # 获取安装包信息
        sqlserver_pkg = Package.get_latest_package(
            version=db_module["db_version"],
            pkg_type=MediumEnum.Sqlserver,
            db_type=DBType.Sqlserver,
        )
        # 获取版本对应的key,如果为空则报异常
        install_key = self.get_version_key(db_module["db_version"])
        if not install_key:
            raise Exception(_("找不到对应版本的install key"))

        # 拼接每个端口的配置
        init_sqlserver_config = {}

        for cluster in self.global_data["clusters"]:
            init_sqlserver_config[cluster["port"]] = get_sqlserver_config(
                bk_biz_id=int(self.global_data["bk_biz_id"]),
                immutable_domain=cluster["immutable_domain"],
                db_module_id=int(self.global_data["db_module_id"]),
                db_version=db_module["db_version"],
                cluster_type=self.global_data["cluster_type"],
            )

        install_ports = self.global_data["install_ports"]
        if not isinstance(install_ports, list) or len(init_sqlserver_config) == 0:
            raise Exception(_("传入的安装sqlserver端口列表为空或者非法值，请联系系统管理员: install_ports {}".format(install_ports)))

        return {
            "db_type": DBActuatorTypeEnum.Sqlserver.value,
            "action": SqlserverActuatorActionEnum.Deploy.value,
            "payload": {
                "general": {"runtime_account": PayloadHandler.get_create_sqlserver_account()},
                "extend": {
                    "host": kwargs["ips"][0]["ip"],
                    "pkg": sqlserver_pkg.name,
                    "pkg_md5": sqlserver_pkg.md5,
                    "charset": db_module["charset"],
                    "sqlserver_version": db_module["db_version"],
                    "install_key": install_key,
                    "max_remain_mem_gb": int(db_module["max_remain_mem_gb"]),
                    "buffer_percent": int(db_module["buffer_percent"]),
                    "ports": install_ports,
                    "sqlserver_configs": copy.deepcopy(init_sqlserver_config),
                },
            },
        }

    def get_execute_sql_payload(self, **kwargs) -> dict:
        """
        执行SQL文件的payload
        """
        return {
            "db_type": DBActuatorTypeEnum.Sqlserver.value,
            "action": SqlserverActuatorActionEnum.ExecSQLFiles.value,
            "payload": {
                "general": {"runtime_account": PayloadHandler.get_sqlserver_account()},
                "extend": {
                    "host": kwargs["ips"][0]["ip"],
                    "ports": self.global_data["ports"],
                    "charset_no": self.global_data["charset_no"],
                    "file_path": self.global_data["sql_target_path"],
                    "execute_objects": self.global_data["execute_objects"],
                },
            },
        }

    def get_backup_dbs_payload(self, **kwargs) -> dict:
        """
        执行数据库备份的payload
        """
        return {
            "db_type": DBActuatorTypeEnum.Sqlserver.value,
            "action": SqlserverActuatorActionEnum.BackupDBS.value,
            "payload": {
                "general": {"runtime_account": PayloadHandler.get_sqlserver_account()},
                "extend": {
                    "host": kwargs["ips"][0]["ip"],
                    "port": kwargs["custom_params"]["port"],
                    "backup_dbs": self.global_data["backup_dbs"],
                    "backup_type": self.global_data["backup_type"],
                    "backup_id": self.global_data["backup_id"],
                    "is_set_full_model": self.global_data.get("is_set_full_model", False),
                    "target_backup_dir": self.global_data.get("target_backup_dir", ""),
                },
            },
        }

    def get_backup_log_dbs_payload(self, **kwargs) -> dict:
        """
        执行数据库备份的payload, 日志备份专属，
        """
        return {
            "db_type": DBActuatorTypeEnum.Sqlserver.value,
            "action": SqlserverActuatorActionEnum.BackupDBS.value,
            "payload": {
                "general": {"runtime_account": PayloadHandler.get_sqlserver_account()},
                "extend": {
                    "host": kwargs["ips"][0]["ip"],
                    "port": kwargs["custom_params"]["port"],
                    "backup_dbs": self.global_data["backup_dbs"],
                    "backup_type": SqlserverBackupMode.LOG_BACKUP.value,
                    "backup_id": self.global_data["backup_id"],
                    "target_backup_dir": self.global_data.get("target_backup_dir", ""),
                },
            },
        }

    def get_rename_dbs_payload(self, **kwargs) -> dict:
        """
        执行数据库重命名的payload
        """
        return {
            "db_type": DBActuatorTypeEnum.Sqlserver.value,
            "action": SqlserverActuatorActionEnum.RenameDBS.value,
            "payload": {
                "general": {"runtime_account": PayloadHandler.get_sqlserver_account()},
                "extend": {
                    "host": kwargs["ips"][0]["ip"],
                    "port": self.global_data["port"],
                    "rename_dbs": self.global_data["rename_infos"],
                    "slaves": self.global_data["slaves"],
                    "sync_mode": self.global_data["sync_mode"],
                },
            },
        }

    def get_clean_dbs_payload(self, **kwargs) -> dict:
        """
        执行数据库重命名的payload
        """
        return {
            "db_type": DBActuatorTypeEnum.Sqlserver.value,
            "action": SqlserverActuatorActionEnum.CleanDBS.value,
            "payload": {
                "general": {"runtime_account": PayloadHandler.get_sqlserver_account()},
                "extend": {
                    "host": kwargs["ips"][0]["ip"],
                    "port": self.global_data["port"],
                    "clean_dbs": self.global_data["clean_dbs"],
                    "sync_mode": self.global_data["sync_mode"],
                    "clean_mode": self.global_data["clean_mode"],
                    "slaves": self.global_data["slaves"],
                    "clean_tables": self.global_data["clean_tables"],
                    "ignore_clean_tables": self.global_data["ignore_clean_tables"],
                },
            },
        }

    def get_switch_payload(self, **kwargs) -> dict:
        """
        执行互切或者故障转移的payload
        """
        return {
            "db_type": DBActuatorTypeEnum.Sqlserver.value,
            "action": SqlserverActuatorActionEnum.RoleSwitch.value,
            "payload": {
                "general": {"runtime_account": PayloadHandler.get_sqlserver_account()},
                "extend": {
                    "host": kwargs["ips"][0]["ip"],
                    "port": self.global_data["port"],
                    "master_host": self.global_data["master_host"],
                    "master_port": self.global_data["master_port"],
                    "force": self.global_data["force"],
                    "sync_mode": self.global_data["sync_mode"],
                },
            },
        }

    def get_check_abnormal_db_payload(self, **kwargs) -> dict:
        """
        检查实例是否存在非正常状态的数据
        """
        return {
            "db_type": DBActuatorTypeEnum.Sqlserver_check.value,
            "action": SqlserverActuatorActionEnum.CheckAbnormalDB.value,
            "payload": {
                "general": {"runtime_account": PayloadHandler.get_sqlserver_account()},
                "extend": {
                    "host": kwargs["ips"][0]["ip"],
                    "port": self.global_data["port"],
                },
            },
        }

    def get_check_inst_process_payload(self, **kwargs) -> dict:
        """
        检查实例是否存在业务连接
        """
        return {
            "db_type": DBActuatorTypeEnum.Sqlserver_check.value,
            "action": SqlserverActuatorActionEnum.CheckInstProcess.value,
            "payload": {
                "general": {"runtime_account": PayloadHandler.get_sqlserver_account()},
                "extend": {
                    "host": kwargs["ips"][0]["ip"],
                    "port": self.global_data["port"],
                },
            },
        }

    def get_clone_user_payload(self, **kwargs) -> dict:
        """
        实例之间克隆用户
        """
        return {
            "db_type": DBActuatorTypeEnum.Sqlserver.value,
            "action": SqlserverActuatorActionEnum.CloneLoginUsers.value,
            "payload": {
                "general": {"runtime_account": PayloadHandler.get_sqlserver_account()},
                "extend": {
                    "host": kwargs["ips"][0]["ip"],
                    "port": self.global_data["port"],
                    "source_host": self.global_data["source_host"],
                    "source_port": self.global_data["source_port"],
                },
            },
        }

    def get_clone_jobs_payload(self, **kwargs) -> dict:
        """
        实例之间克隆作业
        """
        return {
            "db_type": DBActuatorTypeEnum.Sqlserver.value,
            "action": SqlserverActuatorActionEnum.CloneJobs.value,
            "payload": {
                "general": {"runtime_account": PayloadHandler.get_sqlserver_account()},
                "extend": {
                    "host": kwargs["ips"][0]["ip"],
                    "port": self.global_data["port"],
                    "source_host": self.global_data["source_host"],
                    "source_port": self.global_data["source_port"],
                },
            },
        }

    def get_clone_linkserver_payload(self, **kwargs) -> dict:
        """
        实例之间克隆linkserver配置
        """
        return {
            "db_type": DBActuatorTypeEnum.Sqlserver.value,
            "action": SqlserverActuatorActionEnum.CloneLinkservers.value,
            "payload": {
                "general": {"runtime_account": PayloadHandler.get_sqlserver_account()},
                "extend": {
                    "host": kwargs["ips"][0]["ip"],
                    "port": self.global_data["port"],
                    "source_host": self.global_data["source_host"],
                    "source_port": self.global_data["source_port"],
                },
            },
        }

    @staticmethod
    def get_restore_full_dbs_payload(**kwargs) -> dict:
        """
        恢复全量备份的payload
        """
        return {
            "db_type": DBActuatorTypeEnum.Sqlserver.value,
            "action": SqlserverActuatorActionEnum.RestoreDBSForFull.value,
            "payload": {
                "general": {"runtime_account": PayloadHandler.get_sqlserver_account()},
                "extend": {
                    "host": kwargs["ips"][0]["ip"],
                    "port": kwargs["custom_params"]["port"],
                    "restore_infos": kwargs["custom_params"]["restore_infos"],
                    "restore_mode": kwargs["custom_params"].get("restore_mode", ""),
                },
            },
        }

    @staticmethod
    def get_restore_log_dbs_payload(**kwargs) -> dict:
        """
        恢复增量备份的payload
        """
        return {
            "db_type": DBActuatorTypeEnum.Sqlserver.value,
            "action": SqlserverActuatorActionEnum.RestoreDBSForLog.value,
            "payload": {
                "general": {"runtime_account": PayloadHandler.get_sqlserver_account()},
                "extend": {
                    "host": kwargs["ips"][0]["ip"],
                    "port": kwargs["custom_params"]["port"],
                    "restore_infos": kwargs["custom_params"]["restore_infos"],
                    "restore_mode": kwargs["custom_params"].get("restore_mode", ""),
                    "restore_time": kwargs["custom_params"].get("restore_time", ""),
                },
            },
        }

    def get_build_database_mirroring(self, **kwargs) -> dict:
        """
        建立数据库级别镜像关系的payload
        """
        return {
            "db_type": DBActuatorTypeEnum.Sqlserver.value,
            "action": SqlserverActuatorActionEnum.BuildDBMirroring.value,
            "payload": {
                "general": {"runtime_account": PayloadHandler.get_sqlserver_account()},
                "extend": {
                    "host": kwargs["ips"][0]["ip"],
                    "port": self.global_data["port"],
                    "dr_host": kwargs["custom_params"]["dr_host"],
                    "dr_port": kwargs["custom_params"]["dr_port"],
                    "dbs": kwargs["custom_params"]["dbs"],
                },
            },
        }

    def get_build_add_dbs_in_always_on(self, **kwargs) -> dict:
        """
        建立数据库加入always_on可用组的payload
        """
        return {
            "db_type": DBActuatorTypeEnum.Sqlserver.value,
            "action": SqlserverActuatorActionEnum.AddDBSInAlwaysOn.value,
            "payload": {
                "general": {"runtime_account": PayloadHandler.get_sqlserver_account()},
                "extend": {
                    "host": kwargs["ips"][0]["ip"],
                    "port": self.global_data["port"],
                    "add_slaves": kwargs["custom_params"]["add_slaves"],
                    "dbs": kwargs["custom_params"]["dbs"],
                },
            },
        }

    @staticmethod
    def get_build_always_on(**kwargs) -> dict:
        """
        建立实例加入always_on可用组的payload
        """
        return {
            "db_type": DBActuatorTypeEnum.Sqlserver.value,
            "action": SqlserverActuatorActionEnum.BuildAlwaysOn.value,
            "payload": {
                "general": {"runtime_account": PayloadHandler.get_sqlserver_account()},
                "extend": {
                    "host": kwargs["ips"][0]["ip"],
                    "port": kwargs["custom_params"]["port"],
                    "add_slaves": kwargs["custom_params"]["add_slaves"],
                    "group_name": kwargs["custom_params"]["group_name"],
                    "is_first": kwargs["custom_params"].get("is_first", True),
                },
            },
        }

    @staticmethod
    def get_init_machine_for_always_on(**kwargs) -> dict:
        """
        建立always_on可用组之前初始化机器的payload
        """
        return {
            "db_type": DBActuatorTypeEnum.Sqlserver.value,
            "action": SqlserverActuatorActionEnum.InitForAlwaysOn.value,
            "payload": {
                "general": {"runtime_account": PayloadHandler.get_sqlserver_account()},
                "extend": {
                    "host": kwargs["ips"][0]["ip"],
                    "port": kwargs["custom_params"]["port"],
                    "add_members": kwargs["custom_params"]["add_members"],
                    "is_first": kwargs["custom_params"].get("is_first", True),
                },
            },
        }

    def uninstall_sqlserver(self, **kwargs) -> dict:
        """
        卸载sqlserver的payload
        """
        return {
            "db_type": DBActuatorTypeEnum.Sqlserver.value,
            "action": SqlserverActuatorActionEnum.Uninstall.value,
            "payload": {
                "general": {"runtime_account": PayloadHandler.get_sqlserver_account()},
                "extend": {
                    "host": kwargs["ips"][0]["ip"],
                    "ports": self.global_data["custom_params"]["ports"],
                    "force": self.global_data.get("force", False),
                },
            },
        }

    @staticmethod
    def check_backup_file_is_in_local(**kwargs) -> dict:
        """
        移动备份文件
        """
        return {
            "db_type": DBActuatorTypeEnum.Sqlserver.value,
            "action": SqlserverActuatorActionEnum.MoveBackupFile.value,
            "payload": {
                "general": {"runtime_account": PayloadHandler.get_sqlserver_account()},
                "extend": {
                    "target_path": kwargs["custom_params"]["target_path"],
                    "file_list": kwargs["custom_params"]["file_list"],
                },
            },
        }
