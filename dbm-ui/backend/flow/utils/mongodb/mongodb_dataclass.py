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

import os
from dataclasses import dataclass
from typing import Any, Optional

from django.conf import settings

from backend import env
from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName, OpType, ReqType
from backend.configuration.constants import DBType
from backend.configuration.models import SystemSettings
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.instance_role import InstanceRole
from backend.db_package.models import Package
from backend.flow.consts import (
    DEFAULT_CONFIG_CONFIRM,
    DEFAULT_DB_MODULE_ID,
    ConfigFileEnum,
    ConfigTypeEnum,
    MediumEnum,
    MongoDBActuatorActionEnum,
    MongoDBDefaultAuthDB,
    MongoDBInstanceType,
    MongoDBManagerUser,
    MongoDBTask,
    MongoDBTotalCache,
    MongoDBUserPrivileges,
    MongoOplogSizePercent,
    NameSpaceEnum,
)
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.utils.mongodb import mongodb_script_template
from backend.flow.utils.mongodb.calculate_cluster import get_cache_size, get_oplog_size, machine_order_by_tolerance
from backend.flow.utils.mongodb.mongodb_password import MongoDBPassword
from backend.flow.utils.mongodb.mongodb_repo import MongoRepository


@dataclass()
class ActKwargs:
    """节点私有变量数据类"""

    def __init__(self):
        # 传入流程信息
        self.payload: dict = None
        # 流程id
        self.root_id: int = None
        # 创建单个复制集信息
        self.replicaset_info: dict = None
        # 创建mongos
        self.mongos_info: dict = None
        # 集群类型
        self.cluster_type: str = None
        # db大版本
        self.db_main_version: str = None
        # db发行版本
        self.db_release_version: str = None
        # db发行
        self.db_release: str = None
        # 备份所在目录
        self.file_path: str = None
        # db配置
        self.db_conf: dict = None
        # db的os配置
        self.os_conf: dict = None
        # 安装包以及文件
        self.pkg: Package = None
        # db实例
        self.db_instance: dict = None
        # 管理员用户
        self.manager_users: list = [
            MongoDBManagerUser.DbaUser.value,
            MongoDBManagerUser.AppDbaUser.value,
            MongoDBManagerUser.MonitorUser.value,
            MongoDBManagerUser.AppMonitorUser.value,
        ]
        # 实例角色
        self.instance_role = [
            InstanceRole.MONGO_M1.value,
            InstanceRole.MONGO_M2.value,
            InstanceRole.MONGO_M3.value,
            InstanceRole.MONGO_M4.value,
            InstanceRole.MONGO_M5.value,
            InstanceRole.MONGO_M6.value,
            InstanceRole.MONGO_M7.value,
            InstanceRole.MONGO_M8.value,
            InstanceRole.MONGO_M9.value,
            InstanceRole.MONGO_M10.value,
            InstanceRole.MONGO_BACKUP.value,
        ]

    def __get_define_config(self, namespace: str, conf_file: str, conf_type: str) -> Any:
        """获取一些全局的参数配置"""
        bk_biz_id = str(self.payload["bk_biz_id"])
        data = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": bk_biz_id,
                "level_name": LevelName.APP,
                "level_value": bk_biz_id,
                "conf_file": conf_file,
                "conf_type": conf_type,
                "namespace": namespace,
                "format": FormatType.MAP.value,
            }
        )
        return data["content"]

    def save_conf(self, namespace: str):
        """保存配置到dbconfig"""

        conf_type = ConfigTypeEnum.DBConf.value
        conf_file = "{}-{}".format("Mongodb", self.db_main_version)
        cluster_name = ""
        key_file = ""
        cache_size = ""
        oplog_size = ""
        conf_items = []
        if namespace == ClusterType.MongoReplicaSet.value:
            cluster_name = self.replicaset_info["set_id"]
            key_file = self.replicaset_info["key_file"]
            cache_size = str(self.replicaset_info["cacheSizeGB"])
            oplog_size = str(self.replicaset_info["oplogSizeMB"])
        elif namespace == ClusterType.MongoShardedCluster.value:
            cluster_name = self.payload["cluster_id"]
            key_file = self.payload["key_file"]
            cache_size = str(self.payload["shards"][0]["cacheSizeGB"])
            oplog_size = str(self.payload["shards"][0]["oplogSizeMB"])
            config_cache_size = str(self.payload["config"]["cacheSizeGB"])
            config_oplog_size = str(self.payload["config"]["oplogSizeMB"])
            conf_items.extend(
                [
                    {"conf_name": "config_cacheSizeGB", "conf_value": config_cache_size, "op_type": OpType.UPDATE},
                    {"conf_name": "config_oplogSizeMB", "conf_value": config_oplog_size, "op_type": OpType.UPDATE},
                ]
            )
        conf_items.extend(
            [
                {"conf_name": "key_file", "conf_value": key_file, "op_type": OpType.UPDATE},
                {"conf_name": "cacheSizeGB", "conf_value": cache_size, "op_type": OpType.UPDATE},
                {"conf_name": "oplogSizeMB", "conf_value": oplog_size, "op_type": OpType.UPDATE},
            ]
        )
        DBConfigApi.upsert_conf_item(
            {
                "conf_file_info": {
                    "conf_file": conf_file,
                    "conf_type": conf_type,
                    "namespace": namespace,
                },
                "conf_items": conf_items,
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "confirm": DEFAULT_CONFIG_CONFIRM,
                "req_type": ReqType.SAVE_AND_PUBLISH,
                "bk_biz_id": str(self.payload["bk_biz_id"]),
                "level_name": LevelName.CLUSTER,
                "level_value": cluster_name,
            }
        )

    def get_conf(self, cluster_name: str) -> dict:
        """从dbconfig获取配置"""

        return DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(self.payload["bk_biz_id"]),
                "level_name": LevelName.CLUSTER.value,
                "level_value": cluster_name,
                "conf_file": "{}-{}".format("Mongodb", self.db_main_version),
                "conf_type": ConfigTypeEnum.DBConf.value,
                "namespace": self.cluster_type,
                "format": FormatType.MAP.value,
            }
        )["content"]

    def get_init_info(self):
        """获取初始信息一些信息"""

        # 集群类型
        self.cluster_type = self.payload["cluster_type"]
        # # db大版本
        self.db_main_version = str(self.payload["db_version"].split("-")[1].split(".")[0])
        # db发行版本
        self.db_release_version = self.payload["db_version"]
        # db发行
        self.db_release = self.payload["db_version"].split("-")[0]
        # db版本
        self.payload["db_version"] = self.payload["db_version"].split("-")[1]

    def get_mongodb_conf(self):
        """获取db配置信息"""

        self.db_conf = self.__get_define_config(
            namespace=self.cluster_type,
            conf_type=ConfigTypeEnum.DBConf.value,
            conf_file="{}-{}".format("Mongodb", self.db_main_version),
        )

    def get_mongodb_os_conf(self):
        """获取os配置信息"""

        self.os_conf = self.__get_define_config(
            namespace=NameSpaceEnum.MongoDBCommon.value,
            conf_type=ConfigTypeEnum.Config.value,
            conf_file=ConfigFileEnum.OsConf.value,
        )
        return self.os_conf

    @staticmethod
    def get_mongodb_monitor_conf():
        """获取监控配置信息"""
        bkm_dbm_report = SystemSettings.get_setting_value(key="BKM_DBM_REPORT")
        return {
            "agent_address": env.MYSQL_CROND_AGENT_ADDRESS,
            "beat_path": env.MYSQL_CROND_BEAT_PATH,
            "event_config": {
                "data_id": int(bkm_dbm_report["event"]["data_id"]),
                "token": bkm_dbm_report["event"]["token"],
            },
            "metric_config": {
                "data_id": int(bkm_dbm_report["metric"]["data_id"]),
                "token": bkm_dbm_report["metric"]["token"],
            },
        }

    def get_file_path(self):
        """安装文件存放路径"""

        self.file_path = self.__get_define_config(
            namespace=NameSpaceEnum.MongoDBCommon.value,
            conf_type=ConfigTypeEnum.Config.value,
            conf_file=ConfigFileEnum.OsConf.value,
        )["file_path"]

    def get_backup_dir(self):
        """备份文件存放路径"""

        resp = self.__get_define_config(
            namespace=self.cluster_type,
            conf_type=ConfigTypeEnum.DBConf,
            conf_file="{}-{}".format("Mongodb", self.db_main_version),
        )
        return resp["backup_dir"]

    def get_pkg(self):
        self.pkg = Package.get_latest_package(
            version=self.db_release_version, pkg_type=MediumEnum.MongoDB, db_type=DBType.MongoDB
        )

    @staticmethod
    def get_password(ip: str, port: int, bk_cloud_id: int, username: str) -> str:
        """获取密码"""

        result = MongoDBPassword().get_password_from_db(ip=ip, port=port, bk_cloud_id=bk_cloud_id, username=username)
        if result["password"] is None:
            raise ValueError(
                "get password of user:{} from password service fail, error:{}".format(username, result["info"])
            )
        return result["password"]

    def get_send_media_kwargs(self, media_type: str) -> dict:
        """
        介质下发的kwargs
        media_type: all 所有介质
        media_type: actuator 仅actuator介质
        """

        if self.payload.get("db_version") and not self.db_release and not self.db_release_version:
            # db大版本
            self.db_main_version = str(self.payload["db_version"].split("-")[1].split(".")[0])
            # db发行版本
            self.db_release_version = self.payload["db_version"]
            # db发行
            self.db_release = self.payload["db_version"].split("-")[0]
            # db版本
            self.payload["db_version"] = self.payload["db_version"].split("-")[1]

        file_list = []
        if media_type == "actuator":
            file_list = GetFileList(db_type=DBType.MongoDB).mongodb_actuator_pkg()
        elif media_type == "all":
            file_list = GetFileList(db_type=DBType.MongoDB).mongodb_pkg(db_version=self.db_release_version)
        ip_list = self.payload["hosts"]
        exec_ips = [host["ip"] for host in ip_list]
        return {
            "file_list": file_list,
            "ip_list": ip_list,
            "exec_ips": exec_ips,
            "file_target_path": self.file_path + "/install",
        }

    def get_create_dir_kwargs(self) -> dict:
        """创建dbactuator执行目录的kwargs"""

        return {
            "create_dir": True,
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": self.payload["hosts"][0]["bk_cloud_id"],
            "exec_ip": self.payload["hosts"],
            "db_act_template": {
                "file_path": self.file_path,
                "payload": {},
            },
        }

    def get_os_init_kwargs(self) -> dict:
        """os初始化的kwargs"""

        # 获取os配置
        self.get_mongodb_os_conf()
        # 获取os密码
        user = self.os_conf["user"]
        password = self.get_password(
            ip="0.0.0.0", port=0, bk_cloud_id=self.payload["hosts"][0]["bk_cloud_id"], username=user
        )

        return {
            "init_flag": True,
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": self.payload["hosts"][0]["bk_cloud_id"],
            "exec_ip": self.payload["hosts"],
            "file_target_path": self.file_path + "/install",
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.OsInit,
                "file_path": self.file_path,
                "user": user,
                "group": self.os_conf["group"],
                "data_dir": self.os_conf["install_dir"],
                "backup_dir": self.os_conf["backup_dir"],
                "payload": {
                    "user": user,
                    "password": password,
                },
            },
        }

    def get_install_plugin_kwargs(self, plugin_name: str, new_cluster: bool) -> dict:
        """
        安装蓝鲸插件的kwargs
        new_cluster 是否新集群部署
        """

        if new_cluster:
            ips = [host["ip"] for host in self.payload["hosts"]]
        else:
            ips = [host["ip"] for host in self.payload["plugin_hosts"]]
        return {
            "plugin_name": plugin_name,
            "ips": ips,
            "bk_cloud_id": self.payload["hosts"][0]["bk_cloud_id"],
        }

    def get_install_mongod_kwargs(self, node: dict, cluster_role: str) -> dict:
        """复制集mongod安装的kwargs"""

        # 获取安装包名以及MD5值
        self.get_pkg()
        # 获取配置
        self.get_mongodb_conf()
        self.db_conf["cacheSizeGB"] = self.replicaset_info["cacheSizeGB"]
        self.db_conf["oplogSizeMB"] = self.replicaset_info["oplogSizeMB"]
        if cluster_role:
            key_file = self.payload["key_file"]
        else:
            key_file = self.replicaset_info["key_file"]
        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": node["bk_cloud_id"],
            "exec_ip": node["ip"],
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.mongoDInstall,
                "file_path": self.file_path,
                "payload": {
                    "mediapkg": {
                        "pkg": os.path.basename(self.pkg.path),
                        "pkg_md5": self.pkg.md5,
                    },
                    "ip": node["ip"],
                    "port": self.replicaset_info["port"],
                    "dbVersion": self.payload["db_version"],
                    "instanceType": MongoDBInstanceType.MongoD,
                    "setId": self.replicaset_info["set_id"],
                    "keyFile": key_file,
                    "auth": True,
                    "clusterRole": cluster_role,
                    "dbConfig": self.db_conf,
                },
            },
        }

    def get_install_mongos_kwargs(self, node: dict, replace: bool) -> dict:
        """mongos安装"""

        # 获取安装包名以及MD5值
        self.get_pkg()
        # 获取配置
        self.get_mongodb_conf()
        # 获取configDB配置
        if replace:
            cluster_id = node["cluster_id"]
            mongos_replace_install = True
            config_db = []
        else:
            cluster_id = ""
            mongos_replace_install = False
            config_db = [
                "{}:{}".format(config_node["ip"], str(self.payload["config"]["port"]))
                for config_node in self.payload["config"]["nodes"]
            ]
        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": node["bk_cloud_id"],
            "exec_ip": node["ip"],
            "mongos_replace_install": mongos_replace_install,
            "cluster_id": cluster_id,
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.mongoSInstall,
                "file_path": self.file_path,
                "payload": {
                    "mediapkg": {
                        "pkg": os.path.basename(self.pkg.path),
                        "pkg_md5": self.pkg.md5,
                    },
                    "ip": node["ip"],
                    "port": self.mongos_info["port"],
                    "dbVersion": self.payload["db_version"],
                    "instanceType": MongoDBInstanceType.MongoS,
                    "setId": self.mongos_info["conf_set_id"],
                    "keyFile": self.payload["key_file"],
                    "auth": True,
                    "configDB": config_db,
                    "dbConfig": self.db_conf,
                },
            },
        }

    def get_replicaset_init_kwargs(self, config_svr: bool) -> dict:
        """复制集初始化"""

        priority = {}
        hidden = {}
        instances = [
            "{}:{}".format(node["ip"], str(self.replicaset_info["port"])) for node in self.replicaset_info["nodes"]
        ]
        for index, instance in enumerate(instances):
            if index == len(instances) - 1:
                priority[instance] = 0
                hidden[instance] = True
            else:
                priority[instance] = 1
                hidden[instance] = False

        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": self.replicaset_info["nodes"][0]["bk_cloud_id"],
            "exec_ip": self.replicaset_info["nodes"][0]["ip"],
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.InitReplicaset,
                "file_path": self.file_path,
                "payload": {
                    "ip": self.replicaset_info["nodes"][0]["ip"],
                    "port": self.replicaset_info["port"],
                    "setId": self.replicaset_info["set_id"],
                    "configSvr": config_svr,
                    "ips": instances,
                    "priority": priority,
                    "hidden": hidden,
                },
            },
        }

    def get_add_relationship_to_meta_kwargs(self, replicaset_info: dict) -> dict:
        """添加replicaset关系到meta的kwargs"""

        info = {
            "bk_biz_id": self.payload["bk_biz_id"],
            "major_version": self.db_release_version,
            "creator": self.payload["created_by"],
            "region": self.payload["city"],
            "db_module_id": 0,
            "disaster_tolerance_level": self.payload["disaster_tolerance_level"],
        }

        if self.payload["cluster_type"] == ClusterType.MongoReplicaSet.value:
            info["cluster_type"] = ClusterType.MongoReplicaSet.value
            info["skip_machine"] = replicaset_info["skip_machine"]
            info["immute_domain"] = replicaset_info["nodes"][0]["domain"]
            info["name"] = replicaset_info["set_id"]
            info["alias"] = replicaset_info["alias"]
            info["spec_id"] = self.payload["spec_id"]
            info["spec_config"] = self.payload["spec_config"]
            info["bk_cloud_id"] = replicaset_info["nodes"][0]["bk_cloud_id"]

            # 复制集节点
            info["storages"] = []
            if len(replicaset_info["nodes"]) <= 11:
                for index, node in enumerate(replicaset_info["nodes"]):
                    if index == len(replicaset_info["nodes"]) - 1:
                        info["storages"].append(
                            {
                                "role": self.instance_role[-1],
                                "ip": node["ip"],
                                "port": replicaset_info["port"],
                                "domain": node["domain"],
                            }
                        )
                    else:
                        info["storages"].append(
                            {
                                "role": self.instance_role[index],
                                "ip": node["ip"],
                                "port": replicaset_info["port"],
                                "domain": node["domain"],
                            }
                        )
        elif self.payload["cluster_type"] == ClusterType.MongoShardedCluster.value:
            info["cluster_type"] = ClusterType.MongoShardedCluster.value
            info["name"] = self.payload["cluster_id"]
            info["alias"] = self.payload["alias"]
            info["bk_cloud_id"] = self.payload["config"]["nodes"][0]["bk_cloud_id"]
            info["machine_specs"] = self.payload["machine_specs"]
            info["immute_domain"] = self.payload["mongos"]["domain"]
            # mongos
            info["proxies"] = [
                {"ip": node["ip"], "port": self.payload["mongos"]["port"]} for node in self.payload["mongos"]["nodes"]
            ]
            # config
            info["configs"] = []
            config = {
                "shard": self.payload["config"]["set_id"],
                "nodes": [],
            }
            if len(self.payload["config"]["nodes"]) <= 11:
                for index, node in enumerate(self.payload["config"]["nodes"]):
                    if index == len(self.payload["config"]["nodes"]) - 1:
                        config["nodes"].append(
                            {"ip": node["ip"], "port": self.payload["config"]["port"], "role": self.instance_role[-1]}
                        )
                    else:
                        config["nodes"].append(
                            {
                                "ip": node["ip"],
                                "port": self.payload["config"]["port"],
                                "role": self.instance_role[index],
                            }
                        )
            info["configs"].append(config)

            # shard
            info["storages"] = []
            for shard in self.payload["shards"]:
                storage = {
                    "shard": shard["set_id"],
                    "nodes": [],
                }
                if len(shard["nodes"]) <= 11:
                    for index, node in enumerate(shard["nodes"]):
                        if index == len(shard["nodes"]) - 1:
                            storage["nodes"].append(
                                {"role": self.instance_role[-1], "ip": node["ip"], "port": shard["port"]}
                            )
                        else:
                            storage["nodes"].append(
                                {"role": self.instance_role[index], "ip": node["ip"], "port": shard["port"]}
                            )
                info["storages"].append(storage)
        return info

    def get_add_domain_to_dns_kwargs(self, cluster: bool) -> dict:
        """添加域名到dns的kwargs"""

        if not cluster:
            domains = [
                {
                    "domain": node["domain"],
                    "instance_list": ["{}#{}".format(node["ip"], str(self.replicaset_info["port"]))],
                }
                for node in self.replicaset_info["nodes"]
            ]
            bk_cloud_id = self.replicaset_info["nodes"][0]["bk_cloud_id"]
        else:
            domains = [
                {
                    "domain": self.payload["mongos"]["domain"],
                    "instance_list": ["{}#{}".format(node["ip"], str(self.payload["mongos"]["port"]))],
                }
                for node in self.payload["mongos"]["nodes"]
            ]
            bk_cloud_id = self.payload["mongos"]["nodes"][0]["bk_cloud_id"]
        return {
            "bk_biz_id": self.payload["bk_biz_id"],
            "bk_cloud_id": bk_cloud_id,
            "domains": domains,
        }

    def get_add_shard_to_cluster_kwargs(self) -> dict:
        """把shard添加到cluster的kwargs"""

        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "add_shard_to_cluster": True,
            "bk_cloud_id": self.payload["mongos"]["nodes"][0]["bk_cloud_id"],
            "exec_ip": self.payload["mongos"]["nodes"][0]["ip"],
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.AddShardToCluster,
                "file_path": self.file_path,
                "payload": {
                    "ip": self.payload["mongos"]["nodes"][0]["ip"],
                    "port": self.payload["mongos"]["port"],
                    "adminUsername": MongoDBManagerUser.DbaUser,
                    "shards": self.payload["add_shards"],
                },
            },
        }

    def get_init_exec_script_kwargs(self, script_type: str) -> dict:
        """通过执行脚本"""

        db_init_set_status = False
        create_extra_manager_user_status = False
        if self.payload["cluster_type"] == ClusterType.MongoReplicaSet.value:
            mongo_type = "replicaset"
            set_name = self.replicaset_info["set_id"]
        else:
            mongo_type = "cluster"
            set_name = ""

        if script_type == MongoDBTask.MongoDBExtraUserCreate:
            create_extra_manager_user_status = True
            db_init_set_status = False
            script = mongodb_script_template.mongo_extra_manager_user_create_js_script
        elif script_type == MongoDBTask.MongoDBInitSet:
            create_extra_manager_user_status = False
            db_init_set_status = True
            script = mongodb_script_template.mongo_init_set_js_script

        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "db_init_set": db_init_set_status,
            "create_extra_manager_user": create_extra_manager_user_status,
            "set_name": set_name,
            "bk_cloud_id": self.replicaset_info["nodes"][0]["bk_cloud_id"],
            "exec_ip": self.replicaset_info["nodes"][0]["ip"],
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.MongoExecuteScript,
                "file_path": self.file_path,
                "payload": {
                    "ip": self.replicaset_info["nodes"][0]["ip"],
                    "port": self.replicaset_info["port"],
                    "script": script,
                    "type": mongo_type,
                    "secondary": False,
                    "adminUsername": MongoDBManagerUser.DbaUser.value,
                    "adminPassword": "",
                    "repoUrl": "",
                    "repoUsername": "",
                    "repoToken": "",
                    "repoProject": "",
                    "repoRepo": "",
                    "repoPath": "",
                },
            },
        }

    def get_add_manager_user_kwargs(self) -> dict:
        """创建dba用户"""

        if self.payload["cluster_type"] == ClusterType.MongoReplicaSet.value:
            set_name = self.replicaset_info["set_id"]
        else:
            set_name = ""
        if float(".".join(self.payload["db_version"].split(".")[0:2])) < 2.6:
            privileges = [
                MongoDBUserPrivileges.UserAdminAnyDatabaseRole.value,
                MongoDBUserPrivileges.DbAdminAnyDatabaseRole.value,
                MongoDBUserPrivileges.ReadWriteAnyDatabaseRole.value,
                MongoDBUserPrivileges.ClusterAdminRole.value,
            ]
        else:
            privileges = [MongoDBUserPrivileges.RootRole.value]

        return {
            "create_manager_user": True,
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "set_name": set_name,
            "bk_cloud_id": self.replicaset_info["nodes"][0]["bk_cloud_id"],
            "exec_ip": self.replicaset_info["nodes"][0]["ip"],
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.AddUser,
                "file_path": self.file_path,
                "payload": {
                    "ip": self.replicaset_info["nodes"][0]["ip"],
                    "port": self.replicaset_info["port"],
                    "instanceType": MongoDBInstanceType.MongoD,
                    "username": MongoDBManagerUser.DbaUser,
                    "password": "",
                    "adminUsername": "",
                    "adminPassword": "",
                    "authDb": MongoDBDefaultAuthDB.AuthDB,
                    "dbsPrivileges": [
                        {
                            "db": "admin",
                            "privileges": privileges,
                        }
                    ],
                },
            },
        }

    def get_get_manager_password_kwargs(self) -> dict:
        """获取用户密码"""

        if self.payload["cluster_type"] == ClusterType.MongoReplicaSet.value:
            set_name = self.replicaset_info["set_id"]
        else:
            set_name = ""
        return {"set_trans_data_dataclass": CommonContext.__name__, "set_name": set_name, "users": self.manager_users}

    def get_add_password_to_db_kwargs(self, usernames: list, info: dict) -> dict:
        """添加密码到db"""

        if self.payload["cluster_type"] == ClusterType.MongoReplicaSet.value:
            set_name = self.replicaset_info["set_id"]
        else:
            set_name = ""

        nodes = [
            {"ip": node["ip"], "port": info["port"], "bk_cloud_id": node["bk_cloud_id"]} for node in info["nodes"]
        ]
        return {"nodes": nodes, "usernames": usernames, "set_name": set_name, "operator": self.payload["created_by"]}

    def get_cluster_info_user(self, cluster_id: int, admin_user: str):
        """创建/删除用户获取cluster信息"""

        # 获取集群信息
        cluster_info = MongoRepository().fetch_one_cluster(withDomain=False, id=cluster_id)
        bk_cloud_id = cluster_info.bk_cloud_id
        self.cluster_type = cluster_info.cluster_type
        exec_ip: str = None
        port: int = None
        instance_type: str = None
        if cluster_info.cluster_type == ClusterType.MongoReplicaSet.value:
            exec_ip = cluster_info.get_shards()[0].members[0].ip
            port = int(cluster_info.get_shards()[0].members[0].port)
            instance_type = MongoDBInstanceType.MongoD
        elif cluster_info.cluster_type == ClusterType.MongoShardedCluster.value:
            exec_ip = cluster_info.get_mongos()[0].ip
            port = int(cluster_info.get_mongos()[0].port)
            instance_type = MongoDBInstanceType.MongoS

        # 获取用户密码
        password = self.get_password(ip=exec_ip, port=port, bk_cloud_id=bk_cloud_id, username=admin_user)
        self.payload["db_version"] = cluster_info.major_version
        self.payload["hosts"] = [{"ip": exec_ip, "bk_cloud_id": bk_cloud_id}]
        self.payload["bk_cloud_id"] = bk_cloud_id
        self.payload["port"] = port
        self.payload["instance_type"] = instance_type
        self.payload["admin_password"] = password
        self.payload["region"] = cluster_info.region
        # 获取file_path
        self.get_file_path()

    def get_user_kwargs(self, create: bool, admin_user: str, info: dict) -> dict:
        """用户"""

        if create:
            # 创建
            return {
                "set_trans_data_dataclass": CommonContext.__name__,
                "get_trans_data_ip_var": None,
                "bk_cloud_id": self.payload["bk_cloud_id"],
                "exec_ip": self.payload["hosts"][0]["ip"],
                "db_act_template": {
                    "action": MongoDBActuatorActionEnum.AddUser,
                    "file_path": self.file_path,
                    "payload": {
                        "ip": self.payload["hosts"][0]["ip"],
                        "port": self.payload["port"],
                        "instanceType": self.payload["instance_type"],
                        "username": info["username"],
                        "password": info["password"],
                        "adminUsername": admin_user,
                        "adminPassword": self.payload["admin_password"],
                        "authDb": info["auth_db"],
                        "dbsPrivileges": info["rule_sets"],
                    },
                },
            }
        else:
            # 删除
            return {
                "set_trans_data_dataclass": CommonContext.__name__,
                "get_trans_data_ip_var": None,
                "bk_cloud_id": self.payload["bk_cloud_id"],
                "exec_ip": self.payload["hosts"][0]["ip"],
                "db_act_template": {
                    "action": MongoDBActuatorActionEnum.DeleteUser,
                    "file_path": self.file_path,
                    "payload": {
                        "ip": self.payload["hosts"][0]["ip"],
                        "port": self.payload["port"],
                        "instanceType": self.payload["instance_type"],
                        "username": info["username"],
                        "adminUsername": admin_user,
                        "adminPassword": self.payload["admin_password"],
                        "authDb": info["auth_db"],
                    },
                },
            }

    def get_exec_script_kwargs(self, cluster_id: int, admin_user: str, script: dict) -> dict:
        """执行脚本"""

        db_type = ""
        if self.cluster_type == ClusterType.MongoReplicaSet.value:
            db_type = "replicaset"
        elif self.cluster_type == ClusterType.MongoShardedCluster.value:
            db_type = "cluster"
        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": self.payload["bk_cloud_id"],
            "exec_ip": self.payload["hosts"][0]["ip"],
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.MongoExecuteScript,
                "file_path": self.file_path,
                "payload": {
                    "ip": self.payload["hosts"][0]["ip"],
                    "port": self.payload["port"],
                    "script": script["script_content"],
                    "scriptName": script["script_name"],
                    "Type": db_type,
                    "secondary": False,
                    "adminUsername": admin_user,
                    "adminPassword": self.payload["admin_password"],
                    "repoUrl": settings.BKREPO_ENDPOINT_URL,
                    "repoUsername": settings.BKREPO_USERNAME,
                    "repoToken": settings.BKREPO_PASSWORD,
                    "repoProject": settings.BKREPO_PROJECT,
                    "repoRepo": settings.BKREPO_BUCKET,
                    "repoPath": self.payload["rules"][self.payload["cluster_ids"].index(cluster_id)]["path"],
                },
            },
        }

    def get_set_dns_resolv_kwargs(self) -> dict:
        """机器设置dns解析"""

        return {
            "force": True,
            "ip": self.payload["hosts"][0]["ip"],
            "bk_biz_id": str(self.payload["bk_biz_id"]),
            "bk_cloud_id": str(self.payload["hosts"][0]["bk_cloud_id"]),
            "bk_city": self.payload["region"],
        }

    def get_hosts_deinstall(self):
        """获取所有需要卸载的cluster的hosts"""

        hosts = set()
        bk_cloud_id: int = None
        for cluster_id in self.payload["cluster_ids"]:
            cluster_info = MongoRepository().fetch_one_cluster(withDomain=False, id=cluster_id)
            if cluster_info.cluster_type == ClusterType.MongoReplicaSet.value:
                shard = cluster_info.get_shards()[0]
                bk_cloud_id = shard.members[0].bk_cloud_id
                for member in shard.members:
                    hosts.add(member.ip)
            elif cluster_info.cluster_type == ClusterType.MongoShardedCluster.value:
                mongos = cluster_info.get_mongos()
                shards = cluster_info.get_shards()
                config = cluster_info.get_config()
                bk_cloud_id = mongos[0].bk_cloud_id
                for mongo in mongos:
                    hosts.add(mongo.ip)
                for member in config.members:
                    hosts.add(member.ip)
                for shard in shards:
                    for member in shard.members:
                        hosts.add(member.ip)
        list_hosts = []
        for host in hosts:
            list_hosts.append({"ip": host, "bk_cloud_id": bk_cloud_id})
        self.payload["hosts"] = list_hosts

    def get_cluster_info_deinstall(self, cluster_id: int):
        """卸载流程获取cluster信息"""

        cluster_info = MongoRepository().fetch_one_cluster(withDomain=True, id=cluster_id)
        self.payload["cluster_type"] = cluster_info.cluster_type
        self.payload["set_id"] = cluster_info.name
        self.payload["cluster_name"] = cluster_info.name
        self.payload["bk_cloud_id"] = cluster_info.bk_cloud_id
        nodes = []
        if cluster_info.cluster_type == ClusterType.MongoReplicaSet.value:
            backup_node = {}
            for member in cluster_info.get_shards()[0].members:
                if member.role == InstanceRole.MONGO_BACKUP.value:
                    backup_node = {
                        "ip": member.ip,
                        "port": int(member.port),
                        "bk_cloud_id": member.bk_cloud_id,
                        "domain": member.domain,
                        "instance_role": member.role,
                    }
                    continue
                nodes.append(
                    {
                        "ip": member.ip,
                        "port": int(member.port),
                        "bk_cloud_id": member.bk_cloud_id,
                        "domain": member.domain,
                        "instance_role": member.role,
                    }
                )
            nodes.append(backup_node)
            self.payload["nodes"] = nodes
        elif cluster_info.cluster_type == ClusterType.MongoShardedCluster.value:
            mongos = cluster_info.get_mongos()
            shards = cluster_info.get_shards()
            config = cluster_info.get_config()
            mongos_nodes = []
            shards_nodes = []
            config_nodes = []
            for mongo in mongos:
                mongos_nodes.append(
                    {"ip": mongo.ip, "port": int(mongo.port), "bk_cloud_id": mongo.bk_cloud_id, "domain": mongo.domain}
                )
            for shard in shards:
                shard_info = {"shard": shard.set_name}
                nodes = []
                backup_node = {}
                for member in shard.members:
                    if member.role == InstanceRole.MONGO_BACKUP.value:
                        backup_node = {
                            "ip": member.ip,
                            "port": int(member.port),
                            "bk_cloud_id": member.bk_cloud_id,
                            "instance_role": member.role,
                        }
                        continue
                    nodes.append(
                        {
                            "ip": member.ip,
                            "port": int(member.port),
                            "bk_cloud_id": member.bk_cloud_id,
                            "instance_role": member.role,
                        }
                    )
                nodes.append(backup_node)
                shard_info["nodes"] = nodes
                shards_nodes.append(shard_info)
            backup_node = {}
            for member in config.members:
                if member.role == InstanceRole.MONGO_BACKUP.value:
                    backup_node = {
                        "ip": member.ip,
                        "port": int(member.port),
                        "bk_cloud_id": member.bk_cloud_id,
                        "instance_role": member.role,
                    }
                    continue
                config_nodes.append(
                    {
                        "ip": member.ip,
                        "port": int(member.port),
                        "bk_cloud_id": member.bk_cloud_id,
                        "instance_role": member.role,
                    }
                )
            config_nodes.append(backup_node)
            self.payload["mongos_nodes"] = mongos_nodes
            self.payload["shards_nodes"] = shards_nodes
            self.payload["config_nodes"] = config_nodes

    def get_mongo_deinstall_kwargs(
        self, node_info: dict, instance_type: str, nodes_info: list, force: bool, rename_dir: bool
    ) -> dict:
        """卸载mongo的kwargs"""

        nodes = []
        for node in nodes_info:
            nodes.append(node["ip"])
        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": self.payload["bk_cloud_id"],
            "exec_ip": node_info["ip"],
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.MongoDeInstall,
                "file_path": self.file_path,
                "payload": {
                    "ip": node_info["ip"],
                    "port": node_info["port"],
                    "setId": self.payload["set_id"],
                    "nodeInfo": nodes,
                    "instanceType": instance_type,
                    "force": force,
                    "renameDir": rename_dir,
                },
            },
        }

    def get_meta_deinstall_kwargs(self, cluster_id: int) -> dict:
        """卸载集群修改元数据的kwarg"""

        return {
            "created_by": self.payload["created_by"],
            "immute_domain": "",
            "cluster_id": cluster_id,
            "bk_biz_id": self.payload["bk_biz_id"],
        }

    def get_delete_domain_kwargs(self):
        """删除dns"""

        del_domains = []
        if self.payload["cluster_type"] == ClusterType.MongoReplicaSet.value:
            for node in self.payload["nodes"]:
                del_domains.append(
                    {"domain": node["domain"], "del_instance_list": ["{}#{}".format(node["ip"], str(node["port"]))]}
                )
        elif self.payload["cluster_type"] == ClusterType.MongoShardedCluster.value:
            del_instance_list = [
                "{}#{}".format(node["ip"], str(node["port"])) for node in self.payload["mongos_nodes"]
            ]
            del_domains.append(
                {"domain": self.payload["mongos_nodes"][0]["domain"], "del_instance_list": del_instance_list}
            )

        return {
            "bk_cloud_id": self.payload["bk_cloud_id"],
            "bk_biz_id": self.payload["bk_biz_id"],
            "del_domains": del_domains,
        }

    def get_delete_pwd_kwargs(self):
        """删除密码"""

        instances = []
        if self.payload["cluster_type"] == ClusterType.MongoReplicaSet.value:
            for node in self.payload["nodes"]:
                instances.append({"ip": node["ip"], "port": node["port"], "bk_cloud_id": node["bk_cloud_id"]})
        elif self.payload["cluster_type"] == ClusterType.MongoShardedCluster.value:
            for node in self.payload["mongos_nodes"]:
                instances.append({"ip": node["ip"], "port": node["port"], "bk_cloud_id": node["bk_cloud_id"]})
            for node in self.payload["config_nodes"]:
                instances.append({"ip": node["ip"], "port": node["port"], "bk_cloud_id": node["bk_cloud_id"]})
            for shard in self.payload["shards_nodes"]:
                for node in shard["nodes"]:
                    instances.append({"ip": node["ip"], "port": node["port"], "bk_cloud_id": node["bk_cloud_id"]})
        return {
            "instances": instances,
            "usernames": self.manager_users,
        }

    def get_restart_info_by_hosts(self):
        """获取所有需要restart的主机信息"""

        # 去重主机
        hosts = []
        for info in self.payload["infos"]:
            host_info = {"ip": info["ip"], "bk_cloud_id": info["bk_cloud_id"]}
            if host_info not in hosts:
                hosts.append(host_info)

        # 获取主机对应的实例
        instances_by_ip = []
        for host in hosts:
            instances = []
            for info in self.payload["infos"]:
                if info["ip"] == host["ip"] and info["bk_cloud_id"] == host["bk_cloud_id"]:
                    instances.append(
                        {
                            "cluster_id": info["cluster_id"],
                            "port": info["port"],
                            "role": info["role"],
                        }
                    )
            instances_by_ip.append(
                {
                    "hosts": [{"ip": host["ip"], "bk_cloud_id": host["bk_cloud_id"]}],
                    "instances": instances,
                }
            )
        self.payload["instances_by_ip"] = instances_by_ip

    def get_instance_restart_kwargs(
        self,
        host: dict,
        instance: dict,
        cache_size_gb: int,
        mongos_conf_db_old: str,
        mongos_conf_db_new: str,
        cluster_id: int,
        only_change_param: bool,
    ) -> dict:
        """重启实例的kwargs"""

        # 获取信息
        ip = host["ip"]
        bk_cloud_id = host["bk_cloud_id"]
        port = instance["port"]
        username = MongoDBManagerUser.DbaUser.value
        if instance["role"] == MongoDBInstanceType.MongoS.value:
            instance_type = MongoDBInstanceType.MongoS.value
        else:
            instance_type = MongoDBInstanceType.MongoD.value
            # 获取密码
        password = self.get_password(ip=ip, port=port, bk_cloud_id=bk_cloud_id, username=username)
        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": bk_cloud_id,
            "exec_ip": ip,
            "cluster_id": cluster_id,
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.MongoRestart,
                "file_path": self.file_path,
                "payload": {
                    "ip": ip,
                    "port": instance["port"],
                    "instanceType": instance_type,
                    "auth": True,
                    "cacheSizeGB": cache_size_gb,
                    "mongoSConfDbOld": mongos_conf_db_old,
                    "mongoSConfDbNew": mongos_conf_db_new,
                    "adminUsername": username,
                    "adminPassword": password,
                    "onlyChangeParam": only_change_param,
                },
            },
        }

    def get_host_replace(self, mongodb_type: str, info: dict):
        """替换获取host信息"""

        hosts = []
        plugin_hosts = []
        if mongodb_type == ClusterType.MongoReplicaSet.value:
            # 源ip
            hosts.append({"ip": info["ip"], "bk_cloud_id": info["bk_cloud_id"]})
            # 目标ip
            hosts.append({"ip": info["target"]["ip"], "bk_cloud_id": info["target"]["bk_cloud_id"]})
            plugin_hosts.append({"ip": info["target"]["ip"], "bk_cloud_id": info["target"]["bk_cloud_id"]})
            # db版本
            self.payload["db_version"] = info["instances"][0]["db_version"]

        elif mongodb_type == ClusterType.MongoShardedCluster.value:
            for mongos in info["mongos"]:
                # 源ip
                hosts.append({"ip": mongos["ip"], "bk_cloud_id": mongos["bk_cloud_id"]})
                # 目标ip
                hosts.append({"ip": mongos["target"]["ip"], "bk_cloud_id": mongos["target"]["bk_cloud_id"]})
                plugin_hosts.append({"ip": mongos["target"]["ip"], "bk_cloud_id": mongos["target"]["bk_cloud_id"]})
            for config in info["mongo_config"]:
                # 源ip
                hosts.append({"ip": config["ip"], "bk_cloud_id": config["bk_cloud_id"]})
                # 目标ip
                hosts.append({"ip": config["target"]["ip"], "bk_cloud_id": config["target"]["bk_cloud_id"]})
                plugin_hosts.append({"ip": config["target"]["ip"], "bk_cloud_id": config["target"]["bk_cloud_id"]})
            for shard in info["mongodb"]:
                # 源ip
                hosts.append({"ip": shard["ip"], "bk_cloud_id": shard["bk_cloud_id"]})
                # 目标ip
                hosts.append({"ip": shard["target"]["ip"], "bk_cloud_id": shard["target"]["bk_cloud_id"]})
                plugin_hosts.append({"ip": shard["target"]["ip"], "bk_cloud_id": shard["target"]["bk_cloud_id"]})
            # 获取参数
            if info["mongos"]:
                self.payload["db_version"] = info["mongos"][0]["instances"][0]["db_version"]
            elif info["mongo_config"]:
                self.payload["db_version"] = info["mongo_config"][0]["instances"][0]["db_version"]
            elif info["mongodb"]:
                self.payload["db_version"] = info["mongodb"][0]["instances"][0]["db_version"]

        self.payload["hosts"] = hosts
        self.payload["plugin_hosts"] = plugin_hosts

    def get_mongos_host_replace(self):
        """替换configDB获取mongos主机"""

        for mongos in self.payload["mongos_nodes"]:
            self.payload["hosts"].append({"ip": mongos["ip"], "bk_cloud_id": mongos["bk_cloud_id"]})

    @staticmethod
    def get_config_set_name_replace(cluster_id) -> str:
        """获取分片集群的configDB的set_id"""

        return MongoRepository().fetch_one_cluster(withDomain=False, id=cluster_id).get_config().set_name

    def calc_param_replace(self, info: dict, instance_num: int):
        """ "计算参数"""

        self.replicaset_info = {}
        # 同机器的实例数
        if instance_num:
            instance_count = instance_num
        else:
            instance_count = len(info["instances"])
        # 计算cacheSizeGB和oplogSizeMB
        self.replicaset_info["cacheSizeGB"] = get_cache_size(
            memory_size=info["target"]["bk_mem"],
            cache_percent=MongoDBTotalCache.Cache_Percent.value,
            num=instance_count,
        )
        data_disk = "/data1"
        if info["target"]["storage_device"].get("/data1"):
            data_disk = "/data1"
        elif info["target"]["storage_device"].get("/data"):
            data_disk = "/data"
        self.replicaset_info["oplogSizeMB"] = get_oplog_size(
            disk_size=info["target"]["storage_device"].get(data_disk)["size"],
            oplog_percent=MongoOplogSizePercent.Oplog_Percent.value,
            num=instance_count,
        )

    def get_instance_replace_kwargs(self, info: dict, source_down: bool) -> dict:
        """替换的kwargs"""

        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": info["bk_cloud_id"],
            "exec_ip": info["ip"],
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.MongoDReplace,
                "file_path": self.file_path,
                "payload": {
                    "ip": info["ip"],
                    "port": self.db_instance["port"],
                    "sourceIP": info["ip"],
                    "sourcePort": self.db_instance["port"],
                    "sourceDown": source_down,
                    "adminUsername": MongoDBManagerUser.DbaUser.value,
                    "adminPassword": self.get_password(
                        info["ip"], self.db_instance["port"], info["bk_cloud_id"], MongoDBManagerUser.DbaUser.value
                    ),
                    "targetIP": info["target"]["ip"],
                    "targetPort": self.db_instance["port"],
                    "targetPriority": "",
                    "targetHidden": "",
                },
            },
        }

    def get_change_meta_replace_kwargs(self, info: dict, instance: dict) -> dict:
        """
        修改元数据的kwargs
        复制集有instance参数
        mongos，shard，configDB无instance参数
        """

        mongos = []
        mongodb = []
        mongo_config = []
        cluster_id = 0
        if info["db_type"] != "mongos":
            change_meta = {
                "ip": info["ip"],
                "spec_id": info["spec_id"],
                "spec_config": info["spec_config"],
                "target": {"ip": info["target"]["ip"], "spec_id": info["target"]["spec_id"]},
            }
            if info["db_type"] == "cluster_mongodb":
                mongodb.append(change_meta)
                cluster_id = info["instances"][0]["cluster_id"]
            elif info["db_type"] == "replicaset_mongodb":
                mongodb.append(change_meta)
                cluster_id = instance["cluster_id"]
            elif info["db_type"] == "mongo_config":
                mongo_config.append(change_meta)
                cluster_id = info["instances"][0]["cluster_id"]
        else:
            for mongos_info_by_ip in info["mongos"]:
                mongos.append(
                    {
                        "ip": mongos_info_by_ip["ip"],
                        "spec_id": mongos_info_by_ip["spec_id"],
                        "spec_config": mongos_info_by_ip["spec_config"],
                        "target": {
                            "ip": mongos_info_by_ip["target"]["ip"],
                            "spec_id": mongos_info_by_ip["target"]["spec_id"],
                        },
                    }
                )
            cluster_id = info["mongos"][0]["instances"][0]["cluster_id"]

        return {
            "created_by": info["created_by"],
            "immute_domain": "",
            "cluster_id": cluster_id,
            "bk_biz_id": info["bk_biz_id"],
            "mongos": mongos,
            "mongodb": mongodb,
            "mongo_config": mongo_config,
        }

    def get_password_from_db(self, info: dict) -> dict:
        """从db中获取密码"""

        passwords = {}
        for username in info["usernames"]:
            passwords[username] = self.get_password(
                ip=self.payload["nodes"][0]["ip"],
                port=self.payload["nodes"][0]["port"],
                bk_cloud_id=self.payload["nodes"][0]["bk_cloud_id"],
                username=username,
            )
        info["passwords"] = passwords
        return info

    def get_host_scale_mongos(self, info: dict, increase: bool):
        """cluster增加或减少mongos获取主机"""

        if increase:
            hosts = [{"ip": mongos["ip"], "bk_cloud_id": mongos["bk_cloud_id"]} for mongos in info["mongos"]]
            self.payload["plugin_hosts"] = hosts
        else:
            hosts = [{"ip": mongos["ip"], "bk_cloud_id": mongos["bk_cloud_id"]} for mongos in info["reduce_nodes"]]
        self.payload["hosts"] = hosts

    def get_change_meta_mongos_kwargs(self, increase: bool) -> dict:
        """增加或减少修改mongos的元数据的kwargs"""

        mongos_add = []
        mongos_del = []
        if increase:
            mongos_add = [
                {
                    "ip": mongos["ip"],
                    "spec_id": self.mongos_info["resource_spec"]["mongos"]["id"],
                    "spec_config": self.mongos_info["resource_spec"]["mongos"],
                }
                for mongos in self.mongos_info["nodes"]
            ]
        else:
            mongos_del = [
                {
                    "ip": mongos["ip"],
                }
                for mongos in self.mongos_info["nodes"]
            ]

        return {
            "created_by": self.payload["created_by"],
            "immute_domain": self.payload["mongos"]["domain"],
            "cluster_id": self.mongos_info["cluster_id"],
            "bk_biz_id": self.payload["bk_biz_id"],
            "mongos_add": mongos_add,
            "mongos_del": mongos_del,
        }

    def calc_scale(self, info: dict) -> dict:
        """容量变更计算cluster对应关系"""

        # 获取副本集老实例信息
        cluster_id = info["cluster_id"]
        self.get_cluster_info_deinstall(cluster_id=cluster_id)
        if self.payload["cluster_type"] == ClusterType.MongoReplicaSet.value:
            # 获取副本集新机器的顺序 副本集容量变更独占机器
            mongodb_host_order_by_tolerance = machine_order_by_tolerance(
                disaster_tolerance_level=info["disaster_tolerance_level"], machine_set=info["mongodb"]
            )
            instances = self.payload["nodes"]
            instance_relationships = []
            for index, host in enumerate(mongodb_host_order_by_tolerance):
                instance_relationships.append(
                    {
                        "created_by": self.payload["created_by"],
                        "bk_biz_id": self.payload["bk_biz_id"],
                        "ip": instances[index]["ip"],
                        "bk_cloud_id": instances[index]["bk_cloud_id"],
                        "target": {
                            "ip": host["ip"],
                            "bk_cloud_id": host["bk_cloud_id"],
                            "spec_id": info["machine_specs"]["mongodb"]["spec_id"],
                            "spec_config": info["machine_specs"]["mongodb"]["spec_config"],
                            "bk_cpu": host["bk_cpu"],
                            "bk_mem": host["bk_mem"],
                            "storage_device": host["storage_device"],
                        },
                        "instances": [
                            {
                                "cluster_id": cluster_id,
                                "cluster_name": self.payload["set_id"],
                                "db_version": info["db_version"],
                                "domain": instances[index]["domain"],
                                "port": instances[index]["port"],
                            }
                        ],
                    }
                )
            self.payload["instance_relationships"] = instance_relationships

        elif self.payload["cluster_type"] == ClusterType.MongoShardedCluster.value:
            # 获取新机器顺序
            mongodb_host_set = []
            for host_set in info["mongodb"]:
                mongodb_host_order_by_tolerance = machine_order_by_tolerance(
                    disaster_tolerance_level=info["disaster_tolerance_level"], machine_set=host_set
                )
                mongodb_host_set.append(mongodb_host_order_by_tolerance)
            # 每台机器部署的实例数
            node_replica_count = int(info["shards_num"] / info["shard_machine_group"])
            # 所有shard的实例对应关系
            shards_instance_relationships = []
            # 分配机器
            for index, shard_host_set in enumerate(mongodb_host_set):
                # 每组机器获取对应的shards
                shards = self.payload["shards_nodes"][index * node_replica_count : (index + 1) * node_replica_count]
                for shard in shards:
                    # 单个shard的实例对应关系
                    shard_instance_relationships = []
                    for node_index, node in enumerate(shard["nodes"]):
                        shard_instance_relationships.append(
                            {
                                "created_by": self.payload["created_by"],
                                "bk_biz_id": self.payload["bk_biz_id"],
                                "node_replica_count": node_replica_count,
                                "ip": node["ip"],
                                "bk_cloud_id": node["bk_cloud_id"],
                                "target": {
                                    "ip": shard_host_set[node_index]["ip"],
                                    "bk_cloud_id": shard_host_set[node_index]["bk_cloud_id"],
                                    "spec_id": info["machine_specs"]["mongodb"]["spec_id"],
                                    "spec_config": info["machine_specs"]["mongodb"]["spec_config"],
                                    "bk_cpu": shard_host_set[node_index]["bk_cpu"],
                                    "bk_mem": shard_host_set[node_index]["bk_mem"],
                                    "storage_device": shard_host_set[node_index]["storage_device"],
                                },
                                "instances": [
                                    {
                                        "cluster_id": cluster_id,
                                        "cluster_name": self.payload["cluster_name"],
                                        "seg_range": shard["shard"],
                                        "db_version": info["db_version"],
                                        "domain": node.get("domain", ""),
                                        "port": node["port"],
                                    }
                                ],
                            }
                        )
                    shards_instance_relationships.append(shard_instance_relationships)
            self.payload["shards_instance_relationships"] = shards_instance_relationships

    def get_host_scale(self, mongodb_type: str, info: dict):
        """容量变更获取host信息"""

        hosts = []
        plugin_hosts = []
        if mongodb_type == ClusterType.MongoReplicaSet.value:
            for instance_relationship in self.payload["instance_relationships"]:
                # 源ip
                hosts.append({"ip": instance_relationship["ip"], "bk_cloud_id": instance_relationship["bk_cloud_id"]})
                # 目标ip
                hosts.append(
                    {
                        "ip": instance_relationship["target"]["ip"],
                        "bk_cloud_id": instance_relationship["target"]["bk_cloud_id"],
                    }
                )
                plugin_hosts.append(
                    {
                        "ip": instance_relationship["target"]["ip"],
                        "bk_cloud_id": instance_relationship["target"]["bk_cloud_id"],
                    }
                )
                # db版本
            self.payload["db_version"] = self.payload["instance_relationships"][0]["instances"][0]["db_version"]
            self.db_main_version = self.payload["db_version"].split("-")[1].split(".")[0]

        elif mongodb_type == ClusterType.MongoShardedCluster.value:
            hosts_set = set()
            plugin_hosts_set = set()
            bk_cloud_id = info["mongodb"][0][0]["bk_cloud_id"]
            for shards_instance_relationships in self.payload["shards_instance_relationships"]:
                for instance_relationship in shards_instance_relationships:
                    hosts_set.add(instance_relationship["ip"])
                    hosts_set.add(instance_relationship["target"]["ip"])
                    plugin_hosts_set.add(instance_relationship["target"]["ip"])
            for host in hosts_set:
                hosts.append({"ip": host, "bk_cloud_id": bk_cloud_id})
            for host in plugin_hosts_set:
                plugin_hosts.append({"ip": host, "bk_cloud_id": bk_cloud_id})
            self.payload["db_version"] = info["db_version"]
            self.db_main_version = self.payload["db_version"].split("-")[1].split(".")[0]
        self.payload["hosts"] = hosts
        self.payload["plugin_hosts"] = plugin_hosts

    def get_scale_change_meta(self, info: dict, instance: dict) -> dict:
        """容量变更修改meta"""

        return {
            "created_by": self.payload["created_by"],
            "immute_domain": "",
            "cluster_id": instance["cluster_id"],
            "bk_biz_id": self.payload["bk_biz_id"],
            "mongodb": [
                {
                    "ip": info["ip"],
                    "port": instance["port"],
                    "target": {
                        "ip": info["target"]["ip"],
                        "port": instance["port"],
                        "spec_id": info["target"]["spec_id"],
                        "spec_config": info["target"]["spec_config"],
                    },
                }
            ],
        }

    def get_host_increase_node(self, info: dict):
        """cluster增加node获取主机"""

        hosts = []
        for host in info["add_shard_nodes"]:
            hosts.append({"ip": host["ip"], "bk_cloud_id": host["bk_cloud_id"]})
        # db版本
        self.payload["db_version"] = info["db_version"]
        self.db_main_version = self.payload["db_version"].split("-")[1].split(".")[0]
        self.payload["hosts"] = hosts
        self.payload["plugin_hosts"] = hosts

    def calc_increase_node(self, info: dict):
        """增加节点计算cluster对应关系"""

        # 以IP为维度获取cluster对应关系
        if self.payload["cluster_type"] == ClusterType.MongoReplicaSet.value:
            if len(info["cluster_ids"]) > 1:
                reuse_machine = True
            else:
                reuse_machine = False
            add_shard_node = info["add_shard_node"]
            index = info["add_shard_node"]["node_index"]
            current_shard_nodes_num = info["current_shard_nodes_num"]
            self.payload["replicaset_set"] = []
            self.payload["scale_outs"] = []
            for cluster_id in info["cluster_ids"]:
                self.get_cluster_info_deinstall(cluster_id=cluster_id)
                port = self.payload["nodes"][0]["port"]
                role = self.instance_role[current_shard_nodes_num - 1 + index]
                node_name = role
                ip = add_shard_node["ip"]
                bk_cloud_id = add_shard_node["bk_cloud_id"]
                # self.payload["cluster_name"] 为 "app-clustername"

                domain = "{}.{}.{}.db".format(
                    node_name,
                    self.payload["cluster_name"].replace("{}-".format(self.payload["bk_app_abbr"]), ""),
                    self.payload["bk_app_abbr"],
                )
                db_instance = {
                    "cluster_id": cluster_id,
                    "role": role,
                    "ip": ip,
                    "port": port,
                    "bk_cloud_id": bk_cloud_id,
                    "domain": domain,
                }
                scale_out_instance = {
                    "cluster_id": cluster_id,
                    "shard": "",
                    "role": role,
                    "ip": ip,
                    "port": port,
                    "domain": domain,
                    "spec_id": info["resource_spec"]["shard_nodes"]["spec_id"],
                    "sepc_config": info["resource_spec"]["shard_nodes"],
                    "reuse_machine": reuse_machine,
                }
                self.payload["replicaset_set"].append(db_instance)
                self.payload["scale_outs"].append(scale_out_instance)
        elif self.payload["cluster_type"] == ClusterType.MongoShardedCluster.value:
            cluster_id = info["cluster_id"]
            self.get_cluster_info_deinstall(cluster_id=info["cluster_id"])
            self.payload["shards_instance_relationships_by_ip"] = {}
            self.payload["scale_out_instances_by_ip"] = {}
            # 每台机器部署的实例数
            node_replica_count = info["node_replica_count"]
            if node_replica_count > 1:
                reuse_machine = True
            else:
                reuse_machine = False
            # cluster的shard每增加一个节点所需要的机器数
            host_num_one_node = int(info["shards_num"] / node_replica_count)
            # 分配机器，每增加一个node取一次对应的机器
            for node in range(info["add_shard_nodes_num"]):
                for index, host in enumerate(
                    info["add_shard_nodes"][node * host_num_one_node : (node + 1) * host_num_one_node]
                ):
                    # 把机器分配对应的shard
                    shards = self.payload["shards_nodes"][
                        index * node_replica_count : (index + 1) * node_replica_count
                    ]
                    db_instances_by_ip = []
                    scale_out_instances_by_ip = []
                    for shard in shards:
                        # 单个shard的实例对应关系
                        current_node_num = len(shard["nodes"])
                        role = self.instance_role[current_node_num - 1 + node]
                        ip = host["ip"]
                        port = shard["nodes"][0]["port"]
                        db_instances_by_ip.append(
                            {
                                "cluster_id": cluster_id,
                                "ip": ip,
                                "bk_cloud_id": host["bk_cloud_id"],
                                "role": role,
                                "cluster_name": self.payload["cluster_name"],
                                "seg_range": shard["shard"],
                                "db_version": info["db_version"],
                                "port": shard["nodes"][0]["port"],
                            }
                        )
                        scale_out_instances_by_ip.append(
                            {
                                "cluster_id": cluster_id,
                                "shard": shard["shard"],
                                "role": role,
                                "ip": ip,
                                "port": port,
                                "domain": "",
                                "spec_id": info["resource_spec"]["shard_nodes"]["spec_id"],
                                "sepc_config": info["resource_spec"]["shard_nodes"],
                                "reuse_machine": reuse_machine,
                            }
                        )
                    self.payload["shards_instance_relationships_by_ip"][host["ip"]] = db_instances_by_ip
                    self.payload["scale_out_instances_by_ip"][host["ip"]] = scale_out_instances_by_ip

    def get_increase_node_kwargs(self, info: dict) -> dict:
        """添加node的kwargs"""

        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": info["exec_bk_cloud_id"],
            "exec_ip": info["exec_ip"],
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.MongoDReplace,
                "file_path": self.file_path,
                "payload": {
                    "ip": info["ip"],
                    "port": info["port"],
                    "sourceIP": "",
                    "sourcePort": 0,
                    "sourceDown": False,
                    "adminUsername": info["admin_user"],
                    "adminPassword": info["admin_password"],
                    "targetIP": info["target"]["ip"],
                    "targetPort": info["target"]["port"],
                    "targetPriority": "1",
                    "targetHidden": "0",
                },
            },
        }

    def get_meta_scale_node_kwargs(self, info: list, increase: bool) -> dict:
        """增减shard节点数修改meta的"""

        if increase:
            scale_out = info
            scale_in = []
        else:
            scale_out = []
            scale_in = info
        return {
            "created_by": self.payload["created_by"],
            "immute_domain": "",
            "cluster_id": info[0]["cluster_id"],
            "bk_biz_id": self.payload["bk_biz_id"],
            "scale_out": scale_out,
            "scale_in": scale_in,
        }

    def calc_reduce_node(self, info: dict):
        """减少节点计算cluster对应关系"""

        # 获取副本集老实例信息
        reduce_shard_nodes = info["reduce_shard_nodes"]
        hosts_set = set()
        hosts = []
        if self.payload["cluster_type"] == ClusterType.MongoReplicaSet.value:
            db_instances = []
            for cluster_id in info["cluster_ids"]:
                self.get_cluster_info_deinstall(cluster_id=cluster_id)
                current_node_num = len(self.payload["nodes"])
                for index in range(reduce_shard_nodes):
                    role = self.instance_role[current_node_num - 2 - index]
                    for node in self.payload["nodes"]:
                        if node["instance_role"] == role:
                            db_instances.append(
                                {
                                    "cluster_id": cluster_id,
                                    "role": role,
                                    "cluster_name": self.payload["cluster_name"],
                                    "ip": node["ip"],
                                    "port": node["port"],
                                    "bk_cloud_id": node["bk_cloud_id"],
                                    "domain": node["domain"],
                                }
                            )
                            hosts_set.add(node["ip"])
                            break
            self.payload["db_instances"] = db_instances
            bk_cloud_id = self.payload["db_instances"][0]["bk_cloud_id"]

        elif self.payload["cluster_type"] == ClusterType.MongoShardedCluster.value:
            cluster_id = info["cluster_id"]
            self.get_cluster_info_deinstall(cluster_id=cluster_id)
            self.payload["shards_instance_relationships"] = {}
            bk_cloud_id = ""
            # 所有shard的实例对应关系
            shards_instance_relationships = {}
            for shard in self.payload["shards_nodes"]:
                shards_instance_relationships[shard["shard"]] = []
            for shard in self.payload["shards_nodes"]:
                current_node_num = len(shard["nodes"])
                for index in range(reduce_shard_nodes):
                    role = self.instance_role[current_node_num - 2 - index]
                    for node in shard["nodes"]:
                        if node["instance_role"] == role:
                            shards_instance_relationships[shard["shard"]].append(
                                {
                                    "cluster_id": cluster_id,
                                    "ip": node["ip"],
                                    "bk_cloud_id": node["bk_cloud_id"],
                                    "role": role,
                                    "cluster_name": self.payload["cluster_name"],
                                    "seg_range": shard["shard"],
                                    "port": node["port"],
                                }
                            )
                            bk_cloud_id = node["bk_cloud_id"]
                            hosts_set.add(node["ip"])
            self.payload["shards_instance_relationships"] = shards_instance_relationships
        for host in hosts_set:
            hosts.append({"ip": host, "bk_cloud_id": bk_cloud_id})
        self.payload["hosts"] = hosts

    def get_reduce_node_kwargs(self, info: dict) -> dict:
        """减少node的kwargs"""

        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": info["exec_bk_cloud_id"],
            "exec_ip": info["exec_ip"],
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.MongoDReplace,
                "file_path": self.file_path,
                "payload": {
                    "ip": info["ip"],
                    "port": info["port"],
                    "sourceIP": info["source"]["ip"],
                    "sourcePort": info["source"]["port"],
                    "sourceDown": False,
                    "adminUsername": info["admin_user"],
                    "adminPassword": info["admin_password"],
                    "targetIP": "",
                    "targetPort": 0,
                    "targetPriority": "",
                    "targetHidden": "",
                },
            },
        }

    def get_hosts_enable_disable(self):
        """获取所有需要启用或禁用的cluster的hosts"""

        hosts = set()
        bk_cloud_id: int = None
        for cluster_id in self.payload["cluster_ids"]:
            cluster_info = MongoRepository().fetch_one_cluster(withDomain=False, id=cluster_id)
            if cluster_info.cluster_type == ClusterType.MongoReplicaSet.value:
                shard = cluster_info.get_shards()[0]
                bk_cloud_id = shard.members[0].bk_cloud_id
                for member in shard.members:
                    hosts.add(member.ip)
            elif cluster_info.cluster_type == ClusterType.MongoShardedCluster.value:
                mongos = cluster_info.get_mongos()
                bk_cloud_id = mongos[0].bk_cloud_id
                for mongo in mongos:
                    hosts.add(mongo.ip)
        list_hosts = []
        for host in hosts:
            list_hosts.append({"ip": host, "bk_cloud_id": bk_cloud_id})
        self.payload["hosts"] = list_hosts

    def get_mongo_start_kwargs(self, node_info: dict, instance_type: str) -> dict:
        """启动mongo进程的kwargs"""

        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": self.payload["bk_cloud_id"],
            "exec_ip": node_info["ip"],
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.MongoStart,
                "file_path": self.file_path,
                "payload": {
                    "ip": node_info["ip"],
                    "port": node_info["port"],
                    "instanceType": instance_type,
                    "auth": True,
                },
            },
        }

    def get_host_instance_deinstall(self):
        """instance卸载获取host"""

        hosts = []
        host_bk_cloud_id_set = set()
        for instance in self.payload["infos"]:
            host_bk_cloud_id_set.add("{}#{}".format(instance["ip"], instance["bk_cloud_id"]))
        for host_bk_cloud_id in host_bk_cloud_id_set:
            info = host_bk_cloud_id.split("#")
            hosts.append(
                {
                    "ip": info[0],
                    "bk_cloud_id": info[1],
                }
            )
        self.payload["hosts"] = hosts

    def get_host_cluster_autofix(self, info: dict):
        """cluster自愈获取host信息"""

        plugin_hosts = []
        plugin_hosts.append({"ip": info["target"]["ip"], "bk_cloud_id": info["target"]["bk_cloud_id"]})
        # 获取参数
        self.payload["hosts"] = plugin_hosts
        self.payload["plugin_hosts"] = plugin_hosts

    def get_change_config_ip_kwargs(self, info) -> dict:
        """修改所有mongos的config的ip"""

        # 获取信息
        bk_cloud_id = info["target"]["bk_cloud_id"]
        port = info["instances"][0]["port"]
        username = MongoDBManagerUser.DbaUser.value
        old_config_node = "{}:{}".format(info["ip"], port)
        new_config_node = "{}:{}".format(info["target"]["ip"], port)
        # 获取密码
        password = self.get_password(ip=info["ip"], port=port, bk_cloud_id=bk_cloud_id, username=username)
        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": bk_cloud_id,
            "exec_ip": [],
            "all_mongos_change_configdb": True,
            "cluster_id": info["instances"][0]["cluster_id"],
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.MongoRestart,
                "file_path": self.file_path,
                "payload": {
                    "ip": "0.0.0.0",
                    "port": 0,
                    "instanceType": MongoDBInstanceType.MongoS.value,
                    "auth": True,
                    "cacheSizeGB": 0,
                    "mongoSConfDbOld": old_config_node,
                    "mongoSConfDbNew": new_config_node,
                    "adminUsername": username,
                    "adminPassword": password,
                    "onlyChangeParam": True,
                },
            },
        }


@dataclass()
class CommonContext:
    """通用可读写上下文"""

    _data: dict = None

    # 调用第三方接口返回的数据
    def __init__(self):
        self._data = {}
        pass

    def set(self, k, v: str):
        self._data[k] = v

    def get(self, k):
        return self._data.get(k, None)

    output: Optional[Any] = None


def payload_func_install_dbmon(db_act_template: dict, ctx: CommonContext) -> dict:
    """payload_func_install_dbmon Referenced in install_dbmon_sub.py"""
    instances_by_ip = ctx.get("instances_by_ip")
    exec_ip = db_act_template["exec_ip"]
    nodes = instances_by_ip[exec_ip]
    db_act_template["payload"]["servers"] = [node.__json__() for node in nodes]  # 必须强制为list，默认是set
    return db_act_template
