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
from typing import Any, List, Optional

from django.conf import settings

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName, OpType, ReqType
from backend.configuration.constants import DBType
from backend.db_meta.enums import machine_type
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.instance_role import InstanceRole
from backend.db_meta.models import Cluster
from backend.db_package.models import Package
from backend.flow.consts import (
    DEFAULT_CONFIG_CONFIRM,
    DEFAULT_DB_MODULE_ID,
    ConfigFileEnum,
    ConfigTypeEnum,
    MediumEnum,
    MongoDBActuatorActionEnum,
    MongoDBDfaultAuthDB,
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
from backend.flow.utils.mongodb.calculate_cluster import get_cache_size, get_oplog_size
from backend.flow.utils.mongodb.mongodb_password import MongoDBPassword


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

    def __get_define_config(self, namespace: str, conf_file: str, conf_type: str) -> Any:
        """获取一些全局的参数配置"""

        data = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(self.payload["bk_biz_id"]),
                "level_name": LevelName.APP,
                "level_value": str(self.payload["bk_biz_id"]),
                "conf_file": conf_file,
                "conf_type": conf_type,
                "namespace": namespace,
                "format": FormatType.MAP.value,
            }
        )
        return data["content"]

    def save_key_file(self, namespace: str, conf_type: str, conf_file: str, key_file: str, cluster_name: str):
        """保存keyfile到dbconfig"""

        DBConfigApi.upsert_conf_item(
            {
                "conf_file_info": {
                    "conf_file": conf_file,
                    "conf_type": conf_type,
                    "namespace": namespace,
                },
                "conf_items": [{"conf_name": "key_file", "conf_value": key_file, "op_type": OpType.UPDATE}],
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "confirm": DEFAULT_CONFIG_CONFIRM,
                "req_type": ReqType.SAVE_AND_PUBLISH,
                "bk_biz_id": str(self.payload["bk_biz_id"]),
                "level_name": LevelName.CLUSTER,
                "level_value": cluster_name,
            }
        )

    def set_save_key_file(self):
        """复制集保存keyfile"""

        self.save_key_file(
            namespace=ClusterType.MongoReplicaSet.value,
            conf_type=ConfigTypeEnum.DBConf.value,
            conf_file="{}-{}".format("Mongodb", self.db_main_version),
            key_file=self.replicaset_info["key_file"],
            cluster_name=self.replicaset_info["set_id"],
        )

    def cluster_save_key_file(self):
        """cluster保存keyfile"""

        self.save_key_file(
            namespace=ClusterType.MongoShardedCluster.value,
            conf_type=ConfigTypeEnum.DBConf.value,
            conf_file="{}-{}".format("Mongodb", self.db_main_version),
            key_file=self.payload["key_file"],
            cluster_name=self.payload["cluster_id"],
        )

    def get_key_file(self, cluster_name: str) -> str:
        """获取keyfile"""

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
        )["content"]["key_file"]

    def get_init_info(self):
        """获取初始信息一些信息"""

        # 集群类型
        self.cluster_type = self.payload["cluster_type"]
        # db大版本
        self.db_main_version = str(self.payload["db_version"].split(".")[0])

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
            version=self.payload["db_version"], pkg_type=MediumEnum.MongoDB, db_type=DBType.MongoDB
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

    def get_send_media_kwargs(self) -> dict:
        """介质下发的kwargs"""

        file_list = GetFileList(db_type=DBType.MongoDB).mongodb_pkg(db_version=self.payload["db_version"])
        ip_list = self.payload["hosts"]
        exec_ips = [host["ip"] for host in ip_list]
        return {
            "file_list": file_list,
            "ip_list": ip_list,
            "exec_ips": exec_ips,
            "file_target_path": self.file_path + "/install",
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

    def get_install_mongod_kwargs(self, node: dict, cluster_role: str) -> dict:
        """复制集mongod安装的kwargs"""

        # 获取安装包名以及MD5值
        self.get_pkg()
        # 获取配置
        self.get_mongodb_conf()
        self.db_conf["cacheSizeGB"] = self.replicaset_info["cacheSizeGB"]
        self.db_conf["oplogSizeMB"] = self.replicaset_info["oplogSizeMB"]
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
                    "app": self.payload["app"],
                    "setId": self.replicaset_info["set_id"],
                    "keyFile": self.payload["key_file"],
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
                    "app": self.payload["app"],
                    "setId": self.mongos_info["set_id"],
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
                    "app": self.payload["app"],
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
            "major_version": self.payload["db_version"],
            "creator": self.payload["created_by"],
            "region": self.payload["city"],
            "db_module_id": 0,
        }
        instance_role = [
            InstanceRole.MONGO_M1,
            InstanceRole.MONGO_M2,
            InstanceRole.MONGO_M3,
            InstanceRole.MONGO_M4,
            InstanceRole.MONGO_M5,
            InstanceRole.MONGO_M6,
            InstanceRole.MONGO_M7,
            InstanceRole.MONGO_M8,
            InstanceRole.MONGO_M9,
            InstanceRole.MONGO_M10,
            InstanceRole.MONGO_BACKUP,
        ]
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
                                "role": instance_role[-1],
                                "ip": node["ip"],
                                "port": replicaset_info["port"],
                                "domain": node["domain"],
                            }
                        )
                    else:
                        info["storages"].append(
                            {
                                "role": instance_role[index],
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
                            {"ip": node["ip"], "port": self.payload["config"]["port"], "role": instance_role[-1]}
                        )
                    else:
                        config["nodes"].append(
                            {"ip": node["ip"], "port": self.payload["config"]["port"], "role": instance_role[index]}
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
                                {"role": instance_role[-1], "ip": node["ip"], "port": shard["port"]}
                            )
                        else:
                            storage["nodes"].append(
                                {"role": instance_role[index], "ip": node["ip"], "port": shard["port"]}
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
            return {
                "bk_biz_id": self.payload["bk_biz_id"],
                "bk_cloud_id": self.replicaset_info["nodes"][0]["bk_cloud_id"],
                "domains": domains,
            }
        else:
            domains = [
                {
                    "domain": self.payload["mongos"]["domain"],
                    "instance_list": ["{}#{}".format(node["ip"], str(self.payload["mongos"]["port"]))],
                }
                for node in self.payload["mongos"]["nodes"]
            ]
            return {
                "bk_biz_id": self.payload["bk_biz_id"],
                "bk_cloud_id": self.payload["mongos"]["nodes"][0]["bk_cloud_id"],
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
            set_name = "{}-{}".format(self.payload["app"], self.replicaset_info["set_id"])
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
            set_name = "{}-{}".format(self.payload["app"], self.replicaset_info["set_id"])
        else:
            set_name = ""
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
                    "authDb": MongoDBDfaultAuthDB.AuthDB,
                    "dbsPrivileges": [
                        {
                            "db": "admin",
                            "privileges": [MongoDBUserPrivileges.RootRole.value],
                        }
                    ],
                },
            },
        }

    def get_get_manager_password_kwargs(self) -> dict:
        """获取用户密码"""

        if self.payload["cluster_type"] == ClusterType.MongoReplicaSet.value:
            set_name = "{}-{}".format(self.payload["app"], self.replicaset_info["set_id"])
        else:
            set_name = ""
        return {"set_trans_data_dataclass": CommonContext.__name__, "set_name": set_name, "users": self.manager_users}

    def get_add_password_to_db_kwargs(self, usernames: list, info: dict) -> dict:
        """添加密码到db"""

        if self.payload["cluster_type"] == ClusterType.MongoReplicaSet.value:
            set_name = "{}-{}".format(self.payload["app"], self.replicaset_info["set_id"])
        else:
            set_name = ""

        nodes = [
            {"ip": node["ip"], "port": info["port"], "bk_cloud_id": node["bk_cloud_id"]} for node in info["nodes"]
        ]
        return {"nodes": nodes, "usernames": usernames, "set_name": set_name, "operator": self.payload["created_by"]}

    def get_cluster_info_user(self, cluster_id: int, admin_user: str):
        """创建/删除用户获取cluster信息"""

        # 获取集群信息
        cluster_info = MongoRepository().fetch_one_cluster(id=cluster_id)
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
        # db大版本
        self.db_main_version = str(self.payload["db_version"].split(".")[0])
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

    def get_hosts_deinstall(self):
        """获取所有需要卸载的cluster的hosts"""

        hosts = set()
        for cluster_id in self.payload["cluster_ids"]:
            cluster_info = MongoRepository().fetch_one_cluster(id=cluster_id)
            if cluster_info.cluster_type == ClusterType.MongoReplicaSet.value:
                for member in cluster_info.get_shards()[0].members:
                    hosts.add(member.ip)
            elif cluster_info.cluster_type == ClusterType.MongoShardedCluster.value:
                mongos = cluster_info.get_mongos()
                shards = cluster_info.get_shards()
                config = cluster_info.get_config()
                for mongo in mongos:
                    hosts.add(mongo.ip)
                for member in config.members:
                    hosts.add(member.ip)
                for shard in shards:
                    for member in shard.members:
                        hosts.add(member.ip)
        list_hosts = []
        for host in hosts:
            list_hosts.append({"ip": host})
        self.payload["hosts"] = list_hosts

    def get_cluster_info_deinstall(self, cluster_id: int):
        """卸载流程获取cluster信息"""

        cluster_info = MongoRepository().fetch_one_cluster(id=cluster_id)
        self.payload["cluster_type"] = cluster_info.cluster_type
        # self.payload["app"] = cluster_info.name.split("-")[0]
        self.payload["set_id"] = cluster_info.name
        self.payload["bk_cloud_id"] = cluster_info.bk_cloud_id
        nodes = []
        if cluster_info.cluster_type == ClusterType.MongoReplicaSet.value:
            for member in cluster_info.get_shards()[0].members:
                nodes.append(
                    {
                        "ip": member.ip,
                        "port": int(member.port),
                        "bk_cloud_id": member.bk_cloud_id,
                        "domain": member.domain,
                    }
                )
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
                for member in shard.members:
                    nodes.append({"ip": member.ip, "port": int(member.port), "bk_cloud_id": member.bk_cloud_id})
                shard_info["nodes"] = nodes
                shards_nodes.append(shard_info)
            for member in config.members:
                config_nodes.append({"ip": member.ip, "port": int(member.port), "bk_cloud_id": member.bk_cloud_id})
            self.payload["mongos_nodes"] = mongos_nodes
            self.payload["shards_nodes"] = shards_nodes
            self.payload["config_nodes"] = config_nodes

    def get_mongo_deinstall_kwargs(self, node_info: dict, instance_type: str, nodes_info: list) -> dict:
        """卸载mongo"""

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
                    "app": self.payload["app"],
                    "setId": self.payload["set_id"],
                    "nodeInfo": nodes,
                    "instanceType": instance_type,
                },
            },
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
                            "db_version": info["db_version"],
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
        if instance["role"] == MongoDBInstanceType.MongoS:
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
        """替换获取信息"""

        hosts = []
        if mongodb_type == ClusterType.MongoReplicaSet.value:
            # 源ip
            hosts.append({"ip": info["ip"], "bk_cloud_id": info["bk_cloud_id"]})
            # 目标ip
            hosts.append({"ip": info["target"]["ip"], "bk_cloud_id": info["target"]["bk_cloud_id"]})
            # db版本
            self.payload["db_version"] = info["mongodb"][0]["db_version"]
            self.db_main_version = self.payload["db_version"].split(".")[0]

        elif mongodb_type == ClusterType.MongoShardedCluster.value:
            for mongos in info["mongos"]:
                # 源ip
                hosts.append({"ip": mongos["ip"], "bk_cloud_id": mongos["bk_cloud_id"]})
                # 目标ip
                hosts.append({"ip": mongos["target"]["ip"], "bk_cloud_id": mongos["target"]["bk_cloud_id"]})
            for config in info["mongo_config"]:
                # 源ip
                hosts.append({"ip": config["ip"], "bk_cloud_id": config["bk_cloud_id"]})
                # 目标ip
                hosts.append({"ip": config["target"]["ip"], "bk_cloud_id": config["target"]["bk_cloud_id"]})
            for shard in info["mongodb"]:
                # 源ip
                hosts.append({"ip": shard["ip"], "bk_cloud_id": shard["bk_cloud_id"]})
                # 目标ip
                hosts.append({"ip": shard["target"]["ip"], "bk_cloud_id": shard["target"]["bk_cloud_id"]})
            # 获取参数
            if info["mongos"]:
                self.payload["db_version"] = info["mongos"][0]["instances"][0]["db_version"]
            elif info["mongo_config"]:
                self.payload["db_version"] = info["mongo_config"][0]["instances"][0]["db_version"]
            elif info["mongodb"]:
                self.payload["db_version"] = info["mongodb"][0]["instances"][0]["db_version"]
            self.db_main_version = self.payload["db_version"].split(".")[0]

        self.payload["hosts"] = hosts

    def get_mongos_host_replace(self):
        """替换configDB获取mongos主机"""

        for mongos in self.payload["mongos_nodes"]:
            self.payload["hosts"].append({"ip": mongos["ip"], "bk_cloud_id": mongos["bk_cloud_id"]})

    def calc_param_replace(self, info: dict):
        """"计算参数"""

        self.replicaset_info = {}
        # 同机器的实例数
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


def get_mongo_global_config():
    """获取mongo配置, todo 改为从配置中心获取"""
    return {
        "file_path": "/data",  # actuator工作目录
        "install_dir": "",  # 数据文件存放目录，为空表示使用默认目录，优先 /data1，其次/data
        "backup_dir": "",  # 备份文件存放目录，为空表示使用默认目录，优先 /data，其次/data1
        "user": "mysql",  # 用户名
    }


# entities
# Node -> ReplicaSet -> Cluster[Rs,ShardedCluster]


class MongoNode:
    def __init__(self, ip, port, role, bk_cloud_id, domain):
        self.ip: str = ip
        self.port: str = port
        self.role: str = role
        self.bk_cloud_id: int = bk_cloud_id
        self.domain: str = domain


class ReplicaSet:
    def __init__(self):
        self.set_name: str = None
        self.members: List[MongoNode] = None

    # get_backup_node 返回MONGO_BACKUP member
    def get_backup_node(self):
        i = len(self.members) - 1
        while i >= 0:
            if self.members[i].role == InstanceRole.MONGO_BACKUP:
                return self.members[i]
            i = i - 1

        return None

    # get_not_backup_nodes 返回非MONGO_BACKUP的member
    def get_not_backup_nodes(self):
        members = []
        # i = len(self.members) - 1
        for m in self.members:
            if m.role == InstanceRole.MONGO_BACKUP:
                members.append(m)

        return members

    def get_bk_cloud_id(self):
        for i in self.members:
            return i.bk_cloud_id
        return None


# MongoDBCluster 有cluster_id cluster_name cluster_type
class MongoDBCluster:
    bk_cloud_id: int
    bk_biz_id: int
    creator: str
    name: str
    app: str
    immute_domain: str
    alias: str
    major_version: str
    region: str
    cluster_type: str
    id: str

    def __init__(self):
        self.id: str = None
        self.name: str = None
        self.cluster_type: str = None

    # get_shards interface
    def get_shards(self) -> List[ReplicaSet]:
        pass

    def get_mongos(self) -> List[MongoNode]:
        return None

    def get_config(self) -> ReplicaSet:
        return None

    def get_bk_cloud_id(self):
        pass


class ReplicaSetCluster(MongoDBCluster):
    shard: ReplicaSet  # storages

    def __init__(self):
        self.cluster_type: str = ClusterType.MongoReplicaSet.value

    def get_shards(self):
        return [self.shard]

    def get_mongos(self) -> List[MongoNode]:
        return None


class ShardedCluster(MongoDBCluster):
    shards: List[ReplicaSet]  # storages
    mongos: List[MongoNode]  # proxies
    config: ReplicaSet  # configs

    def __init__(self):
        self.cluster_type: str = ClusterType.MongoShardedCluster.value

    def get_shards(self) -> List[ReplicaSet]:
        return self.shards

    def get_config(self) -> ReplicaSet:
        return self.config

    def get_mongos(self) -> List[MongoNode]:
        return self.mongos


# MongoRepository
#
class MongoRepository:
    def __init__(self):
        pass

    @classmethod
    def fetch_many_cluster(cls, **kwargs):
        rows: List[MongoDBCluster] = []
        v = Cluster.objects.filter(**kwargs)
        for i in v:
            if i.cluster_type == ClusterType.MongoReplicaSet.value:
                row = ReplicaSetCluster()
                row.id = i.id
                row.name = i.name
                row.cluster_type = i.cluster_type
                row.major_version = i.major_version
                row.bk_biz_id = i.bk_biz_id
                row.immute_domain = i.immute_domain
                row.bk_cloud_id = i.bk_cloud_id

                # MongoReplicaSet 只有一个Set
                row.shard = ReplicaSet()
                row.shard.set_name = row.name
                row.shard.members = []

                for m in i.storageinstance_set.all():
                    row.shard.members.append(
                        MongoNode(
                            m.ip_port.split(":")[0],
                            str(m.port),
                            m.instance_role,
                            m.machine.bk_cloud_id,
                            m.bind_entry.first().entry,
                        )
                    )

                rows.append(row)
            elif i.cluster_type == ClusterType.MongoShardedCluster.value:
                row = ShardedCluster()
                row.id = i.id
                row.name = i.name
                row.cluster_type = i.cluster_type
                row.major_version = i.major_version
                row.bk_biz_id = i.bk_biz_id
                row.bk_cloud_id = i.bk_cloud_id
                row.immute_domain = i.immute_domain
                row.mongos = []
                row.shards = []

                for m in i.proxyinstance_set.all():
                    row.mongos.append(
                        MongoNode(
                            m.ip_port.split(":")[0],
                            str(m.port),
                            m.instance_role,
                            m.machine.bk_cloud_id,
                            m.bind_entry.first().entry,
                        )
                    )

                for m in i.nosqlstoragesetdtl_set.all():
                    # seg_range
                    shard = ReplicaSet()
                    shard.set_name = m.seg_range
                    shard.members = []
                    # add primary
                    node = m.instance
                    shard.members.append(
                        MongoNode(
                            node.ip_port.split(":")[0],
                            str(node.port),
                            node.instance_role,
                            node.machine.bk_cloud_id,
                            "",
                        )
                    )

                    # add secondary
                    for e in m.instance.as_ejector.all():
                        node = e.receiver
                        shard.members.append(
                            MongoNode(
                                node.ip_port.split(":")[0],
                                str(node.port),
                                node.instance_role,
                                node.machine.bk_cloud_id,
                                "",
                            )
                        )

                    if m.instance.machine_type == machine_type.MachineType.MONOG_CONFIG.value:
                        row.config = shard
                    else:
                        row.shards.append(shard)

                rows.append(row)

        return rows

    @classmethod
    def fetch_one_cluster(cls, **kwargs):
        rows = cls.fetch_many_cluster(**kwargs)
        if len(rows) > 0:
            return rows[0]
        return None

    @classmethod
    def fetch_many_cluster_dict(cls, **kwargs):
        clusters = cls.fetch_many_cluster(**kwargs)
        clusters_map = {}
        for cluster in clusters:
            clusters_map[cluster.immute_domain.lower()] = cluster
        return clusters_map
