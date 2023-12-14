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
from typing import Any, List

from django.conf import settings
from django.utils.translation import ugettext as _

from backend import env
from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName, ReqType
from backend.configuration.models import SystemSettings
from backend.core import consts
from backend.core.consts import BK_PKG_INSTALL_PATH
from backend.core.encrypt.constants import AsymmetricCipherConfigType
from backend.core.encrypt.handlers import AsymmetricHandler
from backend.db_meta.enums import ClusterType, InstanceInnerRole, MachineType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, Machine, ProxyInstance, StorageInstance, StorageInstanceTuple
from backend.db_package.models import Package
from backend.db_proxy.models import DBCloudProxy
from backend.db_services.mysql.sql_import.constants import BKREPO_SQLFILE_PATH
from backend.flow.consts import (
    CHECKSUM_DB,
    SYSTEM_DBS,
    TDBCTL_USER,
    CHECKSUM_TABlE_PREFIX,
    ConfigTypeEnum,
    DataSyncSource,
    DBActuatorActionEnum,
    DBActuatorTypeEnum,
    MediumEnum,
    MysqlChangeMasterType,
    RollbackType,
)
from backend.flow.engine.bamboo.scene.common.get_real_version import get_mysql_real_version, get_spider_real_version
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.mysql.proxy_act_payload import ProxyActPayload
from backend.flow.utils.tbinlogdumper.tbinlogdumper_act_payload import TBinlogDumperActPayload
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

apply_list = [TicketType.MYSQL_SINGLE_APPLY.value, TicketType.MYSQL_HA_APPLY.value]

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
        init_mysql_config = {}
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
        version_no = get_mysql_real_version(mysql_pkg.name)

        install_mysql_ports = self.ticket_data.get("mysql_ports")
        mysql_config = {}
        if not isinstance(install_mysql_ports, list) or len(install_mysql_ports) == 0:
            logger.error(_("传入的安装mysql端口列表为空或者非法值，请联系系统管理员"))
            return {}

        for port in install_mysql_ports:
            mysql_config[port] = copy.deepcopy(init_mysql_config[port])

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
                    "mycnf_configs": {
                        self.cluster["ctl_port"]: self.__get_mysql_config(
                            immutable_domain=self.cluster["immutable_domain"], db_version="Tdbctl"
                        )
                    },
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

    def get_install_db_backup_payload(self, **kwargs) -> dict:
        """
        安装备份程序，目前是必须是先录入元信息后，才执行备份程序的安装
        非spider-master角色实例不安装备份程序，已在外层屏蔽
        """
        db_backup_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.DbBackup)
        cfg = self.__get_dbbackup_config()
        mysql_ports = []
        port_domain_map = {}
        cluster_id_map = {}
        shard_port_map = {}  # port as key

        machine = Machine.objects.get(ip=kwargs["ip"])
        if machine.machine_type == MachineType.SPIDER.value:
            ins_list = ProxyInstance.objects.filter(machine__ip=kwargs["ip"])
            role = ins_list[0].tendbclusterspiderext.spider_role
        elif machine.machine_type in [MachineType.REMOTE.value, MachineType.BACKEND.value, MachineType.SINGLE.value]:
            ins_list = StorageInstance.objects.filter(machine__ip=kwargs["ip"])
            role = ins_list[0].instance_inner_role
            # tendbcluster remote 补充shard信息
            if machine.machine_type == MachineType.REMOTE.value:
                for ins in ins_list:
                    if ins.instance_inner_role == InstanceInnerRole.MASTER.value:
                        tp = StorageInstanceTuple.objects.filter(ejector=ins).first()
                    else:
                        tp = StorageInstanceTuple.objects.get(receiver=ins)
                    shard_port_map[ins.port] = tp.tendbclusterstorageset.shard_id
        else:
            raise DBMetaException(message=_("不支持的机器类型: {}".format(machine.machine_type)))

        for instance in ins_list:
            cluster = instance.cluster.get()
            mysql_ports.append(instance.port)
            port_domain_map[instance.port] = cluster.immute_domain
            cluster_id_map[instance.port] = cluster.id

            shard_port_map[instance.port] = shard_port_map.get(instance.port, 0)

            # # 如果是spider-master类型机器，中控实例也需要安装备份程序
            # if role == TenDBClusterSpiderRole.SPIDER_MASTER.value:
            #     mysql_ports.append(instance.admin_port)
            #     port_domain_map[instance.admin_port] = cluster.immute_domain
            #     cluster_id_map[instance.admin_port] = cluster.id

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
                    "shard_value": shard_port_map,
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

    # def get_clone_proxy_user_payload(self, **kwargs):
    #     """
    #     克隆proxy上的user白名单
    #     """
    #     return {
    #         "db_type": DBActuatorTypeEnum.Proxy.value,
    #         "action": DBActuatorActionEnum.CloneProxyUser.value,
    #         "payload": {
    #             "general": {"runtime_account": self.__get_proxy_account()},
    #             "extend": {
    #                 "source_proxy_host": kwargs["ip"],
    #                 "source_proxy_port": self.cluster["proxy_port"],
    #                 "target_proxy_host": self.cluster["target_proxy_ip"],
    #                 "target_proxy_port": self.cluster["proxy_port"],
    #             },
    #         },
    #     }

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

    # def get_restart_proxy_payload(self, **kwargs):
    #     """
    #     重启proxy
    #     """
    #     return {
    #         "db_type": DBActuatorTypeEnum.Proxy.value,
    #         "action": DBActuatorActionEnum.RestartProxy.value,
    #         "payload": {
    #             "general": {"runtime_account": self.__get_proxy_account()},
    #             "extend": {
    #                 "host": kwargs["ip"],
    #                 "port": self.cluster["proxy_port"],
    #             },
    #         },
    #     }

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

    def get_rollback_data_download_backupfile_payload(self, **kwargs) -> dict:
        """
        下载定点恢复的全库备份介质 作废
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
        MYSQL 定点回档恢复备份介质
        """
        if self.cluster.get("rollback_type", "") == RollbackType.LOCAL_AND_TIME:
            index_file = os.path.basename(kwargs["trans_data"]["backupinfo"]["index_file"])
        elif self.cluster.get("rollback_type", "") == RollbackType.LOCAL_AND_BACKUPID:
            index_file = os.path.basename(self.cluster["backupinfo"]["index_file"])
        else:
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
                        "recover_binlog": True,
                    },
                    "src_instance": {"host": self.cluster["master_ip"], "port": self.cluster["master_port"]},
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
                },
            },
        }

    def get_partition_payload(self, **kwargs) -> dict:
        """
        表分区
        """
        ticket = Ticket.objects.get(id=self.ticket_data["uid"])
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
                    "ticket": ticket.url,
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
            data["payload"]["extend"]["start_time"] = self.ticket_data["start_time"]
            data["payload"]["extend"]["end_time"] = self.ticket_data["end_time"]

        return data

    def get_mysql_flashback_payload(self, **kwargs) -> dict:
        """
        mysql flashback
        """
        targets = kwargs["trans_data"]["targets"]
        databases = list(targets.keys())
        tables = list(targets[databases[0]].keys())
        return self.__flashback_payload(databases, tables, **kwargs)

    def get_spider_flashback_payload(self, **kwargs) -> dict:
        """
        tendbcluster flashback
        """
        targets = kwargs["trans_data"]["targets"]
        shard_id = self.cluster["shard_id"]

        # 由于 flashback 库表输入的语义特性
        # 每个 database 对应的 tables 肯定是一样的
        # 所以可以这么取巧的拿出来
        databases = list(targets.keys())
        tables = list(targets[databases[0]].keys())

        databases = ["{}_{}".format(ele, shard_id) for ele in databases]

        return self.__flashback_payload(databases, tables, **kwargs)

    def __flashback_payload(self, databases: List, tables: List, **kwargs) -> dict:
        return {
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

    def get_install_mysql_checksum_payload(self, **kwargs) -> dict:
        checksum_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLChecksum)

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
                    "db_module_id": instance.db_module_id,
                }
            )

        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.DeployMySQLChecksum.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "pkg": checksum_pkg.name,
                    "pkg_md5": checksum_pkg.md5,
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
        mysql_crond_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLCrond)

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
                    "pkg": mysql_crond_pkg.name,
                    "pkg_md5": mysql_crond_pkg.md5,
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
        mysql_monitor_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLMonitor)
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
                        "db_module_id": instance.db_module_id,
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
                        "db_module_id": instance.db_module_id,
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
                        "db_module_id": instance.db_module_id,
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
                "general": {"runtime_account": {**self.account, **self.proxy_account}},
                "extend": {
                    "pkg": mysql_monitor_pkg.name,
                    "pkg_md5": mysql_monitor_pkg.md5,
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
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.MySQLBackupDemand.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "host": self.ticket_data["ip"],
                    "port": self.ticket_data["port"],
                    "role": self.ticket_data["role"],
                    "backup_type": self.ticket_data["backup_type"],
                    "backup_gsd": self.ticket_data["backup_gsd"],
                    "regex": kwargs["trans_data"]["db_table_filter_regex"],
                    "backup_id": self.ticket_data["backup_id"].__str__(),
                    "bill_id": str(self.ticket_data["uid"]),
                    "custom_backup_dir": self.ticket_data.get("custom_backup_dir", ""),
                    "shard_id": self.ticket_data.get("shard_id", 0),
                },
            },
        }

    def tendb_cluster_remote_switch(self, **kwargs):
        """
        定义拼接TenDB-Cluster集群的remote互切/主故障切换的payload参数
        """
        cluster = Cluster.objects.get(id=self.ticket_data["cluster_id"])

        switch_paris = []
        for tuples in self.ticket_data["switch_tuples"]:
            objs = cluster.storageinstance_set.filter(machine__ip=tuples["master"]["ip"])
            for master in objs:
                slave = StorageInstanceTuple.objects.get(ejector=master).receiver
                switch_paris.append(
                    {
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
                    "port": cluster.proxyinstance_set.first().admin_port,
                    "slave_delay_check": self.ticket_data["is_check_delay"],
                    "force": self.ticket_data["force"],
                    "switch_paris": switch_paris,
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
                    "src_instance": {"host": self.cluster["source_ip"], "port": self.cluster["source_port"]},
                    "change_master": self.cluster["change_master"],
                    "work_id": "",
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
                    "force": self.cluster["change_master_force"],
                    "bin_file": bin_file,
                    "bin_position": bin_position,
                },
            },
        }

    def tendb_recover_binlog_payload(self, **kwargs):
        """
        MYSQL 实例 前滚binglog
        """
        if self.cluster.get("rollback_type", "") == RollbackType.LOCAL_AND_TIME:
            binlog_files = kwargs["trans_data"]["binlog_files"]
            backup_time = kwargs["trans_data"]["backup_time"]
        else:
            binlog_files = self.cluster["binlog_files"]
            backup_time = self.cluster["backup_time"]
        binlog_files_list = binlog_files.split(",")
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

    def get_install_tmp_db_backup_payload(self, **kwargs):
        """
        数据恢复时安装临时备份程序。大部分信息可忽略不计
        """
        db_backup_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.DbBackup)
        cfg = self.__get_dbbackup_config()
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
                    "role": InstanceInnerRole.MASTER.value,
                    "configs": cfg["ini"],
                    "options": cfg["options"],
                    "cluster_address": {},
                    "cluster_id": {},
                    "cluster_type": ClusterType.TenDBHA,
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
        nginx_ip = DBCloudProxy.objects.filter(bk_cloud_id=self.bk_cloud_id).last().internal_address
        bkrepo_url = f"http://{nginx_ip}/apis/proxypass" if self.bk_cloud_id else settings.BKREPO_ENDPOINT_URL

        if self.cluster["is_upload_bkrepo"]:
            fileserver.update(
                {
                    "url": bkrepo_url,
                    "bucket": settings.BKREPO_BUCKET,
                    "username": settings.BKREPO_USERNAME,
                    "password": settings.BKREPO_PASSWORD,
                    "project": settings.BKREPO_PROJECT,
                    "upload_path": BKREPO_SQLFILE_PATH,
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

        nginx_ip = DBCloudProxy.objects.filter(bk_cloud_id=self.bk_cloud_id).last().internal_address
        bkrepo_url = f"http://{nginx_ip}/apis/proxypass" if self.bk_cloud_id else settings.BKREPO_ENDPOINT_URL

        if self.cluster["is_upload_bkrepo"]:
            fileserver.update(
                {
                    "url": bkrepo_url,
                    "bucket": settings.BKREPO_BUCKET,
                    "username": settings.BKREPO_USERNAME,
                    "password": settings.BKREPO_PASSWORD,
                    "project": settings.BKREPO_PROJECT,
                    "upload_path": BKREPO_SQLFILE_PATH,
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
                    "open_area_param": self.cluster["open_area_param"],
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

    def get_adopt_tendbha_storage_payload(self, **kwargs):
        db_version = self.cluster["version"]
        # 这个包其实没有用, 所以只要传包名, 不需要下发
        # 是因为复用了 mysql install actor 需要包名做条件分支
        self.mysql_pkg = Package.get_latest_package(version=db_version, pkg_type=MediumEnum.MySQL)

        drs_account, dbha_account = self.get_super_account()
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.AdoptTendbHAStorage.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "pkg": self.mysql_pkg.name,
                    "pkg_md5": self.mysql_pkg.md5,
                    "ip": kwargs["ip"],
                    "ports": self.cluster["ports"],
                    "mysql_version": self.cluster["version"],
                    "super_account": drs_account,
                    "dbha_account": dbha_account,
                },
            },
        }

    @staticmethod
    def get_adopt_tendbha_proxy_payload(**kwargs):
        return {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.AdoptTendbHAProxy.value,
            "payload": {"general": {}, "extend": {}},  # {"runtime_account": self.account},
        }
