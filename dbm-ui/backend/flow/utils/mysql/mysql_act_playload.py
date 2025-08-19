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
import copy
import json
import logging
import os
from collections import defaultdict
from typing import Any, List

from django.conf import settings
from django.utils.translation import ugettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName, ReqType
from backend.constants import IP_PORT_DIVIDER
from backend.core.consts import BK_PKG_INSTALL_PATH
from backend.core.encrypt.constants import AsymmetricCipherConfigType
from backend.core.encrypt.handlers import AsymmetricHandler
from backend.db_meta.enums import InstanceInnerRole, MachineType, TenDBClusterSpiderRole
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, Machine, StorageInstanceTuple
from backend.db_package.models import Package
from backend.db_proxy.reverse_api.common.impl import list_nginx_addrs
from backend.db_services.mysql.sql_import.constants import BKREPO_DBCONSOLE_DUMPFILE_PATH, BKREPO_SQLFILE_PATH
from backend.flow.consts import (
    CHECKSUM_DB,
    ROLLBACK_DB_TAIL,
    STAGE_DB_HEADER,
    SYSTEM_DBS,
    TDBCTL_USER,
    CHECKSUM_TABlE_PREFIX,
    ConfigTypeEnum,
    DataSyncSource,
    DBActuatorActionEnum,
    DBActuatorTypeEnum,
    MediumEnum,
    MySQLBackupFileTagEnum,
    MySQLBackupTypeEnum,
    MysqlChangeMasterType,
    MysqlVersionToDBBackupForMap,
)
from backend.flow.engine.bamboo.scene.common.get_real_version import get_mysql_real_version, get_spider_real_version
from backend.flow.engine.bamboo.scene.spider.common.exceptions import TendbGetBackupInfoFailedException
from backend.flow.utils.base.bkrepo import get_bk_repo_url
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.mysql.proxy_act_payload import ProxyActPayload
from backend.flow.utils.tbinlogdumper.tbinlogdumper_act_payload import TBinlogDumperActPayload
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class MysqlActPayload(PayloadHandler, ProxyActPayload, TBinlogDumperActPayload):
    """
    定义mysql不同执行类型，拼接不同的payload参数，对应不同的dict结构体。
    todo 后续要优化这块代码，因为类太大，建议按照场景拆分，然后继承，例如TBinlogDumperActPayload继承TBinlogDumper相关的方法
    todo 比如spider场景拆出来、公共部分的拆出来等
    """

    def __get_mysql_config(self, immutable_domain, db_version) -> Any:
        """
        生成并获取mysql实例配置,集群级别配置
        spider/spider-ctl/spider-mysql实例统一用这里拿去配置
        """
        if db_version != "Tdbctl" and self.db_module_id == 0:
            # 这里做一层判断，对传入的db_module_id值判断，非Tdbctl实例，传入的db_module_id必须是合理且存在的值，否则抛出异常
            raise Exception(
                f"The db_module_id parameter is illegal, db_module_id:{self.db_module_id}, db_version:{db_version}"
            )
        data = DBConfigApi.get_or_generate_instance_config(
            {
                "bk_biz_id": str(self.ticket_data["bk_biz_id"]),
                "level_name": LevelName.CLUSTER,
                "level_value": immutable_domain,
                "level_info": {"module": str(self.db_module_id)},
                "conf_file": db_version,
                "conf_type": ConfigTypeEnum.DBConf,
                "namespace": self.cluster_type,
                "format": FormatType.MAP_LEVEL,
                "method": ReqType.GENERATE_AND_PUBLISH,
            }
        )
        return data["content"]

    def __get_version_and_charset(self, db_module_id) -> Any:
        """获取版本号和字符集信息"""
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(self.ticket_data["bk_biz_id"]),
                "level_name": LevelName.MODULE,
                "level_value": str(db_module_id),
                "conf_file": "deploy_info",
                "conf_type": "deploy",
                "namespace": self.cluster_type,
                "format": FormatType.MAP,
            }
        )["content"]
        logger.info(f"Get mysql version,charset,engine from dbconfig: {data}")
        return data["charset"], data["db_version"]

    def __get_mysql_rotatebinlog_config(self) -> dict:
        """
        远程获取rotate_binlog配置
        """
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(self.ticket_data["bk_biz_id"]),
                "level_name": LevelName.MODULE,
                "level_value": str(self.db_module_id),
                "conf_file": "binlog_rotate.yaml",
                "conf_type": "backup",
                "namespace": self.cluster_type,
                "format": FormatType.MAP_LEVEL,
            }
        )
        return data["content"]

    def get_sys_init_payload(self, **kwargs) -> dict:
        """
        拼接初始化机器的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Default.value,
            "action": DBActuatorActionEnum.Sysinit.value,
            "payload": {
                "user": self.account["os_mysql_user"],
                "pwd": self.account["os_mysql_pwd"],
                "nginx_addrs": list_nginx_addrs(bk_cloud_id=self.bk_cloud_id),
            },
        }

    def deal_with_upgrade_to_mysql57(self, cfg: dict) -> dict:
        del_keys = [
            "secure_auth",
            "innodb_additional_mem_pool_size",
            "innodb_create_use_gcs_real_format",
            "thread_concurrency",
            "storage_engine",
            "old_passwords",
            "innodb_file_io_threads",
        ]
        for key in del_keys:
            if key in cfg["mysqld"]:
                del cfg["mysqld"][key]

        # 需要rename key 的配置
        if "thread_cache" in cfg["mysqld"]:
            cfg["mysqld"]["thread_cache_size"] = cfg["mysqld"]["thread_cache"]
            del cfg["mysqld"]["thread_cache"]
        if "key_buffer" in cfg["mysqld"]:
            cfg["mysqld"]["key_buffer_size"] = cfg["mysqld"]["key_buffer"]
            del cfg["mysqld"]["key_buffer"]
        if "log_warnings" in cfg["mysqld"]:
            cfg["mysqld"]["log_error_verbosity"] = "1"
            del cfg["mysqld"]["log_warnings"]

        return cfg

    def deal_with_upgrade_to_mysql80(self, is_community: bool, cfg: dict) -> dict:
        """
        处理不同介质的之间的mysql配置
        """
        if "log_warnings" in cfg["mysqld"]:
            value = cfg["mysqld"]["log_warnings"]
            if value == "0":
                cfg["mysqld"]["log_error_verbosity"] = "1"
            elif value == "1":
                cfg["mysqld"]["log_error_verbosity"] = "2"
            else:
                cfg["mysqld"]["log_error_verbosity"] = "3"
            del cfg["mysqld"]["log_warnings"]
        # mysql8.0 无法识别这些参数
        for key in [
            "innodb_file_format",
            "query_cache_size",
            "query_cache_type",
            "show_compatibility_56",
            "query_response_time_stats",
            "userstat",
        ]:
            if key in cfg["mysqld"]:
                del cfg["mysqld"][key]
        if "thread_handling" in cfg["mysqld"]:
            val = cfg["mysqld"]["thread_handling"]
            # thread_handling = 2 是tmysql参数。社区版本和txsql 都不能识别
            if val == "1":
                cfg["mysqld"]["thread_handling"] = "no-threads"
            elif val == "2":
                cfg["mysqld"]["thread_handling"] = "one-thread-per-connection"
            elif val == "3":
                cfg["mysqld"]["thread_handling"] = "loaded-dynamically"

        # 这里应该是社区版本等非Tendb数据库的版本需要处理的参数
        # 介质管理暂未记录介质来源属性
        if is_community:
            for key in [
                "log_bin_compress",
                "relay_log_uncompress",
                "blob_compressed",
                "innodb_min_blob_compress_length",
                "innodb_table_drop_mode",
                "read_binlog_speed_limit",
                "datetime_precision_use_v1",
            ]:
                if key in cfg["mysqld"]:
                    loose_key = "loose_" + key
                    cfg["mysqld"][loose_key] = cfg["mysqld"][key]
                    del cfg["mysqld"][key]
        return cfg

    def deal_mysql_config(self, db_version: str, origin_configs: dict, init_configs: dict) -> dict:
        """
        处理不同介质的之间的mysql配置
        """
        cfg = copy.deepcopy(init_configs)
        cfg["mysqld"].update(origin_configs)
        if db_version >= "5.7.0":
            cfg = self.deal_with_upgrade_to_mysql57(cfg)
        is_community = False
        if db_version >= "8.0.0":
            # 这里应该是社区版本等非Tendb数据库的版本需要处理的参数
            # 介质管理暂未记录介质来源属性
            if db_version >= "8.0.30":
                is_community = True
            cfg = self.deal_with_upgrade_to_mysql80(is_community=is_community, cfg=cfg)

        return cfg

    def get_engine_from_mysql_config(self, mysql_configs: dict) -> str:
        for config in mysql_configs.values():
            if "default_storage_engine" in config["mysqld"]:
                return config["mysqld"]["default_storage_engine"]
            if "default-storage-engine" in config["mysqld"]:
                return config["mysqld"]["default-storage-engine"]
        return "innodb"

    def get_install_mysql_payload(self, **kwargs) -> dict:
        """
        拼接安装MySQL的payload参数, 分别兼容集群申请、集群实例重建、集群实例添加单据的获取方式
        由于集群实例重建或者添加单据是不知道 需要部署的版本号以及字符集，需要通过接口获取
        """
        logger.debug("cluster info ", self.cluster)
        init_mysql_config = {}
        engine = "innodb"
        if self.ticket_data.get("charset") and self.ticket_data.get("db_version"):
            # 如果单据传入有字符集和版本号，则以单据为主：
            charset, db_version = self.ticket_data.get("charset"), self.ticket_data.get("db_version")
        else:
            # 如果没有传入，则通过db_config获取
            charset, db_version = self.__get_version_and_charset(db_module_id=self.db_module_id)

        for cluster in self.ticket_data["clusters"]:
            init_mysql_config[cluster["mysql_port"]] = self.__get_mysql_config(
                immutable_domain=cluster["master"], db_version=db_version
            )
        mysql_pkg = Package.get_latest_package(version=db_version, pkg_type=MediumEnum.MySQL)
        if self.cluster.get("pkg_id"):
            pkg_id = self.cluster["pkg_id"]
            if pkg_id > 0:
                mysql_pkg = Package.objects.get(id=pkg_id, pkg_type=MediumEnum.MySQL)
        version_no = get_mysql_real_version(mysql_pkg.name)
        install_mysql_ports = self.ticket_data.get("mysql_ports")
        mysql_config = {}
        if not isinstance(install_mysql_ports, list) or len(install_mysql_ports) == 0:
            logger.error(_("传入的安装mysql端口列表为空或者非法值，请联系系统管理员"))
            return {}
        # todo 指定实例的配置参数
        old_configs = self.cluster.get("old_instance_configs", {})
        logger.debug("source instance config:", old_configs)
        for port in install_mysql_ports:
            mysql_config[port] = copy.deepcopy(init_mysql_config[port])
            port_str = str(port)
            if port_str in old_configs.keys():
                mysql_config[port] = self.deal_mysql_config(
                    db_version=version_no, init_configs=mysql_config[port], origin_configs=old_configs[port_str]
                )
        logger.debug("install  config:", mysql_config)
        engine = self.get_engine_from_mysql_config(mysql_configs=mysql_config)
        logger.debug("engine is ", engine)
        drs_account, dbha_account = self.get_super_account()

        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.Deploy.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "pkg": mysql_pkg.name,
                    "pkg_md5": mysql_pkg.md5,
                    "mysql_version": version_no,
                    "charset": charset,
                    "engine": engine,
                    "inst_mem": 0,
                    "ports": self.ticket_data.get("mysql_ports", []),
                    "super_account": drs_account,
                    "dbha_account": dbha_account,
                    "webconsolers_account": self.get_webconsolers_account(),
                    "partition_yw_account": self.get_partition_yw_account(),
                    "mycnf_configs": copy.deepcopy(mysql_config),
                },
            },
        }

    def get_install_spider_payload(self, **kwargs):
        """
        拼接spider节点安装的payload
        todo 后续需要考虑兼容字符集和版本信息的多获取路径
        """

        spider_charset = self.ticket_data["spider_charset"]
        spider_version = self.ticket_data["spider_version"]
        # 如果指定安装包
        if self.cluster.get("pkg_id"):
            pkg_id = self.cluster["pkg_id"]
            spider_pkg = Package.objects.get(id=pkg_id, pkg_type=MediumEnum.Spider)
        else:
            spider_pkg = Package.get_latest_package(version=spider_version, pkg_type=MediumEnum.Spider)
        version_no = get_spider_real_version(spider_pkg.name)

        install_spider_ports = self.ticket_data.get("spider_ports")
        spider_config = {}
        spider_auto_incr_mode_map = {}
        if not isinstance(install_spider_ports, list) or len(install_spider_ports) == 0:
            raise Exception(_("传入的安装spider端口列表为空或者非法值，请联系系统管理员"))

        for port in install_spider_ports:
            spider_config[port] = copy.deepcopy(
                self.__get_mysql_config(immutable_domain=self.cluster["immutable_domain"], db_version=spider_version)
            )
            spider_auto_incr_mode_map[port] = self.cluster["auto_incr_value"]

        drs_account, dbha_account = self.get_super_account()

        return {
            "db_type": DBActuatorTypeEnum.Spider.value,
            "action": DBActuatorActionEnum.Deploy.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "pkg": spider_pkg.name,
                    "pkg_md5": spider_pkg.md5,
                    "mysql_version": version_no,
                    "charset": spider_charset,
                    "inst_mem": 0,
                    "ports": self.ticket_data["spider_ports"],
                    "super_account": drs_account,
                    "dbha_account": dbha_account,
                    "webconsolers_account": self.get_webconsolers_account(),
                    "partition_yw_account": self.get_partition_yw_account(),
                    "mycnf_configs": copy.deepcopy(spider_config),
                    "spider_auto_incr_mode_map": spider_auto_incr_mode_map,
                },
            },
        }

    def get_install_slave_spider_payload(self, **kwargs):
        """
        拼接spider_slave 安装时需要的参数
        """
        content = self.get_install_spider_payload(**kwargs)
        # 允许 spider 本地 mysqld 可写
        # 保留 spider 不能写 remote
        slave_config = {"spider_read_only_mode": "1"}
        # 拼装spider_slave需要的只读参数
        for key in content["payload"]["extend"]["mycnf_configs"]:
            content["payload"]["extend"]["mycnf_configs"][key]["mysqld"].update(slave_config)
        return content

    def get_append_deploy_ctl_payload(self, **kwargs):
        """
        拼接spider-ctl节点添加单实例的payload
        """
        ctl_charset = self.cluster["ctl_charset"]

        ctl_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.tdbCtl)
        version_no = get_mysql_real_version(ctl_pkg.name)

        drs_account, dbha_account = self.get_super_account()
        return {
            "db_type": DBActuatorTypeEnum.SpiderCtl.value,
            "action": DBActuatorActionEnum.AppendDeploy.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "pkg": ctl_pkg.name,
                    "pkg_md5": ctl_pkg.md5,
                    "mysql_version": version_no,
                    "charset": ctl_charset,
                    "inst_mem": 0,
                    "ports": [self.cluster["ctl_port"]],
                    "super_account": drs_account,
                    "dbha_account": dbha_account,
                    "webconsolers_account": self.get_webconsolers_account(),
                    "partition_yw_account": self.get_partition_yw_account(),
                    "mycnf_configs": {
                        self.cluster["ctl_port"]: self.__get_mysql_config(
                            immutable_domain=self.cluster["immutable_domain"], db_version="Tdbctl"
                        )
                    },
                },
            },
        }

    def get_import_schema_to_tdbctl_payload(self, **kwargs):
        return {
            "db_type": DBActuatorTypeEnum.SpiderCtl.value,
            "action": DBActuatorActionEnum.ImportSchemaToTdbctl.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["ctl_port"],
                    "backend_host": self.cluster["shard_0_host"],
                    "backend_port": self.cluster["shard_0_port"],
                    "spider_port": self.cluster["spider_port"],
                    "use_mydumper": self.cluster["use_mydumper"],
                    "stream": self.cluster["stream"],
                    "drop_before": self.cluster["drop_before"],
                    "threads": self.cluster["threads"],
                    "tdbctl_user": self.cluster["tdbctl_user"],
                    "tdbctl_pass": self.cluster["tdbctl_pass"],
                },
            },
        }

    def get_check_schema_payload(self, **kwargs):
        return {
            "db_type": DBActuatorTypeEnum.SpiderCtl.value,
            "action": DBActuatorActionEnum.CheckTdbctlWithSpiderSchema.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["ctl_port"],
                    "spider_port": self.cluster["spider_port"],
                },
            },
        }

    def get_check_router_payload(self, **kwargs):
        return {
            "db_type": DBActuatorTypeEnum.SpiderCtl.value,
            "action": DBActuatorActionEnum.CheckTdbctlWithSpiderRouter.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["ctl_port"],
                },
            },
        }

    def get_install_spider_ctl_payload(self, **kwargs):
        """
        拼接spider-ctl节点安装的payload, ctl是单机单实例, 所以代码兼容多实例传入
        """
        ctl_charset = self.ticket_data["ctl_charset"]

        ctl_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.tdbCtl)
        version_no = get_mysql_real_version(ctl_pkg.name)

        drs_account, dbha_account = self.get_super_account()
        return {
            "db_type": DBActuatorTypeEnum.SpiderCtl.value,
            "action": DBActuatorActionEnum.Deploy.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "pkg": ctl_pkg.name,
                    "pkg_md5": ctl_pkg.md5,
                    "mysql_version": version_no,
                    "charset": ctl_charset,
                    "inst_mem": 0,
                    "ports": [self.ticket_data["ctl_port"]],
                    "super_account": drs_account,
                    "dbha_account": dbha_account,
                    "webconsolers_account": self.get_webconsolers_account(),
                    "partition_yw_account": self.get_partition_yw_account(),
                    "mycnf_configs": {
                        self.ticket_data["ctl_port"]: self.__get_mysql_config(
                            immutable_domain=self.cluster["immutable_domain"], db_version="Tdbctl"
                        )
                    },
                },
            },
        }

    def get_grant_mysql_repl_user_payload(self, **kwargs) -> dict:
        """
        拼接创建repl账号的payload参数(在master节点执行)
        """
        repl_host = (
            kwargs["trans_data"].get("new_slave_ip", self.cluster["new_slave_ip"])
            if kwargs.get("trans_data")
            else self.cluster["new_slave_ip"]
        )

        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.GrantRepl.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["mysql_port"],
                    "repl_hosts": [repl_host],
                },
            },
        }

    def get_grant_repl_for_migrate_cluster(self, **kwargs) -> dict:
        """
        拼接创建repl账号的payload参数(在master节点执行)
        """
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.GrantRepl.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["mysql_port"],
                    "repl_hosts": [self.cluster["new_master_ip"]],
                },
            },
        }

    def get_change_slave_config_payload(self, **kwargs) -> dict:
        """
        拼接修改mysql slave 参数的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.Deploy.value,
            "payload": {
                "extend": {
                    "tgt_instance": {
                        "host": self.cluster,
                        "port": 3306,
                        "user": "test",
                        "pwd": "test",
                        "socket": "/data1/mysqldata/3306/mysql.sock",
                        "charset": "",
                        "options": "",
                    }
                }
            },
        }

    def get_find_local_backup_payload(self, **kwargs) -> dict:
        """
        拼接获取本地备份文件的参数
        """
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.GetBackupFile.value,
            "payload": {
                # "general":None,
                "extend": {
                    "backup_dirs": ["/data/dbbak", "/data1/dbbak"],
                    "tgt_instance": {"host": kwargs["ip"], "port": self.cluster["master_port"]},
                    "file_server": False,
                }
            },
        }

    def get_change_master_payload(self, **kwargs) -> dict:
        """
        拼接同步主从的payload参数(在slave节点执行), 获取master的位点信息的场景通过上下文获取
        todo mysql_port获取方案对于同已存储对内，因为同集群内的实例端口都一致,兼容旧的方式，后续考虑去取
        """
        default_port = self.cluster.get("mysql_port", 0)
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.ChangeMaster.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster.get("slave_port", default_port),
                    "master_host": kwargs["trans_data"].get("new_master_ip", self.cluster["new_master_ip"]),
                    "master_port": self.cluster.get("master_port", default_port),
                    "is_gtid": False,
                    "max_tolerate_delay": 0,
                    "force": self.ticket_data.get("change_master_force", False),
                    "bin_file": kwargs["trans_data"]["master_ip_sync_info"]["bin_file"],
                    "bin_position": kwargs["trans_data"]["master_ip_sync_info"]["bin_position"],
                },
            },
        }

    def get_change_master_payload_for_migrate_cluster(self, **kwargs) -> dict:
        """
        拼接同步主从的payload参数(在slave节点执行)
        """
        payload = {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.ChangeMaster.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["mysql_port"],
                    "master_host": self.cluster["master_ip"],
                    "master_port": self.cluster["mysql_port"],
                    "is_gtid": False,
                    "max_tolerate_delay": 0,
                    "force": False,
                    "bin_file": kwargs["trans_data"]["change_master_info"]["master_log_file"],
                    "bin_position": kwargs["trans_data"]["change_master_info"]["master_log_pos"],
                },
            },
        }
        return payload

    def get_uninstall_mysql_payload(self, **kwargs) -> dict:
        """
        卸载mysql进程的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.UnInstall.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "force": self.ticket_data["force"],
                    "ports": [self.cluster["backend_port"]],
                },
            },
        }

    def get_uninstall_spider_payload(self, **kwargs) -> dict:
        """
        卸载spider进程的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Spider.value,
            "action": DBActuatorActionEnum.UnInstall.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "force": self.ticket_data["force"],
                    "ports": [self.cluster["spider_port"]],
                },
            },
        }

    def get_uninstall_spider_ctl_payload(self, **kwargs) -> dict:
        """
        卸载spider-ctl进程的payload参数
        """
        return {
            "db_type": DBActuatorTypeEnum.SpiderCtl.value,
            "action": DBActuatorActionEnum.UnInstall.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "force": self.ticket_data["force"],
                    "ports": [self.cluster["spider_ctl_port"]],
                },
            },
        }

    def get_import_sqlfile_payload(self, **kwargs) -> dict:
        """
        return import sqlfile payload
        """
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.ImportSQLFile.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "ports": [self.cluster["port"]],
                    "file_path": self.ticket_data["sql_path"],
                    "file_path_suffix": self.ticket_data["file_path_suffix"],
                    "file_base_dir": self.ticket_data["file_base_dir"],
                    "charset": self.ticket_data["charset"],
                    "execute_objects": self.ticket_data["execute_objects"],
                },
            },
        }

    def get_check_ddl_blocking_payload(self, **kwargs) -> dict:
        """
        return import sqlfile payload
        """
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.CheckPlsExecSQLFile.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "ports": [self.cluster["port"]],
                    "file_path": self.ticket_data["sql_path"],
                    "file_path_suffix": self.ticket_data["file_path_suffix"],
                    "file_base_dir": self.ticket_data["file_base_dir"],
                    "charset": self.ticket_data["charset"],
                    "mnt_spider_instance": self.cluster.get("mnt_spider_instance", {}),
                    "execute_objects": self.ticket_data["execute_objects"],
                },
            },
        }

    def get_tendbcluster_online_ddl_payload(self, **kwargs) -> dict:
        """
        return import sqlfile payload
        """
        return {
            "db_type": DBActuatorTypeEnum.SpiderCtl.value,
            "action": DBActuatorActionEnum.DoOnlineDDL.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "ports": [self.cluster["port"]],
                    "file_path": self.ticket_data["sql_path"],
                    "file_path_suffix": self.ticket_data["file_path_suffix"],
                    "file_base_dir": self.ticket_data["file_base_dir"],
                    "charset": self.ticket_data["charset"],
                    "execute_objects": self.ticket_data["execute_objects"],
                    "bill_id": self.ticket_data.get("uid", 0),
                    "engine": self.cluster["engine"],
                },
            },
        }

    def get_clone_client_grant_payload(self, **kwargs):
        """
        克隆客户端的MySQL权限
        """
        if self.cluster.get("is_drop", False):
            # 代表是proxy替换，会清理proxy权限，则template_client_host为origin_proxy_ip
            template_client_host = self.cluster["origin_proxy_ip"]
        else:
            # 代表是proxy添加，不清理旧proxy权限， 则template_client_host为template_proxy_ip
            template_client_host = self.cluster["template_proxy_ip"]
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.CloneClientGrant.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["mysql_port"],
                    "template_client_host": template_client_host,
                    "target_client_host": self.cluster["target_proxy_ip"],
                    "is_drop": self.cluster.get("is_drop", False),
                    "origin_client_host": self.cluster.get("origin_proxy_ip", "1.1.1.1"),
                },
            },
        }

    def get_semantic_check_payload(self, **kwargs):
        """
        运行SQL语义检查
        """
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.SemanticCheck.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["semantic_port"],
                    "schemafile": f"{BK_PKG_INSTALL_PATH}/{self.cluster['semantic_dump_schema_file_name']}",
                    "execute_objects": self.ticket_data["execute_objects"],
                    "remote_host": self.cluster["backend_ip"],
                    "remote_port": self.cluster["backend_port"],
                },
            },
        }

    def get_semantic_dump_schema_payload(self, **kwargs):
        """
        获取SQL语义测试时库表备份文件
        """
        # 获取db_cloud_token
        bk_cloud_id = self.bk_cloud_id
        db_cloud_token = AsymmetricHandler.encrypt(
            name=AsymmetricCipherConfigType.PROXYPASS.value, content=f"{bk_cloud_id}_dbactuator_token"
        )

        upload_sql_path = BKREPO_SQLFILE_PATH.format(biz=self.ticket_data["bk_biz_id"])
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.SemanticDumpSchema.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "bk_cloud_id": bk_cloud_id,
                    "db_cloud_token": db_cloud_token,
                    "host": kwargs["ip"],
                    "port": self.cluster["port"],
                    "charset": self.ticket_data["charset"],
                    "dump_all": self.cluster.get("dump_all", True),
                    "parse_need_dump_dbs": self.cluster.get("parse_need_dump_dbs", []),
                    "parse_create_dbs": self.cluster.get("parse_create_dbs", []),
                    "execute_objects": self.cluster.get("execute_objects", None),
                    "just_dump_special_tbls": self.cluster.get("just_dump_special_tbls", False),
                    "special_tbls": self.cluster.get("special_tbls", []),
                    "backup_file_name": f"{self.cluster['semantic_dump_schema_file_name']}",
                    "backup_file_name_suffix": f"{self.cluster['semantic_dump_schema_file_name_suffix']}",
                    "backup_dir": BK_PKG_INSTALL_PATH,
                    "fileserver": {
                        "url": get_bk_repo_url(bk_cloud_id),
                        "bucket": settings.BKREPO_BUCKET,
                        "username": settings.BKREPO_USERNAME,
                        "password": settings.BKREPO_PASSWORD,
                        "project": settings.BKREPO_PROJECT,
                        "upload_path": upload_sql_path,
                    },
                },
            },
        }

    def get_mysql_restore_slave_payload(self, **kwargs):
        """
        MYSQL SLAVE 恢复
        """
        index_file = os.path.basename(kwargs["trans_data"]["backupinfo"]["index_file"])
        payload = {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.RestoreSlave.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "work_dir": self.cluster["file_target_path"],
                    "backup_dir": self.cluster["file_target_path"],
                    "backup_files": {
                        # "full": None,
                        "index": [index_file],
                        # "priv": None,
                    },
                    "tgt_instance": {
                        # "host": self.cluster["new_slave_ip"],
                        "host": kwargs["ip"],
                        "port": self.cluster["master_port"],
                        "user": self.account["admin_user"],
                        "pwd": self.account["admin_pwd"],
                        "socket": None,
                        "charset": self.cluster["charset"],
                        "options": "",
                    },
                    "src_instance": {"host": self.cluster["master_ip"], "port": self.cluster["master_port"]},
                    "change_master": self.cluster["change_master"],
                    "work_id": "",
                },
            },
        }
        return payload

    @staticmethod
    def get_clear_machine_crontab(**kwargs):
        """
        crontab 清理的payload
        """
        return {
            "db_type": DBActuatorTypeEnum.Default.value,
            "action": DBActuatorActionEnum.ClearCrontab.value,
            "payload": {},
        }

    def get_clean_mysql_payload(self, **kwargs):
        payload = {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.CleanMysql.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "stop_slave": self.cluster["stop_slave"],
                    "reset_slave": self.cluster["reset_slave"],
                    "restart": self.cluster["restart"],
                    "force": self.cluster["force"],
                    "drop_database": self.cluster["drop_database"],
                    "tgt_instance": {"host": self.cluster["new_slave_ip"], "port": self.cluster["new_slave_port"]},
                },
            },
        }
        return payload

    def get_set_backend_toward_slave_payload(self, **kwargs):
        """
        切换主从act的调用参数，act 逻辑包括：克隆权限、切换角色、设置proxy配置
        下发到slave（新的master机器）执行
        """
        cluster = Cluster.objects.get(id=self.cluster["id"])
        proxys = cluster.proxyinstance_set.all()
        proxy_instances = []
        for proxy in proxys:
            proxy_instances.append({"host": proxy.machine.ip, "port": proxy.port})

        slave_instances = []
        for slave_ip in self.cluster["other_slave_info"]:
            slave_instances.append({"host": slave_ip, "port": self.cluster["mysql_port"]})

        # 拼接切换时需要的临时切换账号，如果是主故障类型切换传空。
        switch_user = {
            "user": self.ticket_data.get("switch_account", None),
            "pwd": self.ticket_data.get("switch_pwd", None),
        }
        mysql_count = self.account
        proxy_count = self.proxy_account

        data = {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.SetBackendTowardSlave.value,
            "payload": {
                "general": {"runtime_account": {**mysql_count, **proxy_count}},
                "extend": {
                    "host": kwargs["ip"],
                    "slave_delay_check": self.ticket_data.get("is_check_delay", True),
                    "is_dead_master": self.ticket_data["is_dead_master"],
                    "grant_repl": self.ticket_data["grant_repl"],
                    "locked_switch": self.ticket_data["locked_switch"],
                    "cluster": {
                        "proxy_instances": proxy_instances,
                        "master_instance": {
                            "host": self.cluster["old_master_ip"],
                            "port": self.cluster["mysql_port"],
                            "switch_account": switch_user,
                        },
                        "alt_slave_instance": {
                            "host": self.cluster["new_master_ip"],
                            "port": self.cluster["mysql_port"],
                        },
                        "slave_instance": slave_instances,
                    },
                },
            },
        }

        if self.cluster.get("new_slave_ip"):
            # 如果cluster结构体参数有 new_slave_ip, 代表是做成对切换，new_slave_ip代表新slave机器
            data["payload"]["extend"]["cluster"]["alt_slave_instance"]["slave"] = {
                "host": self.cluster["new_slave_ip"],
                "port": self.cluster["mysql_port"],
                "switch_account": switch_user,
            }

        return data

    def get_rollback_data_restore_payload(self, **kwargs):
        """
        MYSQL 定点回档恢复备份介质
        """
        logger.info(self.cluster["backupinfo"])
        init_command = self.cluster.get("init_command", "")
        enable_binlog = self.cluster.get("enable_binlog", False)
        index_file = os.path.basename(self.cluster["backupinfo"]["index"]["file_name"])
        payload = {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.RestoreSlave.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "work_dir": self.cluster["file_target_path"],
                    "backup_dir": self.cluster["file_target_path"],
                    "backup_files": {
                        "index": [index_file],
                    },
                    "tgt_instance": {
                        "host": kwargs["ip"],
                        "port": self.cluster["rollback_port"],
                        "user": self.account["admin_user"],
                        "pwd": self.account["admin_pwd"],
                        "socket": None,
                        "charset": self.cluster["charset"],
                        "options": "",
                    },
                    "restore_opts": {
                        "databases": self.cluster["databases"],
                        "tables": self.cluster["tables"],
                        "ignore_databases": self.cluster["databases_ignore"],
                        "ignore_tables": self.cluster["tables_ignore"],
                        "recover_binlog": self.cluster["recover_binlog"],
                        "enable_binlog": enable_binlog,
                        "init_command": init_command,
                    },
                    "src_instance": {"host": "", "port": 0},
                    "change_master": self.cluster["change_master"],
                    "work_id": "",
                },
            },
        }
        return payload

    def get_checksum_payload(self, **kwargs) -> dict:
        """
        数据校验
        """
        db_patterns = []
        ignore_dbs = []
        if self.ticket_data["ticket_type"] == TicketType.TENDBCLUSTER_CHECKSUM:
            db_patterns = [
                ele if ele.endswith("%") or ele == "*" else "{}_{}".format(ele, self.ticket_data["shard_id"])
                for ele in self.ticket_data["db_patterns"]
            ]
            ignore_dbs = [
                ele if ele.endswith("%") or ele == "*" else "{}_{}".format(ele, self.ticket_data["shard_id"])
                for ele in self.ticket_data["ignore_dbs"]
            ]
        elif self.ticket_data["ticket_type"] == TicketType.MYSQL_CHECKSUM:
            db_patterns = self.ticket_data["db_patterns"]
            ignore_dbs = self.ticket_data["ignore_dbs"]
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.Checksum.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "bk_biz_id": self.ticket_data["bk_biz_id"],
                    "cluster_id": self.ticket_data["cluster_id"],
                    "immute_domain": self.ticket_data["immute_domain"],
                    "master_ip": self.ticket_data["master"]["ip"],
                    "master_port": self.ticket_data["master"]["port"],
                    "inner_role": self.ticket_data["master"]["instance_inner_role"],
                    "slaves": self.ticket_data["slaves"],
                    "master_access_slave_user": kwargs["trans_data"]["master_access_slave_user"],
                    "master_access_slave_password": kwargs["trans_data"]["master_access_slave_password"],
                    "db_patterns": db_patterns,
                    "ignore_dbs": ignore_dbs,
                    "table_patterns": self.ticket_data["table_patterns"],
                    "ignore_tables": self.ticket_data["ignore_tables"],
                    "runtime_hour": self.ticket_data["runtime_hour"],
                    "replicate_table": "{}.{}{}".format(
                        CHECKSUM_DB, CHECKSUM_TABlE_PREFIX, self.ticket_data["ran_str"]
                    ),
                    "system_dbs": SYSTEM_DBS,
                    "stage_db_header": STAGE_DB_HEADER,
                    "rollback_db_tail": ROLLBACK_DB_TAIL,
                },
            },
        }

    def get_partition_payload(self, **kwargs) -> dict:
        """
        表分区
        """
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.Partition.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "ip": self.cluster["ip"],
                    "file_path": os.path.join(BK_PKG_INSTALL_PATH, "partition", self.cluster["file_path"]),
                },
            },
        }

    def get_partition_cron_payload(self, **kwargs) -> dict:
        """
        表分区
        """
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.Partition.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "ip": self.ticket_data["ip"],
                    "file_path": os.path.join(BK_PKG_INSTALL_PATH, "partition", self.ticket_data["file_name"]),
                },
            },
        }

    def get_pt_table_sync_payload(self, **kwargs) -> dict:
        """
        获取数据修复的payload
        """
        # 判断单据触发来源
        if self.ticket_data["trigger_type"] == DataSyncSource.ROUTINE.value:
            is_routine_trigger = True
        else:
            is_routine_trigger = False

        data = {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.PtTableSync.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": self.cluster["slave_ip"],
                    "port": self.cluster["slave_port"],
                    "master_host": self.cluster["master_ip"],
                    "master_port": self.cluster["master_port"],
                    "is_sync_non_innodb": self.cluster.get("is_sync_non_innodb", False),
                    "sync_user": self.cluster["sync_user"],
                    "sync_pass": self.cluster["sync_pass"],
                    "check_sum_table": self.cluster["check_sum_table"],
                    "is_routine_trigger": is_routine_trigger,
                },
            },
        }
        if is_routine_trigger:
            data["payload"]["extend"]["start_time"] = self.ticket_data["start_time"]
            data["payload"]["extend"]["end_time"] = self.ticket_data["end_time"]

        return data

    def get_mysql_flashback_payload(self, **kwargs) -> dict:
        """
        mysql flashback
        """
        databases = self.cluster["databases"]
        tables = self.cluster["tables"]

        return self.__flashback_payload(databases, tables, **kwargs)

    def get_spider_flashback_payload(self, **kwargs) -> dict:
        """
        tendbcluster flashback
        """
        shard_id = self.cluster["shard_id"]

        databases = self.cluster["databases"]
        tables = self.cluster["tables"]

        databases = ["{}_{}".format(ele, shard_id) for ele in databases]

        return self.__flashback_payload(databases, tables, **kwargs)

    def __flashback_payload(self, databases: List, tables: List, **kwargs) -> dict:
        payload = {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.GoFlashBackBinlog.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "tgt_instance": {
                        "host": kwargs["ip"],
                        "port": self.cluster["master_port"],
                        "user": self.account["admin_user"],
                        "pwd": self.account["admin_pwd"],
                        "socket": None,
                        "charset": None,
                        "options": "",
                    },
                    "recover_opt": {
                        "databases": databases,
                        "databases_ignore": [],
                        "tables": tables,
                        "tables_ignore": [],
                        "filter_rows": "",
                    },
                    # 原始 binlog 目录，如果不提供，则自动为实例 binlog 目录
                    "binlog_dir": "",
                    # binlog列表，如果不提供，则自动从本地查找符合时间范围的 binlog
                    "binlog_files": None,
                    "work_dir": self.cluster["work_dir"],
                    # "tools": {"mysqlbinlog": self.cluster["mysqlbinlog_rollback"]},
                    # 闪回的目标时间点，对应 recover-binlog 的 start_time, 精确到秒。
                    "target_time": self.cluster["start_time"],
                    "stop_time": self.cluster["end_time"],
                },
            },
        }
        # 如果指定了行级别的回档,需添加4个参数,使用GoFlashBackBinlog工具回档
        rows_filter = self.cluster.get("rows_filter", "").strip()
        direct_write_back = self.cluster.get("direct_write_back", True)
        if rows_filter != "":
            payload["action"] = DBActuatorActionEnum.GoFlashBackBinlog.value
            payload["payload"]["extend"]["recover_opt"]["rows_event_type"] = ""
            payload["payload"]["extend"]["recover_opt"]["conv_rows_update_to_write"] = False
            payload["payload"]["extend"]["recover_opt"]["rows_filter"] = rows_filter
            payload["payload"]["extend"]["recover_opt"]["direct_write_back"] = direct_write_back
        return payload

    def get_mysql_edit_config_payload(self, **kwargs) -> dict:
        """
        mysql 配置修改
        """
        # -1 不重启 1 重启 2 由参数决定
        # 如果参数设置了重启、要指定哪些ip可以重启，否则认为不可重启
        if kwargs["ip"] in self.cluster["restart_ips"] and self.cluster["restart"] in (1, 2):
            restart = self.cluster["restart"]
        else:
            restart = -1
        payload = {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.MysqlEditConfig.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "items": self.cluster["items"],
                    # -1 不持久化 1 持久化 2 仅持久化但不修改运行时
                    "persistent": self.cluster["persistent"],
                    "restart": restart,
                    # "restart_ips": self.cluster["restart_ips"],
                    "tgt_instance": {
                        "host": kwargs["ip"],
                        "port": self.cluster["master_port"],
                        "user": self.account["admin_user"],
                        "pwd": self.account["admin_pwd"],
                        "socket": None,
                        "charset": "",
                        "options": "",
                    },
                },
            },
        }
        return payload

    def get_clear_surrounding_config_payload(self, **kwargs) -> dict:
        """
        拼接获取集群维度清理周边配置的payload，如例行校验、例行备份、rotate_binlog等
        clear_ports 是代表这次需要清理实例端口, 通过单据的cluster信息捕捉
        兼容单节点集群和主从集群的场景
        """
        ports = []
        machine = Machine.objects.get(ip=kwargs["ip"])
        if machine.machine_type == MachineType.PROXY.value:
            ports = (
                self.cluster["proxy_port"]
                if isinstance(self.cluster["proxy_port"], list)
                else [self.cluster["proxy_port"]]
            )
        elif machine.machine_type in (MachineType.BACKEND.value, MachineType.SINGLE.value):
            ports = (
                self.cluster["backend_port"]
                if isinstance(self.cluster["backend_port"], list)
                else [self.cluster["backend_port"]]
            )
        elif machine.machine_type == MachineType.REMOTE.value:
            ports = (
                self.cluster["remote_port"]
                if isinstance(self.cluster["remote_port"], list)
                else [self.cluster["remote_port"]]
            )
        elif machine.machine_type == MachineType.SPIDER.value:
            ports = (
                self.cluster["spider_port"]
                if isinstance(self.cluster["spider_port"], list)
                else [self.cluster["spider_port"]]
            )
        else:
            raise Exception(f"not support machine_type:{machine.machine_type}")

        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.MysqlClearSurroundingConfig.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {"clear_ports": ports, "machine_type": machine.machine_type},
            },
        }

    def get_grant_repl_for_ctl_payload(self, **kwargs) -> dict:
        """
        针对spider中控集群部署场景(一主多从，基于GTID)
        拼接创建repl账号的payload参数(在master节点执行)
        兼容资源池获取IP、手输IP的两类场景
        """
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.GrantRepl.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["mysql_port"],
                    "repl_hosts": self.cluster["slaves"],
                },
            },
        }

    def get_change_master_for_gitd_payload(self, **kwargs) -> dict:
        """
        拼接同步主从的payload参数(在slave节点执行)。基于GTID场景
        """
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.ChangeMaster.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["mysql_port"],
                    "master_host": self.cluster["master_ip"],
                    "master_port": self.cluster["mysql_port"],
                    "is_gtid": True,
                    "max_tolerate_delay": 0,
                    "force": self.ticket_data.get("change_master_force", False),
                    "bin_file": "test.log",
                    "bin_position": 107,
                },
            },
        }

    def get_init_spider_routing_payload(self, **kwargs):
        """
        拼接初始化spider集群节点关系的payload参数。
        """
        tdbctl_account = self.account
        return {
            "db_type": DBActuatorTypeEnum.SpiderCtl.value,
            "action": DBActuatorActionEnum.SpiderInitClusterRouting.value,
            "payload": {
                "general": {"runtime_account": tdbctl_account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.ticket_data["ctl_port"],
                    "mysql_instance_tuples": self.cluster["mysql_instance_tuples"],
                    "spider_instances": self.cluster["spider_instances"],
                    "ctl_instances": self.cluster["ctl_instances"],
                    "tdbctl_user": self.cluster["tdbctl_user"],
                    "tdbctl_pass": self.cluster["tdbctl_pass"],
                    "is_no_slave": self.cluster.get("is_no_slave", False),
                    "is_ctl_alone": self.cluster.get("is_ctl_alone", False),
                },
            },
        }

    def get_init_tdbctl_routing_payload(self, **kwargs):
        """
        拼接初始化spider集群节点关系的payload参数。
        """
        tdbctl_account = self.account
        return {
            "db_type": DBActuatorTypeEnum.SpiderCtl.value,
            "action": DBActuatorActionEnum.SpiderInitClusterRouting.value,
            "payload": {
                "general": {"runtime_account": tdbctl_account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.ticket_data["ctl_port"],
                    "mysql_instance_tuples": self.cluster["mysql_instance_tuples"],
                    "spider_instances": self.cluster["spider_instances"],
                    "spider_slave_instances": self.cluster["spider_slave_instances"],
                    "mnt_spider_instances": self.cluster["mnt_spider_instances"],
                    "mnt_spider_slave_instances": self.cluster["mnt_spider_slave_instances"],
                    "ctl_instances": self.cluster["ctl_instances"],
                    "tdbctl_user": self.cluster["tdbctl_user"],
                    "tdbctl_pass": self.cluster["tdbctl_pass"],
                    "not_flush_all": True,
                    "only_init_ctl": self.cluster["only_init_ctl"],
                },
            },
        }

    def get_add_tmp_spider_node_payload(self, **kwargs):
        tdbctl_account = self.account
        return {
            "db_type": DBActuatorTypeEnum.SpiderCtl.value,
            "action": DBActuatorActionEnum.SpiderAddTmpNode.value,
            "payload": {
                "general": {"runtime_account": tdbctl_account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.ticket_data["ctl_port"],
                    "spider_instances": self.cluster["spider_instances"],
                },
            },
        }

    def get_restart_spider_payload(self, **kwargs):
        return {
            "db_type": DBActuatorTypeEnum.Spider.value,
            "action": DBActuatorActionEnum.RestartSpider.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["spider_port"],
                },
            },
        }

    def add_spider_slave_routing_payload(self, **kwargs):
        """
        拼接添加spider slave集群节点关系的payload参数。
        """
        # 获取中控实例的内置账号
        tdbctl_account = self.account

        # 定义集群的所有slave实例的列表，添加路由关系需要
        slave_instances = []
        add_spider_slave_instances = []

        cluster = Cluster.objects.get(id=self.cluster["cluster_id"])

        # 获取集群的分片信息，过滤具有REPEATER属性的存储对
        remote_tuples = cluster.tendbclusterstorageset_set.exclude(
            storage_instance_tuple__ejector__instance_inner_role=InstanceInnerRole.REPEATER
        )
        spider_port = cluster.proxyinstance_set.first().port
        ctl_port = cluster.proxyinstance_set.first().admin_port

        # 拼接集群分片的remote-dr节点信息，为初始化路由做打算
        if self.cluster["is_init_slave_cluster"]:
            for shard in remote_tuples:
                slave_instances.append(
                    {
                        "shard_id": shard.shard_id,
                        "host": shard.storage_instance_tuple.receiver.machine.ip,
                        "port": shard.storage_instance_tuple.receiver.port,
                    }
                )

        # 拼接这次添加spider-slave节点信息，为初始化路由做打算
        for ip_info in self.cluster["add_spider_slaves"]:
            add_spider_slave_instances.append(
                {
                    "host": ip_info["ip"],
                    "port": spider_port,  # 新添加的spider slave 同一套集群统一同一个spider端口
                }
            )

        return {
            "db_type": DBActuatorTypeEnum.SpiderCtl.value,
            "action": DBActuatorActionEnum.AddSlaveClusterRouting.value,
            "payload": {
                "general": {"runtime_account": tdbctl_account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": ctl_port,
                    "slave_instances": slave_instances,
                    "spider_slave_instances": add_spider_slave_instances,
                },
            },
        }

    def mysql_backup_demand_payload(self, **kwargs):
        port = self.ticket_data["port"]
        if self.cluster.get("is_ctl"):
            port = port + 1000

        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.MySQLBackupDemand.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": self.ticket_data["ip"],
                    "port": port,
                    "role": self.ticket_data["role"],
                    "backup_type": self.ticket_data["backup_type"],
                    "backup_gsd": self.ticket_data["backup_gsd"],
                    "backup_id": self.ticket_data["backup_id"].__str__(),
                    "bill_id": str(self.ticket_data["uid"]),
                    "custom_backup_dir": self.ticket_data.get("custom_backup_dir", ""),
                    "shard_id": self.ticket_data.get("shard_id", 0),
                    "backup_file_tag": self.ticket_data.get("file_tag", ""),
                    "db_patterns": self.ticket_data.get("db_patterns", ["*"]),
                    "ignore_dbs": self.ticket_data.get("ignore_dbs", []),
                    "table_patterns": self.ticket_data.get("table_patterns", ["*"]),
                    "ignore_tables": self.ticket_data.get("ignore_tables", []),
                },
            },
        }

    def spider_priv_backup_demand_payload(self, **kwargs):
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.MySQLBackupDemand.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": self.cluster["host"],
                    "port": self.cluster["port"],
                    "backup_id": self.cluster["backup_id"],
                    "role": TenDBClusterSpiderRole.SPIDER_MASTER.value,
                    "backup_type": MySQLBackupTypeEnum.LOGICAL.value,
                    "backup_gsd": ["grant"],
                    "bill_id": str(self.ticket_data["uid"]),
                    "custom_backup_dir": "",
                    "backup_file_tag": MySQLBackupFileTagEnum.DBFILE1M.value,
                    "db_patterns": ["*"],
                    "ignore_dbs": [],
                    "table_patterns": ["*"],
                    "ignore_tables": [],
                },
            },
        }

    def tendb_cluster_slave_spt_switch(self, **kwargs):
        cluster_id = self.cluster["cluster_id"]
        switch_tuples = self.cluster["switch_tuples"]
        c = Cluster.objects.get(id=cluster_id)
        shards = c.tendbclusterstorageset_set.filter()
        shard_map = defaultdict(int)
        for shard in shards:
            shard_map[shard.storage_instance_tuple.receiver.id] = shard.shard_id
            shard_map[shard.storage_instance_tuple.ejector.id] = shard.shard_id
        switch_paris = []
        for tuples in switch_tuples:
            objs = c.storageinstance_set.filter(machine__ip=tuples["master"]["ip"])
            for master in objs:
                slave = StorageInstanceTuple.objects.get(ejector=master).receiver
                switch_paris.append(
                    {
                        "shard_id": shard_map.get(int(master.id), -1),
                        "master": {"host": master.machine.ip, "port": master.port},
                        "slave": {"host": slave.machine.ip, "port": slave.port},
                    }
                )
        pos_info = kwargs["trans_data"]["masters_bin_pos_map"]
        logger.info(f"pos_info: {pos_info}")
        return {
            "db_type": DBActuatorTypeEnum.SpiderCtl.value,
            "action": DBActuatorActionEnum.TenDBClusterBackendSlaveSptSwitch.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": c.proxyinstance_set.first().admin_port,
                    "slave_delay_check": self.ticket_data["is_check_delay"],
                    "force": self.ticket_data["force"],
                    "switch_paris": switch_paris,
                    "pos_map_info": json.dumps(pos_info),
                    "batch_id": self.cluster["batch_id"],
                },
            },
        }

    def tendb_cluster_remote_switch(self, **kwargs):
        """
        定义拼接TenDB-Cluster集群的remote互切/主故障切换的payload参数
        """
        cluster_id = self.cluster["cluster_id"]
        switch_tuples = self.cluster["switch_tuples"]
        c = Cluster.objects.get(id=cluster_id)
        shards = c.tendbclusterstorageset_set.filter()
        shard_map = defaultdict(int)
        for shard in shards:
            shard_map[shard.storage_instance_tuple.receiver.id] = shard.shard_id
            shard_map[shard.storage_instance_tuple.ejector.id] = shard.shard_id
        switch_paris = []
        for tuples in switch_tuples:
            objs = c.storageinstance_set.filter(machine__ip=tuples["master"]["ip"])
            for master in objs:
                slave = StorageInstanceTuple.objects.get(ejector=master).receiver
                switch_paris.append(
                    {
                        "shard_id": shard_map.get(int(master.id), -1),
                        "master": {"host": master.machine.ip, "port": master.port},
                        "slave": {"host": slave.machine.ip, "port": slave.port},
                    }
                )

        return {
            "db_type": DBActuatorTypeEnum.SpiderCtl.value,
            "action": DBActuatorActionEnum.TenDBClusterBackendSwitch.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": c.proxyinstance_set.first().admin_port,
                    "slave_delay_check": self.ticket_data["is_check_delay"],
                    "force": self.ticket_data["force"],
                    "switch_paris": switch_paris,
                    "batch_id": self.cluster["batch_id"],
                },
            },
        }

    def tendb_cluster_remote_migrate(self, **kwargs):
        """
        定义拼接TenDB-Cluster成对迁移的payload参数
        """
        cluster = Cluster.objects.get(id=self.ticket_data["cluster_id"])
        migrate_cutover_pairs = []
        for info in self.ticket_data["migrate_tuples"]:
            migrate_cutover_pairs.append(
                {
                    "origin_master": {
                        "host": info["old_master"].split(":")[0],
                        "port": int(info["old_master"].split(":")[1]),
                    },
                    "dest_master": {
                        "host": info["new_master"].split(":")[0],
                        "port": int(info["new_master"].split(":")[1]),
                        "user": TDBCTL_USER,
                        "password": self.ticket_data["tdbctl_pass"],
                    },
                    "dest_slave": {
                        "host": info["new_slave"].split(":")[0],
                        "port": int(info["new_slave"].split(":")[1]),
                        "user": TDBCTL_USER,
                        "password": self.ticket_data["tdbctl_pass"],
                    },
                }
            )

        return {
            "db_type": DBActuatorTypeEnum.SpiderCtl.value,
            "action": DBActuatorActionEnum.TenDBClusterMigrateCutOver.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": cluster.proxyinstance_set.first().admin_port,
                    "slave_delay_check": self.ticket_data["slave_delay_check"],
                    "migrate_cutover_pairs": migrate_cutover_pairs,
                },
            },
        }

    def tendb_restore_remotedb_payload(self, **kwargs):
        """
        tendb 恢复remote实例
        """
        recover_grants = self.cluster.get("recover_grants", False)
        logger.info(self.cluster["backupinfo"])
        index_file = os.path.basename(self.cluster["backupinfo"]["index"]["file_name"])
        payload = {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.RestoreSlave.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "work_dir": self.cluster["file_target_path"],
                    "backup_dir": self.cluster["file_target_path"],
                    "backup_files": {
                        # "full": None,
                        "index": [index_file],
                        # "priv": None,
                    },
                    "tgt_instance": {
                        "host": self.cluster["restore_ip"],
                        "port": self.cluster["restore_port"],
                        "user": self.account["admin_user"],
                        "pwd": self.account["admin_pwd"],
                        "socket": None,
                        "charset": self.cluster["charset"],
                        "options": "",
                    },
                    "recover_opt": {
                        "recover_grants": recover_grants,
                    },
                    "src_instance": {"host": self.cluster["source_ip"], "port": self.cluster["source_port"]},
                    "change_master": self.cluster["change_master"],
                    "work_id": "",
                },
            },
        }
        return payload

    def tendb_restore_priv_payload(self, **kwargs):
        """
        tendb 恢复权限
        """
        logger.info(self.cluster["sql_files"])
        payload = {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.FastExecuteSqlFile.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "socket": "",
                    "host": kwargs["ip"],
                    "port": self.cluster["port"],
                    "database": "information_schema",
                    "force": self.cluster["force"],
                    "file_dir": self.cluster["file_target_path"],
                    "sql_files": self.cluster["sql_files"],
                },
            },
        }
        return payload

    def tendb_grant_remotedb_repl_user(self, **kwargs) -> dict:
        """
        拼接创建repl账号的payload参数(在master节点执行)
        """
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.GrantRepl.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": self.cluster["target_ip"],
                    "port": self.cluster["target_port"],
                    "repl_hosts": [self.cluster["repl_ip"]],
                },
            },
        }

    def tendb_remotedb_change_master(self, **kwargs) -> dict:
        """
        拼接同步主从的payload参数(在slave节点执行), 获取master的位点信息的场景通过上下文获取
        todo 后续可能支持多角度传入master的位点信息的拼接
        """
        if self.cluster["change_master_type"] == MysqlChangeMasterType.MASTERSTATUS.value:
            bin_file = kwargs["trans_data"]["show_master_status_info"]["bin_file"]
            bin_position = int(kwargs["trans_data"]["show_master_status_info"]["bin_position"])
        else:
            bin_file = kwargs["trans_data"]["change_master_info"]["master_log_file"]
            bin_position = int(kwargs["trans_data"]["change_master_info"]["master_log_pos"])
        bin_file = bin_file.strip().strip("'")
        logger.info("CHANGE MASTER TO MASTER_LOG_FILE='{}', MASTER_LOG_POS={}".format(bin_file, bin_position))
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.ChangeMaster.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": self.cluster["repl_ip"],
                    "port": self.cluster["repl_port"],
                    "master_host": self.cluster["target_ip"],
                    "master_port": self.cluster["target_port"],
                    "is_gtid": False,
                    "max_tolerate_delay": 0,
                    "force": self.cluster.get("change_master_force", False),
                    "bin_file": bin_file,
                    "bin_position": bin_position,
                },
            },
        }

    def tendb_recover_binlog_payload(self, **kwargs):
        """
        MYSQL 实例 前滚binglog
        """
        logger.info(self.cluster)
        logger.info(
            "backup_time: {} ~ stop_time: {} ".format(self.cluster["backup_time"], self.cluster["rollback_time"])
        )
        binlog_files = self.cluster["binlog_files"]
        backup_time = self.cluster["backup_time"]
        binlog_files_list = binlog_files.split(",")
        binlog_start_file = self.cluster["binlog_start_file"]
        binlog_start_pos = int(self.cluster["binlog_start_pos"])
        if binlog_start_file not in binlog_files_list:
            logger.error("start binlog {} not exist".format(binlog_start_file))
            raise TendbGetBackupInfoFailedException(message=_("start binlog  {} not exist".format(binlog_start_file)))
        payload = {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.RecoverBinlog.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "work_dir": self.cluster["file_target_path"],
                    "binlog_dir": self.cluster["file_target_path"],
                    "binlog_files": binlog_files_list,
                    "tgt_instance": {
                        "host": kwargs["ip"],
                        "port": self.cluster["rollback_port"],
                        "user": self.account["admin_user"],
                        "pwd": self.account["admin_pwd"],
                        "socket": None,
                        "charset": self.cluster["charset"],
                        "options": "",
                    },
                    "recover_opt": {
                        "start_time_bak": backup_time,
                        "stop_time": self.cluster["rollback_time"],
                        "idempotent_mode": True,
                        "not_write_binlog": True,
                        "mysql_client_opt": {"max_allowed_packet": 1073741824, "binary_mode": True},
                        "databases": self.cluster["databases"],
                        "tables": self.cluster["tables"],
                        "databases_ignore": self.cluster["databases_ignore"],
                        "tables_ignore": self.cluster["tables_ignore"],
                        "start_pos": binlog_start_pos,
                    },
                    "parse_only": False,
                    "binlog_start_file": binlog_start_file,
                },
            },
        }
        return payload

    def get_install_tmp_db_backup_payload(self, **kwargs):
        """
        数据恢复时安装临时备份程序。大部分信息可忽略不计
        """

        machine = Machine.objects.get(ip=kwargs["ip"], bk_cloud_id=int(self.bk_cloud_id))
        if machine.machine_type == MachineType.SPIDER.value:
            role = machine.proxyinstance_set.first().tendbclusterspiderext.spider_role
        elif machine.machine_type in [MachineType.REMOTE.value, MachineType.BACKEND.value, MachineType.SINGLE.value]:
            # 原来的代码是下面把 role 写死了这个值, 所以保留原逻辑
            role = InstanceInnerRole.MASTER.value
        else:
            raise DBMetaException(message=_("不支持的机器类型: {}".format(machine.machine_type)))

        # 获取backup程序包的名称
        if self.cluster.get("db_backup_pkg_type"):
            db_backup_pkg_type = self.cluster["db_backup_pkg_type"]

        elif machine.machine_type != MachineType.SPIDER.value:
            db_backup_pkg_type = MysqlVersionToDBBackupForMap[self.ticket_data["db_version"]]
        else:
            logger.warning("db_backup_pkg_type is null, default dbbackup")
            db_backup_pkg_type = MediumEnum.DbBackup

        db_backup_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=db_backup_pkg_type)

        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.DeployDbbackup.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "pkg": db_backup_pkg.name,
                    "pkg_md5": db_backup_pkg.md5,
                    "host": kwargs["ip"],
                    "ports": [0],
                    "bk_cloud_id": int(self.bk_cloud_id),
                    "bk_biz_id": int(self.ticket_data["bk_biz_id"]),
                    "role": role,  # InstanceInnerRole.MASTER.value,
                    "configs": {},
                    "options": {},
                    "cluster_address": {},
                    "cluster_id": {},
                    "cluster_type": machine.cluster_type,  # ClusterType.TenDBHA,
                    "exec_user": self.ticket_data["created_by"],
                    "shard_value": {},
                    "untar_only": True,
                },
            },
        }

    def mysql_mkdir_dir(self, **kwargs) -> dict:
        """
        mkdir for backup
        """
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.OsCmd.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "cmds": [
                        {"cmd_name": "mkdir", "cmd_args": ["-p", self.cluster["file_target_path"]]},
                        {"cmd_name": "chown", "cmd_args": ["mysql.mysql", self.cluster["file_target_path"]]},
                    ],
                    "work_dir": "",
                },
            },
        }

    def get_open_area_dump_schema_payload(self, **kwargs):
        """
        开区导出表结构
        @param kwargs:
        @return:
        """
        fileserver = {}
        db_cloud_token = AsymmetricHandler.encrypt(
            name=AsymmetricCipherConfigType.PROXYPASS.value, content=f"{self.bk_cloud_id}_dbactuator_token"
        )
        upload_sql_path = BKREPO_SQLFILE_PATH.format(biz=self.ticket_data["bk_biz_id"])
        if self.cluster["is_upload_bkrepo"]:
            fileserver.update(
                {
                    "url": get_bk_repo_url(self.bk_cloud_id),
                    "bucket": settings.BKREPO_BUCKET,
                    "username": settings.BKREPO_USERNAME,
                    "password": settings.BKREPO_PASSWORD,
                    "project": settings.BKREPO_PROJECT,
                    "upload_path": upload_sql_path,
                }
            )

        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,  # spider集群也用mysql类型
            "action": DBActuatorActionEnum.MysqlOpenAreaDumpSchema.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["port"],
                    "charset": "default",
                    "root_id": self.cluster["root_id"],
                    "bk_cloud_id": self.bk_cloud_id,
                    "db_cloud_token": db_cloud_token,
                    "dump_dir_name": f"{self.cluster['root_id']}_schema",
                    "fileserver": fileserver,
                    "open_area_param": self.cluster["open_area_param"],
                },
            },
        }

    def get_open_area_import_schema_payload(self, **kwargs):
        """
        开区导入表结构
        @param kwargs:
        @return:
        """
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,  # spider集群也用mysql类型
            "action": DBActuatorActionEnum.MysqlOpenAreaImportSchema.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["port"],
                    "charset": "default",
                    "root_id": self.cluster["root_id"],
                    "bk_cloud_id": self.bk_cloud_id,
                    "dump_dir_name": f"{self.cluster['root_id']}_schema",
                    "open_area_param": self.cluster["open_area_param"],
                },
            },
        }

    def get_open_area_dump_data_payload(self, **kwargs):
        """
        开区导出表数据
        @param kwargs:
        @return:
        """
        fileserver = {}
        db_cloud_token = AsymmetricHandler.encrypt(
            name=AsymmetricCipherConfigType.PROXYPASS.value, content=f"{self.bk_cloud_id}_dbactuator_token"
        )
        upload_sql_path = BKREPO_SQLFILE_PATH.format(biz=self.ticket_data["bk_biz_id"])
        if self.cluster["is_upload_bkrepo"]:
            fileserver.update(
                {
                    "url": get_bk_repo_url(self.bk_cloud_id),
                    "bucket": settings.BKREPO_BUCKET,
                    "username": settings.BKREPO_USERNAME,
                    "password": settings.BKREPO_PASSWORD,
                    "project": settings.BKREPO_PROJECT,
                    "upload_path": upload_sql_path,
                }
            )
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,  # spider集群也用mysql类型
            "action": DBActuatorActionEnum.MysqlOpenAreaDumpData.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["port"],
                    "charset": "default",
                    "root_id": self.cluster["root_id"],
                    "bk_cloud_id": self.bk_cloud_id,
                    "db_cloud_token": db_cloud_token,
                    "dump_dir_name": f"{self.cluster['root_id']}_data",
                    "fileserver": fileserver,
                    "open_area_param": [],
                    "info_file": True,
                },
            },
        }

    def get_open_area_import_data_payload(self, **kwargs):
        """
        开区导入表数据
        @param kwargs:
        @return:
        """
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,  # spider集群也用mysql类型
            "action": DBActuatorActionEnum.MysqlOpenAreaImportData.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["port"],
                    "charset": "default",
                    "root_id": self.cluster["root_id"],
                    "bk_cloud_id": self.bk_cloud_id,
                    "dump_dir_name": f"{self.cluster['root_id']}_data",
                    "open_area_param": self.cluster["open_area_param"],
                },
            },
        }

    def enable_tokudb_payload(self, **kwargs):
        """
        enable Tokudb engine for mysql instance
        """
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.EnableTokudb.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "ports": self.ticket_data.get("mysql_ports", []),
                },
            },
        }

    def get_mysql_upgrade_payload(self, **kwargs) -> dict:
        """
        local upgrade mysql proxy
        """
        mysql_pkg = Package.objects.get(id=self.cluster["pkg_id"], pkg_type=MediumEnum.MySQL)
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.Upgrade.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "ports": self.cluster["ports"],
                    "force": self.ticket_data["force"],
                    "pkg": mysql_pkg.name,
                    "pkg_md5": mysql_pkg.md5,
                    "run": self.cluster["run"],
                },
            },
        }

    def get_data_migrate_dump_payload(self, **kwargs):
        """
        数据迁移导出库表结构与数据
        @param kwargs:
        @return:
        """
        fileserver = {}
        db_cloud_token = AsymmetricHandler.encrypt(
            name=AsymmetricCipherConfigType.PROXYPASS.value, content=f"{self.bk_cloud_id}_dbactuator_token"
        )
        upload_sql_path = BKREPO_SQLFILE_PATH.format(biz=self.ticket_data["bk_biz_id"])
        fileserver.update(
            {
                "url": get_bk_repo_url(self.bk_cloud_id),
                "bucket": settings.BKREPO_BUCKET,
                "username": settings.BKREPO_USERNAME,
                "password": settings.BKREPO_PASSWORD,
                "project": settings.BKREPO_PROJECT,
                "upload_path": upload_sql_path,
            }
        )

        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.MysqlDataMigrateDump.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["port"],
                    "charset": "default",
                    "root_id": self.cluster["root_id"],
                    "bk_cloud_id": self.bk_cloud_id,
                    "db_cloud_token": db_cloud_token,
                    "work_dir": self.cluster["work_dir"],
                    "dump_dir_name": self.cluster["dump_dir_name"],
                    "fileserver": fileserver,
                    "db_list": self.cluster["db_list"],
                    "data_schema_grant": self.cluster["data_schema_grant"],
                },
            },
        }

    def get_data_migrate_import_payload(self, **kwargs):
        """
        数据迁移导入库表结构与数据
        @param kwargs:
        @return:
        """
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.MysqlDataMigrateImport.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["port"],
                    "charset": "default",
                    "root_id": self.cluster["root_id"],
                    "bk_cloud_id": self.bk_cloud_id,
                    "work_dir": self.cluster["work_dir"],
                    "import_dir_name": self.cluster["import_dir_name"],
                    "index_file_name": kwargs["trans_data"]["file_list_info"]["file_name_list"][0],
                },
            },
        }

    def get_dbconsole_schema_payload(self, **kwargs):
        """
        获取dbconsole备份payload
        """
        # 获取db_cloud_token
        bk_cloud_id = self.bk_cloud_id
        db_cloud_token = AsymmetricHandler.encrypt(
            name=AsymmetricCipherConfigType.PROXYPASS.value, content=f"{bk_cloud_id}_dbactuator_token"
        )
        if self.cluster.get("dump_center"):
            self.account["admin_user"] = self.cluster["random_account"]
            self.account["admin_pwd"] = self.cluster["random_password"]
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.MysqlDumpData.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": self.cluster["ip"],
                    "port": self.cluster["port"],
                    "charset": self.ticket_data["charset"],
                    "dump_detail": {
                        "databases": self.ticket_data["databases"],
                        "tables": self.ticket_data.get("tables"),
                        "tables_ignore": self.ticket_data.get("tables_ignore"),
                        "where": self.ticket_data.get("where"),
                        "dump_data": self.ticket_data["dump_data"],
                        "dump_schema": self.ticket_data["dump_schema"],
                    },
                    "zip_file_name": f"{self.cluster['dbconsole_dump_file_name']}.zip",
                    "one_db_one_file": False,
                    "upload_detail": {
                        "bk_cloud_id": bk_cloud_id,
                        "db_cloud_token": db_cloud_token,
                        "backup_file_name": f"{self.cluster['dbconsole_dump_file_name']}",
                        "backup_dir": BK_PKG_INSTALL_PATH,
                        "fileserver": {
                            "url": get_bk_repo_url(bk_cloud_id),
                            "bucket": settings.BKREPO_BUCKET,
                            "username": settings.BKREPO_USERNAME,
                            "password": settings.BKREPO_PASSWORD,
                            "project": settings.BKREPO_PROJECT,
                            "upload_path": BKREPO_DBCONSOLE_DUMPFILE_PATH.format(biz=self.ticket_data["bk_biz_id"]),
                        },
                    },
                },
            },
        }

    def get_change_mycnf_payload(self, **kwargs) -> dict:
        """
        return sync change mysql my.cnf payload
        """
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.MysqlChangeMycnf.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "ports": self.cluster["ports"],
                    "items": self.cluster["items"],
                    "persistent": 1,
                    "restart": 2,
                },
            },
        }

    def rename_create_to_db_via_ctl(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.SpiderCtl.value,
            "action": DBActuatorActionEnum.CreateToDBViaCtl.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": self.ticket_data["ctl_primary"].split(IP_PORT_DIVIDER)[0],
                    "port": int(self.ticket_data["ctl_primary"].split(IP_PORT_DIVIDER)[1]),
                    "requests": self.ticket_data["requests"],
                },
            },
        }

    def rename_pre_drop_to_on_remote(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.RenamePreDropToOnRemote.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": self.cluster["ip"],
                    "port_shard_id_map": self.cluster["port_shard_id_map"],
                    "requests": self.ticket_data["requests"],
                },
            },
        }

    def rename_on_mysql(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.RenameOnMySQL.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": self.cluster["ip"],
                    "port_shard_id_map": self.cluster["port_shard_id_map"],
                    "requests": self.ticket_data["requests"],
                    "has_shard": False,
                },
            },
        }

    def rename_on_remote(self, **kwargs) -> dict:
        p = self.rename_on_mysql(**kwargs)
        p["payload"]["extend"]["has_shard"] = True
        return p

    def rename_drop_from_via_ctl(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.SpiderCtl.value,
            "action": DBActuatorActionEnum.RenameDropFromViaCtl.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": self.ticket_data["ctl_primary"].split(IP_PORT_DIVIDER)[0],
                    "port": int(self.ticket_data["ctl_primary"].split(IP_PORT_DIVIDER)[1]),
                    "requests": self.ticket_data["requests"],
                },
            },
        }

    def rename_check_dbs_in_using(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.RenameCheckDBsInUsing.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": self.cluster["ip"],
                    "port": int(self.cluster["port"]),
                    "dbs": self.cluster["dbs"],
                },
            },
        }

    def truncate_create_stage_via_ctl(self, **kwargs) -> dict:
        """
        在中控创建清档备份库表
        """
        return {
            "db_type": DBActuatorTypeEnum.SpiderCtl.value,
            "action": DBActuatorActionEnum.CreateStageViaCtl.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": self.ticket_data["ctl_primary"].split(IP_PORT_DIVIDER)[0],
                    "port": int(self.ticket_data["ctl_primary"].split(IP_PORT_DIVIDER)[1]),
                    "flow_timestr": self.ticket_data["flow_timestr"],
                    "stage_db_header": STAGE_DB_HEADER,
                    "rollback_db_tail": ROLLBACK_DB_TAIL,
                    "db_patterns": self.ticket_data["db_patterns"],
                    "ignore_dbs": self.ticket_data["ignore_dbs"],
                    "table_patterns": self.ticket_data["table_patterns"],
                    "ignore_tables": self.ticket_data["ignore_tables"],
                    "system_dbs": SYSTEM_DBS,
                    "truncate_data_type": self.ticket_data["truncate_data_type"],
                },
            },
        }

    def truncate_check_dbs_in_using(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.TruncateCheckDBsInUsing.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": self.cluster["ip"],
                    "port": int(self.cluster["port"]),
                    "stage_db_header": STAGE_DB_HEADER,
                    "rollback_db_tail": ROLLBACK_DB_TAIL,
                    "db_patterns": self.ticket_data["db_patterns"],
                    "ignore_dbs": self.ticket_data["ignore_dbs"],
                    "table_patterns": self.ticket_data["table_patterns"],
                    "ignore_tables": self.ticket_data["ignore_tables"],
                    "system_dbs": SYSTEM_DBS,
                },
            },
        }

    def truncate_on_mysql(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.TruncateOnMySQL.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": self.cluster["ip"],
                    "port_shard_id_map": self.cluster["port_shard_id_map"],
                    "flow_timestr": self.ticket_data["flow_timestr"],
                    "stage_db_header": STAGE_DB_HEADER,
                    "rollback_db_tail": ROLLBACK_DB_TAIL,
                    "db_patterns": self.ticket_data["db_patterns"],
                    "ignore_dbs": self.ticket_data["ignore_dbs"],
                    "table_patterns": self.ticket_data["table_patterns"],
                    "ignore_tables": self.ticket_data["ignore_tables"],
                    "system_dbs": SYSTEM_DBS,
                    "has_shard": False,
                    "truncate_data_type": self.ticket_data["truncate_data_type"],
                },
            },
        }

    def truncate_on_remote(self, **kwargs) -> dict:
        p = self.truncate_on_mysql(**kwargs)
        p["payload"]["extend"]["has_shard"] = True
        return p

    def truncate_on_ctl(self, **kwargs) -> dict:
        p = self.truncate_create_stage_via_ctl(**kwargs)
        p["action"] = DBActuatorActionEnum.TruncateOnCtl.value
        return p

    def truncate_pre_drop_stage_on_remote(self, **kwargs) -> dict:
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.TruncatePreDropStageOnRemote.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": self.cluster["ip"],
                    "port_shard_id_map": self.cluster["port_shard_id_map"],
                    "flow_timestr": self.ticket_data["flow_timestr"],
                    "stage_db_header": STAGE_DB_HEADER,
                    "rollback_db_tail": ROLLBACK_DB_TAIL,
                    "db_patterns": self.ticket_data["db_patterns"],
                    "ignore_dbs": self.ticket_data["ignore_dbs"],
                    "table_patterns": self.ticket_data["table_patterns"],
                    "ignore_tables": self.ticket_data["ignore_tables"],
                    "system_dbs": SYSTEM_DBS,
                },
            },
        }

    def mysql_change_server_id(self, **kwargs):
        payload = {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.ChangeServerId.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": [
                    {
                        "host": self.cluster["new_slave_ip"],
                        "port": self.cluster["new_slave_port"],
                    }
                ],
            },
        }
        return payload

    def get_spider_upgrade_payload(self, **kwargs) -> dict:
        """
        local upgrade mysql proxy
        """
        pkg = Package.objects.get(id=self.cluster["pkg_id"], pkg_type=MediumEnum.Spider)
        return {
            "db_type": DBActuatorTypeEnum.Spider.value,
            "action": DBActuatorActionEnum.Upgrade.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "ports": self.cluster["proxy_ports"],
                    "force": self.cluster["force_upgrade"],
                    "pkg": pkg.name,
                    "pkg_md5": pkg.md5,
                },
            },
        }
