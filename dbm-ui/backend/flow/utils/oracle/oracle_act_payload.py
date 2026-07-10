import json
import logging

from backend.configuration.constants import DBType
from backend.core.consts import BK_PKG_INSTALL_PATH
from backend.db_package.models import Package
from backend.flow import consts
from backend.flow.consts import DBActuatorTypeEnum, MediumEnum, OracleActuatorActionEnum, UserName
from backend.flow.utils.oracle.oracle_context_dataclass import AddSlaveContext
from backend.flow.utils.oracle.oracle_password import OraclePassword

logger = logging.getLogger("flow")


class OracleActPayload(object):
    """
    定义Oracle不同的执行类型，拼接不同的payload参数，对应不同的dict结构体
    """

    def __init__(self, ticket_data: dict, cluster: dict):
        self.oracle_pkg = None
        self.patch_list = []
        self.ticket_data = ticket_data
        self.cluster = cluster

    @staticmethod
    def _get_configs(trans_data: dict, path_var_name: str) -> dict:
        """
        获取集群配置信息
        """
        configs = trans_data[path_var_name]
        print(f"configs: {configs}")
        if isinstance(configs, str):
            configs = json.loads(configs)
            print(f"configs: {configs}")
        return configs

    def get_master_dataguard_config_payload(self, **kwargs) -> dict:
        """
        主从配置初始化
        """
        configs = self._get_configs(kwargs["trans_data"], AddSlaveContext.get_configs_var_name())
        return {
            "db_type": DBActuatorTypeEnum.Default.value,
            "action": OracleActuatorActionEnum.MasterDataguardConfig.value,
            "payload": {
                "log_archive_config": configs["log_archive_config"],
                "available_number": configs["available_number"],
                "slave_host": self.ticket_data["new_slave"]["ip"],
                "oracle_sid": configs["oracle_sid"],
                "slave_db_unique_name": configs["slave_db_unique_name"],
            },
        }

    def get_sysinit_payload(self, **kwargs) -> dict:
        """
        系统配置初始化
        """
        configs = self._get_configs(kwargs["trans_data"], AddSlaveContext.get_configs_var_name())
        return {
            "db_type": DBActuatorTypeEnum.Default.value,
            "action": OracleActuatorActionEnum.SysinitOracle.value,
            "payload": {
                "account": OraclePassword.get_sys_account(UserName.OS_ORACLE.value),
                "oracle_sid": configs["oracle_sid"],
                "cf_ssn": configs["cf_ssn"],
                "cf_schema": configs["cf_schema"],
            },
        }

    def get_install_trans_payload(self, **kwargs) -> dict:
        """
        部署oracle软件
        """
        self.oracle_pkg = Package.get_latest_package(
            version=self.ticket_data["db_version"], pkg_type=MediumEnum.Oracle, db_type=DBType.Oracle.value
        )
        for patch in self.ticket_data["patch_list"]:
            self.patch_list.append(
                Package.get_latest_package(version=patch, pkg_type=MediumEnum.Patch, db_type=DBType.Oracle.value)
            )
        path = self._get_configs(kwargs["trans_data"], AddSlaveContext.get_path_var_name())
        return {
            "db_type": DBActuatorTypeEnum.Oracle.value,
            "action": OracleActuatorActionEnum.Install.value,
            "payload": {
                "plain_dirs": path["plain_dirs"],
                "link_plans": path["link_plans"],
                "oracle_pkg": {
                    "name": self.oracle_pkg.name,
                    "md5": self.oracle_pkg.md5,
                },
                "patch_list": [
                    {
                        "name": patch.name,
                        "md5": patch.md5,
                    }
                    for patch in self.patch_list
                ],
            },
        }

    def get_install_instance_trans_payload(self, **kwargs) -> dict:
        """
        部署oracle实例
        """
        configs = self._get_configs(kwargs["trans_data"], AddSlaveContext.get_configs_var_name())
        return {
            "db_type": DBActuatorTypeEnum.Oracle.value,
            "action": OracleActuatorActionEnum.InstallInstanceFromExisting.value,
            "payload": {
                "log_archive_config": configs["log_archive_config"],
                "oracle_sid": configs["oracle_sid"],
                "cf_ssn": configs["cf_ssn"],
                "cf_schema": configs["cf_schema"],
                "pfile": "{}/{}.pfile.ora".format(BK_PKG_INSTALL_PATH, self.ticket_data["uid"]),
                "orapw": "{}/{}.orapw.ora".format(BK_PKG_INSTALL_PATH, self.ticket_data["uid"]),
                "master_host": self.ticket_data["old_node"]["ip"],
                "slave_host": kwargs["ip"],
                "master_db_unique_name": configs["master_db_unique_name"],
                "slave_db_unique_name": configs["slave_db_unique_name"],
            },
        }

    def get_install_instance_via_cascading_trans_payload(self, **kwargs) -> dict:
        """
        部署oracle实例，通过级联方式搭建
        """
        configs = self._get_configs(kwargs["trans_data"], AddSlaveContext.get_configs_var_name())
        master_configs = self._get_configs(kwargs["trans_data"], AddSlaveContext.get_master_configs_var_name())
        return {
            "db_type": DBActuatorTypeEnum.Oracle.value,
            "action": OracleActuatorActionEnum.InstallInstanceFromExisting.value,
            "payload": {
                "log_archive_config": configs["log_archive_config"],
                "oracle_sid": configs["oracle_sid"],
                "cf_ssn": configs["cf_ssn"],
                "cf_schema": configs["cf_schema"],
                "pfile": "{}/{}.pfile.ora".format(BK_PKG_INSTALL_PATH, self.ticket_data["uid"]),
                "orapw": "{}/{}.orapw.ora".format(BK_PKG_INSTALL_PATH, self.ticket_data["uid"]),
                "master_host": self.ticket_data["old_node"]["ip"],
                "slave_host": kwargs["ip"],
                "master_db_unique_name": configs["master_db_unique_name"],
                "slave_db_unique_name": configs["slave_db_unique_name"],
                "old_master_host": self.ticket_data["old_master"]["ip"],
                "old_master_db_unique_name": master_configs["master_db_unique_name"],
            },
        }

    def get_config_data_guard_via_statistic_payload(self, **kwargs) -> dict:
        """
        配置data guard，使用静态监听
        """
        configs = self._get_configs(kwargs["trans_data"], AddSlaveContext.get_configs_var_name())
        return {
            "db_type": DBActuatorTypeEnum.Oracle.value,
            "action": OracleActuatorActionEnum.ConfigDataguard.value,
            "payload": {
                "log_archive_config": configs["log_archive_config"],
                "available_number": configs["available_number"],
                "slave_host": self.ticket_data["new_slave"]["ip"],
                "slave_port": consts.ManagerDefaultPort.ORACLE_STATISTIC_PORT.value,
                "oracle_sid": configs["oracle_sid"],
                "slave_db_unique_name": configs["slave_db_unique_name"],
                "real_master": configs["real_master"],
                "log_archive_dest_state": "defer",
            },
        }

    def get_config_data_guard_payload(self, **kwargs) -> dict:
        """
        配置data guard
        """
        configs = self._get_configs(kwargs["trans_data"], AddSlaveContext.get_master_configs_var_name())
        return {
            "db_type": DBActuatorTypeEnum.Oracle.value,
            "action": OracleActuatorActionEnum.ConfigDataguard.value,
            "payload": {
                "log_archive_config": configs["log_archive_config"],
                "available_number": configs["available_number"],
                "slave_host": self.ticket_data["new_slave"]["ip"],
                "slave_port": consts.ManagerDefaultPort.ORACLE_PORT.value,
                "oracle_sid": configs["oracle_sid"],
                "slave_db_unique_name": configs["slave_db_unique_name"],
                "real_master": configs["real_master"],
                "log_archive_dest_state": "enable",
            },
        }

    def get_config_payload(self, **kwargs) -> dict:
        """
        获取配置
        """
        return {
            "db_type": DBActuatorTypeEnum.Oracle.value,
            "action": OracleActuatorActionEnum.GetConfig.value,
            "payload": {"slave_host": self.ticket_data["new_slave"]["ip"]},
        }

    def get_pfile_payload(self, **kwargs) -> dict:
        """
        获取Pfile
        """
        return {
            "db_type": DBActuatorTypeEnum.Oracle.value,
            "action": OracleActuatorActionEnum.GetPfile.value,
            "payload": {},
        }

    def get_start_listener_payload(self, **kwargs) -> dict:
        """
        启动监听器
        """
        return {
            "db_type": DBActuatorTypeEnum.Oracle.value,
            "action": OracleActuatorActionEnum.StartListener.value,
            "payload": {},
        }

    def get_password_file_payload(self, **kwargs) -> dict:
        """
        获取密码文件
        """
        return {
            "db_type": DBActuatorTypeEnum.Oracle.value,
            "action": OracleActuatorActionEnum.GetPasswordFile.value,
            "payload": {},
        }

    def get_symbolic_link_payload(self, **kwargs) -> dict:
        """
        获取软链接配置
        """
        configs = self._get_configs(kwargs["trans_data"], AddSlaveContext.get_configs_var_name())
        return {
            "db_type": DBActuatorTypeEnum.Oracle.value,
            "action": OracleActuatorActionEnum.GetSymbolicLink.value,
            "payload": {"pathes": configs["pathes"]},
        }

    def get_rman_duplicate_payload(self, **kwargs) -> dict:
        """
        rman duplicate 拷贝数据构造备库
        """
        configs = self._get_configs(kwargs["trans_data"], AddSlaveContext.get_configs_var_name())
        return {
            "db_type": DBActuatorTypeEnum.Oracle.value,
            "action": OracleActuatorActionEnum.RMANDuplicate.value,
            "payload": {
                "available_number": configs["available_number"],
                "master_db_unique_name": configs["master_db_unique_name"],
                "slave_db_unique_name": configs["slave_db_unique_name"],
                "real_master": configs["real_master"],
                "account": OraclePassword.get_sys_account(UserName.ORACLE_SYS),
            },
        }

    def get_switch_log_payload(self, **kwargs) -> dict:
        """
        切换日志
        """
        return {
            "db_type": DBActuatorTypeEnum.Oracle.value,
            "action": OracleActuatorActionEnum.SwitchLog.value,
            "payload": {},
        }

    def get_shutdown_payload(self, **kwargs) -> dict:
        """
        关闭实例与监听
        """
        return {
            "db_type": DBActuatorTypeEnum.Oracle.value,
            "action": OracleActuatorActionEnum.Shutdown.value,
            "payload": {},
        }

    def get_real_time_apply_payload(self, **kwargs) -> dict:
        """
        实时应用
        """
        configs = self._get_configs(kwargs["trans_data"], AddSlaveContext.get_configs_var_name())
        return {
            "db_type": DBActuatorTypeEnum.Oracle.value,
            "action": OracleActuatorActionEnum.RealTimeApply.value,
            "payload": {
                "redo_log_group_num": configs["redo_log_group_num"],
                "redo_log_max_size": configs["redo_log_max_size"],
            },
        }

    def get_real_master_payload(self, **kwargs) -> dict:
        """
        是否为真实主节点
        """
        return {
            "db_type": DBActuatorTypeEnum.Oracle.value,
            "action": OracleActuatorActionEnum.RealMaster.value,
            "payload": {},
        }

    def get_check_sync_status_payload(self, **kwargs) -> dict:
        """
        检查同步状态
        """
        return {
            "db_type": DBActuatorTypeEnum.Oracle.value,
            "action": OracleActuatorActionEnum.CheckSyncStatus.value,
            "payload": {},
        }

    def get_pause_sync_payload(self, **kwargs) -> dict:
        """
        暂停同步
        """
        configs = self._get_configs(kwargs["trans_data"], AddSlaveContext.get_configs_var_name())
        return {
            "db_type": DBActuatorTypeEnum.Oracle.value,
            "action": OracleActuatorActionEnum.PauseSync.value,
            "payload": {
                "available_number": configs["available_number"],
                "master_db_unique_name": configs["master_db_unique_name"],
                "account": OraclePassword.get_sys_account(UserName.ORACLE_SYS),
            },
        }
