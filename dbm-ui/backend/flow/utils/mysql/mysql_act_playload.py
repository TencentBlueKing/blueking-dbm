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
import logging
import os
import re
from typing import Any

from django.conf import settings
from django.utils.translation import ugettext as _

from backend import env
from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName, ReqType
from backend.configuration.models import SystemSettings
from backend.constants import IP_RE_PATTERN
from backend.core import consts
from backend.core.consts import BK_PKG_INSTALL_PATH
from backend.core.encrypt.constants import RSAConfigType
from backend.core.encrypt.handlers import RSAHandler
from backend.db_meta.enums import InstanceInnerRole, MachineType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, Machine, ProxyInstance, StorageInstance
from backend.db_package.models import Package
from backend.db_proxy.constants import ExtensionType
from backend.db_proxy.models import DBCloudProxy, DBExtension
from backend.db_services.mysql.sql_import.constants import BKREPO_SQLFILE_PATH
from backend.flow.consts import (
    CHECKSUM_DB,
    SYSTEM_DBS,
    CHECKSUM_TABlE_PREFIX,
    ConfigTypeEnum,
    DataSyncSource,
    DBActuatorActionEnum,
    DBActuatorTypeEnum,
    MediumEnum,
    NameSpaceEnum,
)
from backend.flow.engine.bamboo.scene.common.get_real_version import get_mysql_real_version, get_spider_real_version
from backend.ticket.constants import TicketType

apply_list = [TicketType.MYSQL_SINGLE_APPLY.value, TicketType.MYSQL_HA_APPLY.value]

logger = logging.getLogger("flow")


class MysqlActPayload(object):
    """
    定义mysql不同执行类型，拼接不同的payload参数，对应不同的dict结构体。
    """

    def __init__(self, bk_cloud_id: int, ticket_data: dict, cluster: dict, cluster_type: str = None):
        """
        @param bk_cloud_id 操作的云区域
        @param ticket_data 单据信息
        @param cluster 需要操作的集群信息
        @param cluster_type 表示操作的集群类型，会决定到db_config获取配置的空间
        """
        self.init_mysql_config = {}
        self.bk_cloud_id = bk_cloud_id
        self.ticket_data = ticket_data
        self.cluster = cluster
        self.cluster_type = cluster_type
        self.mysql_pkg = None
        self.proxy_pkg = None
        self.checksum_pkg = None
        self.mysql_crond_pkg = None
        self.mysql_monitor_pkg = None
        self.account = self.__get_mysql_account()

        # self.db_module_id = (
        #     self.ticket_data["module"] if self.ticket_data.get("module") else self.cluster.get("db_module_id")
        # )
        # 尝试获取db_module_id , 有些单据不需要db_module_id，则最终给0
        # todo 后面可能优化这个问题
        if self.ticket_data.get("module"):
            self.db_module_id = self.ticket_data["module"]
        elif self.cluster and self.cluster.get("db_module_id"):
            self.db_module_id = self.cluster["db_module_id"]
        else:
            self.db_module_id = 0

    @staticmethod
    def __get_mysql_account() -> Any:
        """
        获取mysql实例内置帐户密码
        """
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": "0",
                "level_name": LevelName.PLAT,
                "level_value": "0",
                "conf_file": "mysql#user",
                "conf_type": ConfigTypeEnum.InitUser,
                "namespace": NameSpaceEnum.TenDB.value,
                "format": FormatType.MAP,
            }
        )
        return data["content"]

    def __get_super_account_bypass(self):
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

    def __get_super_account(self):
        """
        获取mysql机器系统管理账号信息
        """

        if env.DRS_USERNAME and env.DBHA_USERNAME:
            return self.__get_super_account_bypass()

        rsa = RSAHandler.get_or_generate_rsa_in_db(RSAConfigType.get_rsa_cloud_name(self.bk_cloud_id))

        drs = DBExtension.get_latest_extension(bk_cloud_id=self.bk_cloud_id, extension_type=ExtensionType.DRS)
        drs_account_data = {
            "access_hosts": DBExtension.get_extension_access_hosts(
                bk_cloud_id=self.bk_cloud_id, extension_type=ExtensionType.DRS
            ),
            "pwd": RSAHandler.decrypt_password(rsa.rsa_private_key.content, drs.details["pwd"]),
            "user": RSAHandler.decrypt_password(rsa.rsa_private_key.content, drs.details["user"]),
        }

        dbha = DBExtension.get_latest_extension(bk_cloud_id=self.bk_cloud_id, extension_type=ExtensionType.DBHA)
        dbha_account_data = {
            "access_hosts": DBExtension.get_extension_access_hosts(
                bk_cloud_id=self.bk_cloud_id, extension_type=ExtensionType.DBHA
            ),
            "pwd": RSAHandler.decrypt_password(rsa.rsa_private_key.content, dbha.details["pwd"]),
            "user": RSAHandler.decrypt_password(rsa.rsa_private_key.content, dbha.details["user"]),
        }

        return drs_account_data, dbha_account_data

    @staticmethod
    def __get_proxy_account() -> Any:
        """
        获取proxy实例内置帐户密码
        """
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": "0",
                "level_name": LevelName.PLAT,
                "level_value": "0",
                "conf_file": "proxy#user",
                "conf_type": ConfigTypeEnum.InitUser,
                "namespace": NameSpaceEnum.TenDB.value,
                "format": FormatType.MAP,
            }
        )
        return data["content"]

    def __get_mysql_config(self, immutable_domain, db_version) -> Any:
        """
        生成并获取mysql实例配置,集群级别配置
        spider/spider-ctl/spider-mysql实例统一用这里拿去配置
        """
        data = DBConfigApi.get_instance_config(
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

    def __get_proxy_config(self) -> Any:
        """获取proxy安装配置, 平台层级的配置，没有业务区分"""
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": "0",
                "level_name": LevelName.PLAT,
                "level_value": "0",
                "conf_file": "default",
                "conf_type": "proxyconf",
                "namespace": self.cluster_type,
                "format": FormatType.MAP,
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
        return data["charset"], data["db_version"]

    def __get_dbbackup_config(self) -> Any:
        rsp = {}
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(self.ticket_data["bk_biz_id"]),
                "level_name": LevelName.MODULE,
                "level_value": str(self.db_module_id),
                "conf_file": "dbbackup.ini",
                "conf_type": "backup",
                "namespace": self.cluster_type,
                "format": FormatType.MAP_LEVEL,
            }
        )
        rsp["ini"] = data["content"]
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(self.ticket_data["bk_biz_id"]),
                "level_name": LevelName.MODULE,
                "level_value": str(self.db_module_id),
                "conf_file": "dbbackup.options",
                "conf_type": "backup",
                "namespace": self.cluster_type,
                "format": FormatType.MAP_LEVEL,
            }
        )
        rsp["options"] = data["content"]
        return rsp

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
            "payload": {"user": self.account["os_mysql_user"], "pwd": self.account["os_mysql_pwd"]},
        }

    def get_install_mysql_payload(self, **kwargs) -> dict:
        """
        拼接安装MySQL的payload参数, 分别兼容集群申请、集群实例重建、集群实例添加单据的获取方式
        由于集群实例重建或者添加单据是不知道 需要部署的版本号以及字符集，需要通过接口获取
        """
        if self.ticket_data.get("charset") and self.ticket_data.get("db_version"):
            # 如果单据传入有字符集和版本号，则以单据为主：
            charset, db_version = self.ticket_data.get("charset"), self.ticket_data.get("db_version")
        else:
            # 如果没有传入，则通过db_config获取
            charset, db_version = self.__get_version_and_charset(db_module_id=self.db_module_id)

        for cluster in self.ticket_data["clusters"]:
            self.init_mysql_config[cluster["mysql_port"]] = self.__get_mysql_config(
                immutable_domain=cluster["master"], db_version=db_version
            )

        self.mysql_pkg = Package.get_latest_package(version=db_version, pkg_type=MediumEnum.MySQL)
        version_no = get_mysql_real_version(self.mysql_pkg.name)

        install_mysql_ports = self.ticket_data.get("mysql_ports")
        mysql_config = {}
        if not isinstance(install_mysql_ports, list) or len(install_mysql_ports) == 0:
            logger.error(_("传入的安装mysql端口列表为空或者非法值，请联系系统管理员"))
            return {}

        for port in install_mysql_ports:
            mysql_config[port] = copy.deepcopy(self.init_mysql_config[port])

        drs_account, dbha_account = self.__get_super_account()

        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.Deploy.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "pkg": self.mysql_pkg.name,
                    "pkg_md5": self.mysql_pkg.md5,
                    "mysql_version": version_no,
                    "charset": charset,
                    "inst_mem": 0,
                    "ports": self.ticket_data.get("mysql_ports", []),
                    "super_account": drs_account,
                    "dbha_account": dbha_account,
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

        drs_account, dbha_account = self.__get_super_account()

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
        slave_config = {"spider_read_only_mode": "1", "read_only": "1"}
        # 拼装spider_slave需要的只读参数
        for key in content["payload"]["extend"]["mycnf_configs"]:
            content["payload"]["extend"]["mycnf_configs"][key]["mysqld"].update(slave_config)
        return content

    def get_install_spider_ctl_payload(self, **kwargs):
        """
        拼接spider-ctl节点安装的payload, ctl是单机单实例, 所以代码兼容多实例传入
        """
        ctl_charset = self.ticket_data["ctl_charset"]

        ctl_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.tdbCtl)
        version_no = get_mysql_real_version(ctl_pkg.name)

        drs_account, dbha_account = self.__get_super_account()
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
                    "mycnf_configs": {
                        self.ticket_data["ctl_port"]: self.__get_mysql_config(
                            immutable_domain=self.cluster["immutable_domain"], db_version="Tdbctl"
                        )
                    },
                },
            },
        }

    def get_install_proxy_payload(self, **kwargs) -> dict:
        """
        拼接安装proxy的payload参数
        """
        self.proxy_pkg = Package.get_latest_package(version="latest", pkg_type=MediumEnum.Proxy)
        return {
            "db_type": DBActuatorTypeEnum.Proxy.value,
            "action": DBActuatorActionEnum.Deploy.value,
            "payload": {
                "general": {"runtime_account": self.__get_proxy_account()},
                "extend": {
                    "host": kwargs["ip"],
                    "pkg": self.proxy_pkg.name,
                    "pkg_md5": self.proxy_pkg.md5,
                    "ports": self.ticket_data.get("proxy_ports", []),
                    "proxy_configs": {"mysql-proxy": self.__get_proxy_config()},
                },
            },
        }

    def get_set_proxy_backends(self, **kwargs) -> dict:
        """
        拼接proxy配置后端实例的payload参数
        """
        set_backend_ip = (
            self.cluster.get("set_backend_ip")
            if self.cluster.get("set_backend_ip")
            else kwargs["trans_data"].get("set_backend_ip")
        )

        return {
            "db_type": DBActuatorTypeEnum.Proxy.value,
            "action": DBActuatorActionEnum.SetBackend.value,
            "payload": {
                "general": {"runtime_account": self.__get_proxy_account()},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["proxy_port"],
                    "backend_host": set_backend_ip,
                    "backend_port": self.cluster["mysql_port"],
                },
            },
        }

    def get_grant_mysql_repl_user_payload(self, **kwargs) -> dict:
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
                    "repl_hosts": [kwargs["trans_data"].get("new_slave_ip", self.cluster["new_slave_ip"])],
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
        todo 后续可能支持多角度传入master的位点信息的拼接
        """
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.ChangeMaster.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["mysql_port"],
                    "master_host": kwargs["trans_data"].get("new_master_ip", self.cluster["new_master_ip"]),
                    "master_port": self.cluster["mysql_port"],
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

    def get_uninstall_proxy_payload(self, **kwargs) -> dict:
        """
        卸载proxy进程的payload 参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Proxy.value,
            "action": DBActuatorActionEnum.UnInstall.value,
            "payload": {
                "general": {"runtime_account": self.__get_proxy_account()},
                "extend": {
                    "host": kwargs["ip"],
                    "force": self.ticket_data["force"],
                    "ports": [self.cluster["proxy_port"]],
                },
            },
        }

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

    def get_install_db_backup_payload(self, **kwargs) -> dict:
        """
        安装备份程序，目前是必须是先录入元信息后，才执行备份程序的安装
        """
        db_backup_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.DbBackup)
        cfg = self.__get_dbbackup_config()
        mysql_ports = []
        port_domain_map = {}
        cluster_id_map = {}

        machine = Machine.objects.get(ip=kwargs["ip"])
        if machine.machine_type == MachineType.SPIDER.value:
            ins_list = ProxyInstance.objects.filter(machine__ip=kwargs["ip"])
            role = ins_list[0].tendbclusterspiderext.spider_role
        elif machine.machine_type in [MachineType.REMOTE.value, MachineType.BACKEND.value, MachineType.SINGLE.value]:
            ins_list = StorageInstance.objects.filter(machine__ip=kwargs["ip"])
            role = ins_list[0].instance_inner_role
        else:
            raise DBMetaException(message=_("不支持的机器类型: {}".format(machine.machine_type)))

        for instance in ins_list:
            cluster = instance.cluster.get()
            mysql_ports.append(instance.port)
            port_domain_map[instance.port] = cluster.immute_domain
            cluster_id_map[instance.port] = cluster.id

        cluster_type = ins_list[0].cluster.get().cluster_type

        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.DeployDbbackup.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "pkg": db_backup_pkg.name,
                    "pkg_md5": db_backup_pkg.md5,
                    "host": kwargs["ip"],
                    "ports": mysql_ports,
                    "bk_cloud_id": int(self.bk_cloud_id),
                    "bk_biz_id": int(self.ticket_data["bk_biz_id"]),
                    "role": role,
                    "configs": cfg["ini"],
                    "options": cfg["options"],
                    "cluster_address": port_domain_map,
                    "cluster_id": cluster_id_map,
                    "cluster_type": cluster_type,
                    "exec_user": self.ticket_data["created_by"],
                },
            },
        }

    def get_dump_na_table_payload(self, **kwargs) -> dict:
        """
        导出非表对象
        """
        old_new_map = kwargs["trans_data"]["old_new_map"]
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.TruncateDataBackupNaTable.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": self.ticket_data["ip"],
                    "port": self.ticket_data["port"],
                    "database_infos": [{"old": k, "new": old_new_map[k]} for k in old_new_map],
                },
            },
        }

    def get_import_sqlfile_payload(self, **kwargs) -> dict:
        """
        return import sqlfile payload
        """
        port = self.cluster["port"]
        cluster_id = self.cluster["id"]
        uid = self.ticket_data["uid"]
        filepath = os.path.join(consts.BK_PKG_INSTALL_PATH, f"sqlfile_{uid}_{cluster_id}_{port}") + "/"
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.ImportSQLFile.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "ports": [port],
                    "file_path": filepath,
                    "charset": self.ticket_data["charset"],
                    "execute_objects": self.ticket_data["execute_objects"],
                },
            },
        }

    def get_clone_client_grant_payload(self, **kwargs):
        """
        克隆客户端的MySQL权限
        """
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.CloneClientGrant.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["mysql_port"],
                    "template_client_host": self.cluster["template_proxy_ip"],
                    "target_client_host": self.cluster["target_proxy_ip"],
                    "is_drop": self.cluster.get("is_drop", False),
                    "origin_client_host": self.cluster.get("origin_proxy_ip", "1.1.1.1"),
                },
            },
        }

    def get_clone_proxy_user_payload(self, **kwargs):
        """
        克隆proxy上的user白名单
        """
        return {
            "db_type": DBActuatorTypeEnum.Proxy.value,
            "action": DBActuatorActionEnum.CloneProxyUser.value,
            "payload": {
                "general": {"runtime_account": self.__get_proxy_account()},
                "extend": {
                    "source_proxy_host": kwargs["ip"],
                    "source_proxy_port": self.cluster["proxy_port"],
                    "target_proxy_host": self.cluster["target_proxy_ip"],
                    "target_proxy_port": self.cluster["proxy_port"],
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
        rsa = RSAHandler.get_or_generate_rsa_in_db(RSAConfigType.PROXYPASS.value)
        db_cloud_token = RSAHandler.encrypt_password(rsa.rsa_public_key.content, f"{bk_cloud_id}_dbactuator_token")

        # 获取url
        nginx_ip = DBCloudProxy.objects.filter(bk_cloud_id=bk_cloud_id).last().internal_address
        bkrepo_url = f"http://{nginx_ip}/apis/proxypass" if bk_cloud_id else settings.BKREPO_ENDPOINT_URL

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
                    "backup_file_name": f"{self.cluster['semantic_dump_schema_file_name']}",
                    "backup_dir": BK_PKG_INSTALL_PATH,
                    "fileserver": {
                        "url": bkrepo_url,
                        "bucket": settings.BKREPO_BUCKET,
                        "username": settings.BKREPO_USERNAME,
                        "password": settings.BKREPO_PASSWORD,
                        "project": settings.BKREPO_PROJECT,
                        "upload_path": BKREPO_SQLFILE_PATH,
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

    def get_restart_proxy_payload(self, **kwargs):
        """
        重启proxy
        """
        return {
            "db_type": DBActuatorTypeEnum.Proxy.value,
            "action": DBActuatorActionEnum.RestartProxy.value,
            "payload": {
                "general": {"runtime_account": self.__get_proxy_account()},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["proxy_port"],
                },
            },
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
        proxy_instances = []
        for proxy_ip in self.cluster["proxy_ip_list"]:
            proxy_instances.append({"host": proxy_ip, "port": self.cluster["proxy_port"]})

        slave_instances = []
        for slave_ip in self.cluster["other_slave_info"]:
            slave_instances.append({"host": slave_ip, "port": self.cluster["mysql_port"]})

        # 拼接切换时需要的临时切换账号，如果是主故障类型切换传空。
        switch_user = {
            "user": self.ticket_data.get("switch_account", None),
            "pwd": self.ticket_data.get("switch_pwd", None),
        }
        mysql_count = self.__get_mysql_account()
        proxy_count = self.__get_proxy_account()

        data = {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.SetBackendTowardSlave.value,
            "payload": {
                "general": {"runtime_account": {**mysql_count, **proxy_count}},
                "extend": {
                    "host": kwargs["ip"],
                    "is_safe": self.ticket_data["is_safe"],
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

    def get_rollback_data_download_backupfile_payload(self, **kwargs) -> dict:
        """
        下载定点恢复的全库备份介质
        """
        payload = {
            "db_type": DBActuatorTypeEnum.Download.value,
            "action": DBActuatorActionEnum.IbsRecver.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "taskid_list": "",
                    "dest_ip": kwargs["ip"],
                    "diretory": self.cluster["diretory"],
                    "reason": "For rollback data",
                    "login_user": self.account["os_mysql_user"],
                    "login_passwd": self.account["os_mysql_pwd"],
                    "task_files": self.cluster["task_files"],
                    "ibs_query": {
                        "source_ip": self.cluster["total_backupinfo"]["mysql_host"],
                        "begin_date": self.cluster["begin_time"],
                        "end_date": self.cluster["end_time"],
                    },
                    # "task_files_wild": {
                    #     "file_tag": "INCREMENT_BACKUP",
                    #     "name_search": str(self.cluster["master_port"]),
                    #     "name_regex": self.cluster["name_regex"]
                    # },
                    "ibs_info": {
                        "url": env.IBS_INFO_URL,
                        "sys_id": env.IBS_INFO_SYSID,
                        "key": env.IBS_INFO_KEY,
                    },
                },
            },
        }
        return payload

    def get_rollback_data_download_binlog_payload(self, **kwargs) -> dict:
        """
        下载定点恢复的binlog文件增量备份介质
        """
        payload = {
            "db_type": DBActuatorTypeEnum.Download.value,
            "action": DBActuatorActionEnum.IbsRecver.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "taskid_list": "",
                    "dest_ip": kwargs["ip"],
                    "diretory": self.cluster["diretory"],
                    "reason": "For rollback data",
                    "login_user": self.account["os_mysql_user"],
                    "login_passwd": self.account["os_mysql_pwd"],
                    # "task_files": self.cluster["backupinfo"]["file_list"],
                    "ibs_query": {
                        "source_ip": self.cluster["master_ip"],
                        "begin_date": self.cluster["binlog_begin_time"],
                        "end_date": self.cluster["binlog_end_time"],
                    },
                    "task_files_wild": {
                        "file_tag": "INCREMENT_BACKUP",
                        "name_search": str(self.cluster["master_port"]),
                        "name_regex": self.cluster["name_regex"],
                    },
                    "ibs_info": {
                        "url": env.IBS_INFO_URL,
                        "sys_id": env.IBS_INFO_SYSID,
                        "key": env.IBS_INFO_KEY,
                    },
                },
            },
        }
        return payload

    def get_rollback_data_restore_payload(self, **kwargs):
        """
        MYSQL SLAVE 恢复
        """
        index_file = os.path.basename(self.cluster["total_backupinfo"]["index_file"])
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
                        # "host": self.cluster["new_slave_ip"],
                        "host": kwargs["ip"],
                        "port": self.cluster["master_port"],
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
                        "recover_binlog": True,
                    },
                    "src_instance": {"host": self.cluster["master_ip"], "port": self.cluster["master_port"]},
                    "change_master": self.cluster["change_master"],
                    "work_id": "",
                },
            },
        }
        return payload

    def get_rollback_data_recover_binlog_payload(self, **kwargs):
        """
        MYSQL定点恢复之binglog前滚
        """
        # todo 如果没有binlog？
        if kwargs["trans_data"]["binlog_files"] is None:
            binlog_files = ""
        else:
            binlog_files = [i["file_name"] for i in kwargs["trans_data"]["binlog_files"]]

        payload = {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.RecoverBinlog.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "work_dir": self.cluster["file_target_path"],
                    "binlog_dir": self.cluster["file_target_path"],
                    "binlog_files": binlog_files,
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
                    "recover_opt": {
                        "start_time_bak": self.cluster["backup_time"],
                        "stop_time": self.cluster["rollback_time"],
                        "idempotent_mode": True,
                        "not_write_binlog": True,
                        "mysql_client_opt": {"max_allowed_packet": 1073741824},
                        "databases": self.cluster["databases"],
                        "tables": self.cluster["tables"],
                        "databases_ignore": self.cluster["databases_ignore"],
                        "tables_ignore": self.cluster["tables_ignore"],
                        "start_pos": int(kwargs["trans_data"]["change_master_info"]["master_log_pos"]),
                    },
                    "parse_only": False,
                    "binlog_start_file": kwargs["trans_data"]["change_master_info"]["master_log_file"],
                },
            },
        }
        return payload

    def get_checksum_payload(self, **kwargs) -> dict:
        """
        数据校验
        """
        db_patterns = [
            ele if ele.endswith("%") else "{}_{}".format(ele, self.ticket_data["shard_id"])
            for ele in self.ticket_data["db_patterns"]
        ]
        ignore_dbs = [
            ele if ele.endswith("%") else "{}_{}".format(ele, self.ticket_data["shard_id"])
            for ele in self.ticket_data["ignore_dbs"]
        ]
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
                },
            },
        }

    def get_partition_payload(self, **kwargs) -> dict:
        """
        表分区
        """
        if self.ticket_data["ticket_type"] == TicketType.MYSQL_PARTITION:
            shard_name = ""
        else:
            shard_name = self.cluster["shard_name"]
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.Partition.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "bk_biz_id": self.ticket_data["bk_biz_id"],
                    "cluster_id": self.ticket_data["cluster_id"],
                    "immute_domain": self.ticket_data["immute_domain"],
                    "master_ip": self.cluster["ip"],
                    "master_port": self.cluster["port"],
                    "shard_name": shard_name,
                    "ticket": "{}/self-service/my-tickets?id={}".format(env.BK_SAAS_HOST, self.ticket_data["uid"]),
                    "file_path": self.cluster["file_path"],
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
            data["start_time"] = self.cluster["start_time"]
            data["end_time"] = self.cluster["end_time"]

        return data

    def get_mysql_flashback_payload(self, **kwargs) -> dict:
        """
        mysql flashback
        """
        payload = {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.FlashBackBinlog.value,
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
                        "databases": self.cluster["databases"],
                        "databases_ignore": self.cluster["databases_ignore"],
                        "tables": self.cluster["tables"],
                        "tables_ignore": self.cluster["tables_ignore"],
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
        return payload

    def get_install_mysql_checksum_payload(self, **kwargs) -> dict:
        self.checksum_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLChecksum)

        instances_info = []
        for instance in StorageInstance.objects.filter(machine__ip=kwargs["ip"]):
            cluster = instance.cluster.get()
            instances_info.append(
                {
                    "bk_biz_id": instance.bk_biz_id,
                    "ip": kwargs["ip"],
                    "port": instance.port,
                    "role": instance.instance_inner_role,
                    "cluster_id": cluster.id,
                    "immute_domain": cluster.immute_domain,
                }
            )

        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.DeployMySQLChecksum.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "pkg": self.checksum_pkg.name,
                    "pkg_md5": self.checksum_pkg.md5,
                    "system_dbs": SYSTEM_DBS,
                    "instances_info": instances_info,
                    "exec_user": self.ticket_data["created_by"],
                    "schedule": "0 5 2 * * 1-5",  # 实际需要更加复杂的配置
                    "api_url": "http://127.0.0.1:9999",  # 长时间可以写死
                },
            },
        }

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

    def get_install_mysql_rotatebinlog_payload(self, **kwargs):
        """
        获取安装实例rotate_binlog程序参数
        """
        mysql_rotatebinlog = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLRotateBinlog
        )
        instances = []
        # 拼接主机需要安装实例备份配置关系

        ins_list = StorageInstance.objects.filter(machine__ip=kwargs["ip"])
        for instance in ins_list:
            ins = {
                "host": kwargs["ip"],
                "port": instance.port,
                "tags": {"bk_biz_id": int(self.ticket_data["bk_biz_id"])},
            }
            cluster = instance.cluster.get()
            ins["tags"]["cluster_domain"] = cluster.immute_domain
            ins["tags"]["cluster_id"] = cluster.id
            ins["tags"]["db_role"] = instance.instance_inner_role
            instances.append(ins)

        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.DeployMysqlBinlogRotate.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "pkg": mysql_rotatebinlog.name,
                    "pkg_md5": mysql_rotatebinlog.md5,
                    "configs": self.__get_mysql_rotatebinlog_config(),
                    "instances": instances,
                },
            },
        }

    def get_install_dba_toolkit_payload(self, **kwargs):
        """
        获取安装实例dba_toolkit工具的参数
        """
        dba_toolkit = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLToolKit)
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.DeployDBAToolkit.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "pkg": dba_toolkit.name,
                    "pkg_md5": dba_toolkit.md5,
                },
            },
        }

    def get_rollback_local_data_restore_payload(self, **kwargs):
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
                        "index": [index_file],
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
                    "restore_opts": {
                        "databases": self.cluster["databases"],
                        "tables": self.cluster["tables"],
                        "ignore_databases": self.cluster["databases_ignore"],
                        "ignore_tables": self.cluster["tables_ignore"],
                        "recover_binlog": True,
                    },
                    "src_instance": {"host": self.cluster["master_ip"], "port": self.cluster["master_port"]},
                    "change_master": self.cluster["change_master"],
                    "work_id": "",
                },
            },
        }
        return payload

    def get_install_restore_backup_payload(self, **kwargs) -> dict:
        """
        安装备份程序，针对从库重建、主从迁移的，实例还不属于集群
        """
        db_backup_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.DbBackup)
        cfg = self.__get_dbbackup_config()
        mysql_ports = []
        port_domain_map = {}
        ins_list = StorageInstance.objects.filter(machine__ip=kwargs["ip"])
        # 获取待添加机器的实例角色，理论上统一主机的所有实例的角色都是一致的，故获取第一个即可
        role = ins_list[0].instance_inner_role
        if role == InstanceInnerRole.REPEATER:
            role = InstanceInnerRole.MASTER

        for cluster in self.ticket_data["clusters"]:
            port = cluster["mysql_port"]
            master_domain = cluster["master"]
            port_domain_map[port] = master_domain
            mysql_ports.append(port)
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.DeployDbbackup.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "pkg": db_backup_pkg.name,
                    "pkg_md5": db_backup_pkg.md5,
                    "host": kwargs["ip"],
                    "ports": mysql_ports,
                    "bk_cloud_id": str(self.bk_cloud_id),
                    "bk_biz_id": str(self.ticket_data["bk_biz_id"]),
                    "role": role,
                    "configs": cfg["ini"],
                    "options": cfg["options"],
                    "cluster_address": port_domain_map,
                },
            },
        }

    def get_clear_surrounding_config_payload(self, **kwargs) -> dict:
        """
        拼接获取集群维度清理周边配置的payload，如例行校验、例行备份、rotate_binlog等
        clear_ports 是代表这次需要清理实例端口, 通过单据的cluster信息捕捉
        兼容单节点集群和主从集群的场景
        """
        ports = []
        machine = Machine.objects.get(ip=kwargs["ip"])
        if machine.machine_type == MachineType.PROXY.value:
            ports = [self.cluster["proxy_port"]]
        elif machine.machine_type in (MachineType.BACKEND.value, MachineType.SINGLE.value):
            ports = [self.cluster["backend_port"]]
        elif machine.machine_type == MachineType.REMOTE.value:
            ports = [self.cluster["remote_port"]]
        elif machine.machine_type == MachineType.SPIDER.value:
            ports = [self.cluster["spider_port"]]
        else:
            pass  # ToDo

        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.MysqlClearSurroundingConfig.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {"clear_ports": ports, "machine_type": machine.machine_type},
            },
        }

    def get_deploy_mysql_crond_payload(self, **kwargs) -> dict:
        self.mysql_crond_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLCrond)

        # 监控自定义上报配置通过SystemSettings表获取
        bkm_dbm_report = SystemSettings.get_setting_value(key="BKM_DBM_REPORT")
        event_data_id = bkm_dbm_report["event"]["data_id"]
        event_data_token = bkm_dbm_report["event"]["token"]
        metrics_data_id = bkm_dbm_report["metric"]["data_id"]
        metrics_data_token = bkm_dbm_report["metric"]["token"]

        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.DeployMySQLCrond.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "pkg": self.mysql_crond_pkg.name,
                    "pkg_md5": self.mysql_crond_pkg.md5,
                    "ip": kwargs["ip"],
                    "bk_cloud_id": int(self.bk_cloud_id),
                    "event_data_id": int(event_data_id),
                    "event_data_token": event_data_token,
                    "metrics_data_id": int(metrics_data_id),
                    "metrics_data_token": metrics_data_token,
                    "beat_path": env.MYSQL_CROND_BEAT_PATH,
                    "agent_address": env.MYSQL_CROND_AGENT_ADDRESS,
                    "bk_biz_id": int(self.ticket_data["bk_biz_id"]),
                },
            },
        }

    def get_deploy_mysql_monitor_payload(self, **kwargs) -> dict:
        """
        部署mysql/proxy/spider事件监控程序
        """
        self.mysql_monitor_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLMonitor
        )
        instances_info = []
        machine = Machine.objects.get(ip=kwargs["ip"])
        if machine.machine_type == MachineType.PROXY.value:
            for instance in ProxyInstance.objects.filter(machine__ip=kwargs["ip"]):
                cluster = instance.cluster.get()
                instances_info.append(
                    {
                        "bk_biz_id": instance.bk_biz_id,
                        "ip": kwargs["ip"],
                        "port": instance.port,
                        "cluster_id": cluster.id,
                        "immute_domain": cluster.immute_domain,
                        "bk_instance_id": instance.bk_instance_id,
                    }
                )
        # 增加对安装spider监控的适配
        elif machine.machine_type == MachineType.SPIDER.value:
            for instance in ProxyInstance.objects.filter(machine__ip=kwargs["ip"]):
                cluster = instance.cluster.get()
                instances_info.append(
                    {
                        "bk_biz_id": instance.bk_biz_id,
                        "ip": kwargs["ip"],
                        "port": instance.port,
                        "role": instance.tendbclusterspiderext.spider_role,  # spider事件监控有没有必要传role来渲染配置？
                        "cluster_id": cluster.id,
                        "immute_domain": cluster.immute_domain,
                        "bk_instance_id": instance.bk_instance_id,
                    }
                )

        # 不同角色的mysql实例，role是否传对应的instance_inner_role ？
        elif machine.machine_type in (MachineType.BACKEND.value, MachineType.SINGLE.value, MachineType.REMOTE.value):
            for instance in StorageInstance.objects.filter(machine__ip=kwargs["ip"]):
                cluster = instance.cluster.get()
                instances_info.append(
                    {
                        "bk_biz_id": instance.bk_biz_id,
                        "ip": kwargs["ip"],
                        "port": instance.port,
                        "role": instance.instance_inner_role,
                        "cluster_id": cluster.id,
                        "immute_domain": cluster.immute_domain,
                        "bk_instance_id": instance.bk_instance_id,
                    }
                )
        else:
            pass  # ToDo

        config_items = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": "{}".format(machine.bk_biz_id),
                "level_name": "cluster",
                "level_value": "act3",
                "conf_file": "items-config.yaml",
                "conf_type": "mysql_monitor",
                "namespace": "tendbha",
                "level_info": {"module": "act"},
                "format": "map",
            }
        )
        logger.info("config_items: {}".format(config_items))

        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.InstallMonitor.value,
            "payload": {
                "general": {"runtime_account": {**self.account, **self.__get_proxy_account()}},
                "extend": {
                    "pkg": self.mysql_monitor_pkg.name,
                    "pkg_md5": self.mysql_monitor_pkg.md5,
                    "system_dbs": SYSTEM_DBS,
                    "exec_user": self.ticket_data["created_by"],
                    "api_url": "http://127.0.0.1:9999",
                    "machine_type": machine.machine_type,
                    "bk_cloud_id": int(self.bk_cloud_id),
                    "instances_info": instances_info,
                    "items_config": config_items["content"],
                },
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
                    "repl_hosts": kwargs["trans_data"].get("slaves", self.cluster["slaves"]),
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
                    "master_host": kwargs["trans_data"].get("master_ip", self.cluster["master_ip"]),
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
        tdbctl_account = self.__get_mysql_account()
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
                },
            },
        }

    def get_add_tmp_spider_node_payload(self, **kwargs):
        tdbctl_account = self.__get_mysql_account()
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
        tdbctl_account = self.__get_mysql_account()

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
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.MySQLBackupDemand.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": self.ticket_data["ip"],
                    "port": self.ticket_data["port"],
                    "backup_type": self.ticket_data["backup_type"],
                    "backup_gsd": self.ticket_data["backup_gsd"],
                    "regex": kwargs["trans_data"]["db_table_filter_regex"],
                    "backup_id": self.ticket_data["backup_id"].__str__(),
                    "bill_id": str(self.ticket_data["uid"]),
                    "custom_backup_dir": self.ticket_data.get("custom_backup_dir", ""),
                },
            },
        }

    def mysql_backup_demand_payload_on_ctl(self, **kwargs):
        payload = self.mysql_backup_demand_payload(**kwargs)
        payload["payload"]["extend"]["port"] += 1000
        return payload
