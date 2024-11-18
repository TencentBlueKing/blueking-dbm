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

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName, OpType
from backend.configuration.constants import DBType
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.instance_role import InstanceRole
from backend.db_meta.enums.spec import SpecClusterType, SpecMachineType
from backend.db_meta.models import Machine
from backend.db_meta.models.spec import Spec
from backend.flow.consts import (
    DEFAULT_DB_MODULE_ID,
    ConfigFileEnum,
    ConfigTypeEnum,
    MongoDBActuatorActionEnum,
    MongoDBManagerUser,
    NameSpaceEnum,
)
from backend.flow.utils.mongodb.migrate_meta import MongoDBMigrateMeta
from backend.flow.utils.mongodb.mongodb_dataclass import CommonContext
from backend.flow.utils.mongodb.mongodb_password import MongoDBPassword


@dataclass()
class MigrateActKwargs:
    """节点私有变量数据类"""

    def __init__(self):
        # 传入流程信息
        self.payload: dict = None
        # 目标端的bk_biz_id
        self.bk_biz_id: int = None
        # 流程id
        self.root_id: int = None
        # 多个副本集的信息
        self.multi_replicaset_info: list = None
        # 副本集的信息
        self.replicaset_info: str = None
        # cluster的信息
        self.cluster_info: str = None
        # 源端cluster信息
        self.source_cluster_info: dict = None
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
        # 目标环境副本集mongodb机型规格
        self.dest_replicaset_machine_spec: dict = self.get_mongodb_spec_info(
            cluster_type=SpecClusterType.MongoDB.value, machine_type=SpecMachineType.MONGODB.value
        )
        # 目标环境cluster mongos机型规格
        self.dest_mongos_machine_spec: dict = self.get_mongodb_spec_info(
            cluster_type=SpecClusterType.MongoDB.value, machine_type=SpecMachineType.MONGOS.value
        )
        # 目标环境cluster config机型规格
        self.dest_config_machine_spec: dict = self.get_mongodb_spec_info(
            cluster_type=SpecClusterType.MongoDB.value, machine_type=SpecMachineType.MONOG_CONFIG.value
        )
        # 目标环境cluster mongodb机型规格
        self.dest_mongodb_machine_spec: dict = self.get_mongodb_spec_info(
            cluster_type=SpecClusterType.MongoDB.value, machine_type=SpecMachineType.MONGODB.value
        )
        # 副本集源环境机器映射目标环境机器规格
        self.replicaset_machine_spec: dict = None
        # cluster源环境机器映射目标环境机器规格
        self.cluster_machine_spec: dict = None
        # 管理员用户
        self.manager_users: list = [
            MongoDBManagerUser.DbaUser.value,
            MongoDBManagerUser.AppDbaUser.value,
            MongoDBManagerUser.MonitorUser.value,
            MongoDBManagerUser.AppMonitorUser.value,
        ]
        # 集群的主机
        self.hosts: list = None
        # 集群bk_cloud_id
        self.bk_cloud_id: int = None

    def skip_machine(self):
        """副本集机器复用"""

        if self.source_cluster_info.get("cluster_type") == ClusterType.MongoReplicaSet.value:
            for node in self.source_cluster_info.get("storages"):
                if Machine.objects.filter(ip=node["ip"], bk_cloud_id=node["bk_cloud_id"]).count() > 0:
                    self.source_cluster_info["skip_machine"] = True
                    break
                else:
                    self.source_cluster_info["skip_machine"] = False

    @staticmethod
    def get_mongodb_spec_info(cluster_type: str, machine_type: str) -> dict:
        """获取机器规格"""

        machine_specs = {}
        for spec in Spec.objects.filter(spec_cluster_type=cluster_type, spec_machine_type=machine_type):
            spec_info = {"spec_id": spec.spec_id, "spec_config": spec.get_spec_info()}
            for device in spec.device_class:
                machine_specs[device] = spec_info
        return machine_specs

    def get_check_dest_cluster_info(self, cluster_name) -> dict:
        """检查cluster是否已经在目标端存在信息"""

        return {
            "bk_biz_id": self.bk_biz_id,
            "cluster_name": cluster_name,
            "meta_func_name": MongoDBMigrateMeta.check_dest_cluster.__name__,
        }

    def get_check_spec_info(self) -> dict:
        """检查目标端机器规格是否存在"""

        replicaset_spec = {}
        cluster_spec = {}
        if self.source_cluster_info.get("cluster_type") == ClusterType.MongoReplicaSet.value:
            if self.source_cluster_info.get("machine_type") in self.dest_replicaset_machine_spec:
                replicaset_spec = self.dest_replicaset_machine_spec.get(self.source_cluster_info.get("machine_type"))
            else:
                replicaset_spec = {"spec_id": 0, "spec_config": ""}
            self.replicaset_machine_spec = replicaset_spec
        elif self.source_cluster_info.get("cluster_type") == ClusterType.MongoShardedCluster.value:
            # mnogos
            if self.source_cluster_info.get("proxies_machine_type") in self.dest_mongos_machine_spec:
                cluster_spec.update(
                    {"mongos": self.dest_mongos_machine_spec.get(self.source_cluster_info.get("proxies_machine_type"))}
                )
            else:
                cluster_spec.update({"mongos": {"spec_id": 0, "spec_config": ""}})
            # config
            if self.source_cluster_info.get("configs_machine_type") in self.dest_config_machine_spec:
                cluster_spec.update(
                    {
                        "mongo_config": self.dest_config_machine_spec.get(
                            self.source_cluster_info.get("configs_machine_type")
                        )
                    }
                )
            else:
                cluster_spec.update({"mongo_config": {"spec_id": 0, "spec_config": ""}})
            # shard
            if self.source_cluster_info.get("storages_machine_type") in self.dest_mongodb_machine_spec:
                cluster_spec.update(
                    {
                        "mongodb": self.dest_mongodb_machine_spec.get(
                            self.source_cluster_info.get("storages_machine_type")
                        )
                    }
                )
            else:
                cluster_spec.update({"mongodb": {"spec_id": 0, "spec_config": ""}})
            self.cluster_machine_spec = cluster_spec
        return {
            "cluster_type": self.source_cluster_info["cluster_type"],
            "replicaset_spec": replicaset_spec,
            "cluster_spec": cluster_spec,
            "meta_func_name": MongoDBMigrateMeta.check_machine_spec.__name__,
        }

    def get_save_conf_info(self, namespace: str) -> dict:
        """获取保存到dbconfig的配置信息"""

        cluster_info = self.source_cluster_info
        conf_type = ConfigTypeEnum.DBConf.value
        conf_file = "{}-{}".format("Mongodb", cluster_info.get("major_version").split("-")[1].split(".")[0])
        cluster_name = ""
        key_file = ""
        cache_size = ""
        oplog_size = ""
        conf_items = []
        if namespace == ClusterType.MongoReplicaSet.value:
            cluster_name = cluster_info["replsetname"]
            key_file = cluster_info["key_file"]
            cache_size = str(cluster_info["cache_size_gb"])
            oplog_size = str(cluster_info["oplog_size_mb"])
        elif namespace == ClusterType.MongoShardedCluster.value:
            cluster_name = cluster_info["cluster_id"]
            key_file = cluster_info["key_file"]
            cache_size = str(cluster_info["storages_cache_size_gb"])
            oplog_size = str(cluster_info["storages_oplog_size_mb"])
            config_cache_size = str(cluster_info["configs_cache_size_gb"])
            config_oplog_size = str(cluster_info["configs_oplog_size_mb"])
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
        return {
            "conf_file": conf_file,
            "conf_type": conf_type,
            "namespace": namespace,
            "conf_items": conf_items,
            "bk_biz_id": str(self.bk_biz_id),
            "cluster_name": cluster_name,
            "meta_func_name": MongoDBMigrateMeta.save_config.__name__,
        }

    def get_dba_info(self) -> dict:
        """获取dba信息"""

        return {
            "bk_biz_id": self.bk_biz_id,
            "db_admins": [
                {"db_type": DBType.MongoDB.value, "users": self.source_cluster_info["mongodb_dbas"].split(",")}
            ],
            "meta_func_name": MongoDBMigrateMeta.upsert_dba.__name__,
        }

    def instance_exchange_role(self, instances: dict) -> list:
        """role转换"""

        nodes = []
        backup_node = {}
        for instance in instances:
            if instance.get("role") == "shardsvr-backup":
                backup_node = instance
            else:
                nodes.append(instance)
        nodes.append(backup_node)
        nodes[-1]["role"] = self.instance_role[-1]
        for index in range(len(nodes) - 1):
            nodes[index]["role"] = self.instance_role[index]
        return nodes

    def get_migrate_info(self) -> dict:
        """获取迁移信息"""

        info = {
            "bk_biz_id": self.bk_biz_id,
            "major_version": self.source_cluster_info.get("major_version"),
            "creator": self.source_cluster_info.get("mongodb_dbas").split(",")[0],
            "region": self.source_cluster_info.get("region"),
            "db_module_id": DEFAULT_DB_MODULE_ID,
            "cluster_type": self.source_cluster_info.get("cluster_type"),
            # "disaster_tolerance_level": self.source_cluster_info.get("disaster_tolerance_level"),
            # 亲和性默认为跨园区CROS_SUBZONE
            "disaster_tolerance_level": "CROS_SUBZONE",
        }
        if self.source_cluster_info.get("cluster_type") == ClusterType.MongoReplicaSet.value:
            # role转换
            # 找出backup,immute_domain
            storages = []
            backup_node = {}
            immute_domain = ""
            for instance in self.source_cluster_info.get("storages"):
                if instance.get("role") == "shardsvr-backup":
                    backup_node = instance
                else:
                    if instance.get("role") == "shardsvr-primary":
                        immute_domain = instance.get("domain")
                    storages.append(instance)
            storages.append(backup_node)
            # 转换role
            if len(storages) > 2:
                storages[-1]["role"] = self.instance_role[-1]
                for index in range(len(storages) - 1):
                    storages[index]["role"] = self.instance_role[index]
            else:
                for index in range(len(storages)):
                    storages[index]["role"] = self.instance_role[index]
            info.update(
                {
                    "skip_machine": self.source_cluster_info.get("skip_machine"),
                    "immute_domain": immute_domain,
                    "name": self.source_cluster_info.get("replsetname"),
                    "alias": self.source_cluster_info.get("replsetname"),
                    "spec_id": self.replicaset_machine_spec.get("spec_id"),
                    "spec_config": self.replicaset_machine_spec.get("spec_config"),
                    "bk_cloud_id": storages[0]["bk_cloud_id"],
                    "storages": storages,
                }
            )
        elif self.source_cluster_info.get("cluster_type") == ClusterType.MongoShardedCluster.value:
            # proxies
            proxies = [
                {"ip": mongos.get("ip"), "port": mongos.get("port")}
                for mongos in self.source_cluster_info.get("proxies")
            ]

            # configs
            configs = []
            config_info = self.source_cluster_info.get("configsvr")
            # role转换 config默认3node
            nodes = self.instance_exchange_role(instances=config_info.get("nodes"))
            configs.append({"shard": config_info.get("shard"), "nodes": nodes})
            # shard shard默认3个node
            storages = []
            for shard in self.source_cluster_info.get("storages"):
                # role转换
                nodes = self.instance_exchange_role(instances=shard.get("nodes"))
                storages.append({"shard": shard.get("shard"), "nodes": nodes})

            info.update(
                {
                    "name": self.source_cluster_info.get("cluster_id"),
                    "alias": self.source_cluster_info.get("cluster_id"),
                    "bk_cloud_id": self.source_cluster_info.get("proxies")[0].get("bk_cloud_id"),
                    "machine_specs": self.cluster_machine_spec,
                    "immute_domain": self.source_cluster_info.get("immute_domain"),
                    "proxies": proxies,
                    "configs": configs,
                    "storages": storages,
                }
            )
        return info

    def get_save_app_password_info(self) -> dict:
        """获取业务的appdba appmonitor密码信息"""

        info = {
            "bk_biz_id": self.bk_biz_id,
            "meta_func_name": MongoDBMigrateMeta.save_app_password.__name__,
        }
        if self.source_cluster_info.get("cluster_type") == ClusterType.MongoReplicaSet.value:
            info["appdba"] = self.source_cluster_info.get("password").get("appdba")
            info["appmonitor"] = self.source_cluster_info.get("password").get("appmonitor")
        elif self.source_cluster_info.get("cluster_type") == ClusterType.MongoShardedCluster.value:
            info["appdba"] = self.source_cluster_info.get("proxies_password").get("appdba")
            info["appmonitor"] = self.source_cluster_info.get("proxies_password").get("appmonitor")
        return info

    def get_save_password_info(self) -> dict:
        """获取保存密码信息"""

        info = {
            "usernames": self.manager_users,
            "operator": self.source_cluster_info.get("mongodb_dbas").split(",")[0],
            "password_infos": [],
            "meta_func_name": MongoDBMigrateMeta.save_password.__name__,
        }
        if self.source_cluster_info.get("cluster_type") == ClusterType.MongoReplicaSet.value:
            nodes = [
                {"ip": node.get("ip"), "port": node.get("port"), "bk_cloud_id": node.get("bk_cloud_id")}
                for node in self.source_cluster_info.get("storages")
            ]
            self.hosts = nodes
            info["password_infos"].append(
                {
                    "nodes": nodes,
                    "password": self.source_cluster_info.get("password"),
                }
            )
        elif self.source_cluster_info.get("cluster_type") == ClusterType.MongoShardedCluster.value:
            # mongos
            proxie_nodes = [
                {"ip": node.get("ip"), "port": node.get("port"), "bk_cloud_id": node.get("bk_cloud_id")}
                for node in self.source_cluster_info.get("proxies")
            ]
            info["password_infos"].append(
                {"nodes": proxie_nodes, "password": self.source_cluster_info.get("proxies_password")}
            )
            # config
            config_nodes = [
                {"ip": node.get("ip"), "port": node.get("port"), "bk_cloud_id": node.get("bk_cloud_id")}
                for node in self.source_cluster_info.get("configsvr")["nodes"]
            ]
            info["password_infos"].append(
                {"nodes": config_nodes, "password": self.source_cluster_info.get("configsvr").get("password")}
            )
            # shard
            storages_hosts_set = set()
            for shard in self.source_cluster_info.get("storages"):
                nodes = [
                    {"ip": node.get("ip"), "port": node.get("port"), "bk_cloud_id": node.get("bk_cloud_id")}
                    for node in shard.get("nodes")
                ]
                for node in nodes:
                    storages_hosts_set.add(node["ip"])
                info["password_infos"].append({"nodes": nodes, "password": shard.get("password")})
            storages_hosts_list = [
                {
                    "ip": host.get("ip"),
                    "bk_cloud_id": self.source_cluster_info.get("storages")[0]["nodes"][0]["bk_cloud_id"],
                }
                for host in storages_hosts_set
            ]
            self.hosts = proxie_nodes + config_nodes + storages_hosts_list
        return info

    def get_change_dns_app_info(self) -> dict:
        """获取修改dns的app字段信息"""

        change_domain_app = []
        bk_cloud_id = 0
        if self.source_cluster_info.get("cluster_type") == ClusterType.MongoReplicaSet.value:
            bk_cloud_id = self.source_cluster_info.get("storages")[0].get("bk_cloud_id")
            change_domain_app = [node.get("domain") for node in self.source_cluster_info.get("storages")]
        elif self.source_cluster_info.get("cluster_type") == ClusterType.MongoShardedCluster.value:
            bk_cloud_id = self.source_cluster_info.get("proxies")[0].get("bk_cloud_id")
            change_domain_app = [self.source_cluster_info.get("immute_domain")]
            # clb域名
            if self.source_cluster_info["clb"]:
                change_domain_app.append(self.source_cluster_info["clb"]["clb_domain"])

        return {
            "app": self.source_cluster_info.get("app"),
            "new_app": str(self.bk_biz_id),
            "bk_cloud_id": bk_cloud_id,
            "change_domain_app": change_domain_app,
            "meta_func_name": MongoDBMigrateMeta.change_domain_app.__name__,
        }

    def get_shard_delete_doamin_info(self):
        """获取shard删除domain信息"""

        # config
        delete_domain = [
            {"domain": node.get("domain"), "del_instance_list": ["{}#{}".format(node.get("ip"), node.get("port"))]}
            for node in self.source_cluster_info.get("configsvr").get("nodes")
        ]
        # shard
        for shard in self.source_cluster_info.get("storages"):
            delete_domain.extend(
                [
                    {
                        "domain": node.get("domain"),
                        "del_instance_list": ["{}#{}".format(node.get("ip"), node.get("port"))],
                    }
                    for node in shard.get("nodes")
                ]
            )
        return {
            "bk_biz_id": self.payload.get("app"),
            "bk_cloud_id": self.source_cluster_info.get("proxies")[0].get("bk_cloud_id"),
            "delete_domain": delete_domain,
            "meta_func_name": MongoDBMigrateMeta.shard_delete_domain.__name__,
        }

    def get_clb_info(self) -> dict:
        """对于cluster，获取clb信息"""

        return {
            "bk_biz_id": self.bk_biz_id,
            "bk_cloud_id": self.source_cluster_info.get("proxies")[0].get("bk_cloud_id"),
            "name": self.source_cluster_info.get("cluster_id"),
            "clb": self.source_cluster_info.get("clb"),
            "region": self.source_cluster_info.get("region"),
            "created_by": self.source_cluster_info.get("mongodb_dbas").split(",")[0],
            "meta_func_name": MongoDBMigrateMeta.add_clb_domain.__name__,
        }

    def get_os_init_info(self) -> dict:
        """进行host初始化"""

        # 获取os配置
        os_conf = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": self.bk_biz_id,
                "level_name": LevelName.APP,
                "level_value": self.bk_biz_id,
                "conf_file": ConfigFileEnum.OsConf.value,
                "conf_type": ConfigTypeEnum.Config.value,
                "namespace": NameSpaceEnum.MongoDBCommon.value,
                "format": FormatType.MAP.value,
            }
        )["content"]
        user = os_conf["user"]
        file_path = os_conf["file_path"]
        self.bk_cloud_id = self.hosts[0]["bk_cloud_id"]
        # 获取os user密码
        password = MongoDBPassword().get_password_from_db(
            ip="0.0.0.0", port=0, bk_cloud_id=self.bk_cloud_id, username=user
        )["password"]
        return {
            "init_flag": True,
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": self.bk_cloud_id,
            "exec_ip": self.hosts,
            "file_target_path": file_path + "/install",
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.OsInit,
                "file_path": file_path,
                "user": user,
                "group": os_conf["group"],
                "data_dir": os_conf["install_dir"],
                "backup_dir": os_conf["backup_dir"],
                "payload": {
                    "user": user,
                    "password": password,
                },
            },
        }

    def get_stop_old_dbmon_info(self) -> dict:
        """关闭集群老的dbmon"""

        return {
            "stop_old_dbmon": True,
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": self.bk_cloud_id,
            "exec_ip": self.hosts,
            "db_act_template": {
                "payload": {},
            },
        }

    def get_install_plugin_info(self, plugin_name: str) -> dict:
        """安装蓝鲸插件"""

        ips = [host["ip"] for host in self.hosts]
        return {
            "plugin_name": plugin_name,
            "ips": ips,
            "bk_cloud_id": self.bk_cloud_id,
        }
