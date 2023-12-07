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
import json
import logging

from django.utils.translation import ugettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.db_package.models import Package
from backend.flow.consts import (
    TBINLOGDUMPER_KAFKA_GLOBAL_CONF,
    TBINLOGDUMPER_KAFKA_TOPIC_CONF,
    DBActuatorActionEnum,
    DBActuatorTypeEnum,
    MediumEnum,
    TBinlogDumperProtocolType,
)
from backend.flow.engine.bamboo.scene.common.get_real_version import get_mysql_real_version
from backend.flow.engine.bamboo.scene.tbinlogdumper.common.exceptions import NormalTBinlogDumperFlowException
from backend.flow.utils.base.payload_handler import PayloadHandler

logger = logging.getLogger("flow")


class TBinlogDumperActPayload(object):
    @staticmethod
    def get_tbinlogdumper_config():
        """
        平台级别获取tbinlogdumper配置
        """
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": "0",
                "level_name": LevelName.PLAT,
                "level_value": "0",
                "conf_file": "latest",
                "conf_type": "tbinlogdumper",
                "namespace": "tendbha",
                "format": FormatType.MAP_LEVEL,
            }
        )

        return data["content"]

    def install_tbinlogdumper_payload(self, **kwargs):
        """
        安装tbinlogdumper实例，字符集是通过master实例获取
        """

        pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.TBinlogDumper)
        version_no = get_mysql_real_version(pkg.name)

        # 计算这次安装tbinlogdumper实例端口,并且计算每个端口安装配置
        mycnf_configs = {}
        dumper_configs = {}

        # 这里做了调整，传入payload需要的admin密码是tbinlogdumper的admin 密码
        account = copy.deepcopy(self.account)
        dumper_account = PayloadHandler.get_tbinlogdumper_account()
        account["admin_user"] = dumper_account["tbinlogdumper_admin_user"]
        account["admin_pwd"] = dumper_account["tbinlogdumper_admin_pwd"]

        for conf in self.ticket_data["add_conf_list"]:
            mycnf_configs[conf["port"]] = self.get_tbinlogdumper_config()
            dumper_configs[conf["port"]] = {
                "dumper_id": str(conf["area_name"]),
                "area_name": str(conf["area_name"]),
                "server_id": conf["server_id"],
                "protocol_type": conf["protocol_type"],
                "target_address": conf["target_address"],
                "target_port": int(conf["target_port"]),
                "l5_modid": conf.get("l5_modid", 0),
                "l5_cmdid": conf.get("l5_cmdid", 0),
                "kafka_user": conf.get("kafka_user", ""),
                "kafka_pwd": conf.get("kafka_pwd", ""),
            }
            # 分场景添加对应启动参数
            mycnf_configs[conf["port"]]["mysqld"]["replicate_wild_do_table"] = ",".join(conf["repl_tables"])
            mycnf_configs[conf["port"]]["mysqld"]["redis_protocol_type"] = conf["protocol_type"]
            if conf["protocol_type"] == TBinlogDumperProtocolType.KAFKA.value:
                mycnf_configs[conf["port"]]["mysqld"]["redis_server_address"] = conf["target_address"]
                mycnf_configs[conf["port"]]["mysqld"]["redis_server_port"] = str(conf["target_port"])
                global_config = copy.deepcopy(TBINLOGDUMPER_KAFKA_GLOBAL_CONF)
                global_config["sasl.username"] = conf["kafka_user"]
                global_config["sasl.password"] = conf["kafka_pwd"]

                mycnf_configs[conf["port"]]["mysqld"]["redis_kafka_global_config"] = json.dumps(global_config)
                mycnf_configs[conf["port"]]["mysqld"]["redis_kafka_topic_config"] = json.dumps(
                    TBINLOGDUMPER_KAFKA_TOPIC_CONF
                )

            elif conf["protocol_type"] == TBinlogDumperProtocolType.L5_AGENT.value:
                mycnf_configs[conf["port"]]["mysqld"]["redis_l5_modid"] = str(conf["l5_modid"])
                mycnf_configs[conf["port"]]["mysqld"]["redis_l5_cmdid"] = str(conf["l5_cmdid"])
            elif conf["protocol_type"] == TBinlogDumperProtocolType.TCP_IP.value:
                mycnf_configs[conf["port"]]["mysqld"]["redis_server_address"] = conf["target_address"]
                mycnf_configs[conf["port"]]["mysqld"]["redis_server_port"] = str(conf["target_port"])
            else:
                raise NormalTBinlogDumperFlowException(
                    message=_("非法协议，请联系系统管理员：protocol_type:{}".format(conf["protocol_type"]))
                )

        drs_account, dbha_account = self.get_super_account()
        return {
            "db_type": DBActuatorTypeEnum.TBinlogDumper.value,
            "action": DBActuatorActionEnum.Deploy.value,
            "payload": {
                "general": {"runtime_account": account},
                "extend": {
                    "host": kwargs["ip"],
                    "pkg": pkg.name,
                    "pkg_md5": pkg.md5,
                    "mysql_version": version_no,
                    "charset": self.ticket_data["charset"],
                    "inst_mem": 0,
                    "ports": [conf["port"] for conf in self.ticket_data["add_conf_list"]],
                    "super_account": drs_account,
                    "dbha_account": dbha_account,
                    "mycnf_configs": mycnf_configs,
                    "dumper_configs": dumper_configs,
                },
            },
        }

    def uninstall_tbinlogdumper_payload(self, **kwargs) -> dict:
        """
        卸载tbinlogdumper进程的payload参数
        """
        # 这里做了调整，传入payload需要的admin密码是tbinlogdumper的admin 密码
        account = copy.deepcopy(self.account)
        dumper_account = PayloadHandler.get_tbinlogdumper_account()
        account["admin_user"] = dumper_account["tbinlogdumper_admin_user"]
        account["admin_pwd"] = dumper_account["tbinlogdumper_admin_pwd"]
        return {
            "db_type": DBActuatorTypeEnum.TBinlogDumper.value,
            "action": DBActuatorActionEnum.UnInstall.value,
            "payload": {
                "general": {"runtime_account": account},
                "extend": {
                    "host": kwargs["ip"],
                    "force": True,
                    "ports": self.cluster["listen_ports"],
                },
            },
        }

    def tbinlogdumper_sync_data_payload(self, **kwargs):
        """
        TBinlogDumper建立数据同步
        """
        account = copy.deepcopy(self.account)
        dumper_account = PayloadHandler.get_tbinlogdumper_account()
        account["admin_user"] = dumper_account["tbinlogdumper_admin_user"]
        account["admin_pwd"] = dumper_account["tbinlogdumper_admin_pwd"]
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.ChangeMaster.value,
            "payload": {
                "general": {"runtime_account": account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["listen_port"],
                    "master_host": self.cluster["master_ip"],
                    "master_port": self.cluster["master_port"],
                    "is_gtid": False,
                    "max_tolerate_delay": 0,
                    "force": False,
                    "bin_file": self.cluster["bin_file"],
                    "bin_position": self.cluster["bin_position"],
                },
            },
        }

    def tbinlogdumper_backup_demand_payload(self, **kwargs):
        return {
            "db_type": DBActuatorTypeEnum.TBinlogDumper.value,
            "action": DBActuatorActionEnum.MySQLBackupDemand.value,
            "payload": {
                "general": {"runtime_account": {**self.account, **PayloadHandler.get_tbinlogdumper_account()}},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.ticket_data["port"],
                    "role": self.ticket_data["role"],
                    "backup_type": "logical",
                    "backup_gsd": ["data"],
                    "regex": self.ticket_data["db_table_filter_regex"],
                    "backup_id": self.ticket_data["backup_id"].__str__(),
                    "bill_id": str(self.ticket_data["uid"]),
                    "custom_backup_dir": "tbinlogdumper",
                },
            },
        }

    def tbinlogdumper_restore_payload(self, **kwargs):
        """
        tbinlogdumper 恢复备份数据（不包括表结构）
        """
        cluster = Cluster.objects.get(id=self.ticket_data["cluster_id"])
        master = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)
        index_file = ""
        for result in kwargs["trans_data"]["backup_info"]["report_result"]:
            if result["file_type"] == "index":
                index_file = result["file_name"]
                break

        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.RestoreSlave.value,
            "payload": {
                "general": {"runtime_account": {**self.account, **PayloadHandler.get_tbinlogdumper_account()}},
                "extend": {
                    "work_dir": kwargs["trans_data"]["backup_info"]["backup_dir"],
                    "backup_dir": kwargs["trans_data"]["backup_info"]["backup_dir"],
                    "backup_files": {
                        "index": [index_file],
                    },
                    "tgt_instance": {
                        "host": kwargs["ip"],
                        "port": self.ticket_data["add_tbinlogdumper_conf"]["port"],
                        "user": self.account["tbinlogdumper_admin_user"],
                        "pwd": self.account["tbinlogdumper_admin_pwd"],
                        "socket": None,
                        "charset": "",
                        "options": "",
                    },
                    "src_instance": {"host": master.machine.ip, "port": master.port},
                    "change_master": True,
                    "work_id": "",
                },
            },
        }

    def tbinlogdumper_load_schema_payload(self, **kwargs):
        """
        TbinlogDumper导入表结构
        """
        cluster = Cluster.objects.get(id=self.ticket_data["cluster_id"])
        master = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)
        return {
            "db_type": DBActuatorTypeEnum.TBinlogDumper.value,
            "action": DBActuatorActionEnum.DumpSchema.value,
            "payload": {
                "general": {"runtime_account": {**self.account, **PayloadHandler.get_tbinlogdumper_account()}},
                "extend": {
                    "host": kwargs["ip"],
                    "port": master.port,
                    "tbinlogdumper_port": self.ticket_data["add_tbinlogdumper_conf"]["port"],
                    "charset": "default",
                },
            },
        }

    def tbinlogdumper_change_master_payload(self, **kwargs) -> dict:
        """
        拼接同步主从的payload参数(在slave节点执行), 获取master的位点信息的场景通过上下文获取
        """
        # 这里做了调整，传入payload需要的admin密码是tbinlogdumper的admin 密码
        account = copy.deepcopy(self.account)
        dumper_account = PayloadHandler.get_tbinlogdumper_account()
        account["admin_user"] = dumper_account["tbinlogdumper_admin_user"]
        account["admin_pwd"] = dumper_account["tbinlogdumper_admin_pwd"]
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.ChangeMaster.value,
            "payload": {
                "general": {"runtime_account": account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster.get("slave_port", 0),
                    "master_host": self.cluster["new_master_ip"],
                    "master_port": self.cluster.get("master_port", 0),
                    "is_gtid": False,
                    "max_tolerate_delay": 0,
                    "force": False,
                    "bin_file": kwargs["trans_data"]["master_ip_sync_info"]["bin_file"],
                    "bin_position": kwargs["trans_data"]["master_ip_sync_info"]["bin_position"],
                },
            },
        }
