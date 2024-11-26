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

import logging

from django.utils.translation import ugettext as _

from backend.components import DBConfigApi, DnsApi
from backend.components.dbconfig.constants import LevelName, ReqType
from backend.configuration.handlers.dba import DBAdministratorHandler
from backend.db_meta.api.cluster.mongocluster import pkg_create_mongo_cluster
from backend.db_meta.api.cluster.mongorepset import pkg_create_mongoset
from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import CLBEntryDetail, Cluster, ClusterEntry, Machine
from backend.flow.consts import DEFAULT_CONFIG_CONFIRM, DEFAULT_DB_MODULE_ID, MongoDBManagerUser
from backend.flow.utils import dns_manage
from backend.flow.utils.mongodb.mongodb_password import MongoDBPassword

logger = logging.getLogger("flow")


class MongoDBMigrateMeta(object):
    """mongodb迁移元数据flow节点函数"""

    def __init__(self, info: dict):
        self.info = info

    def action(self) -> bool:
        function_name = self.info["meta_func_name"].lower()
        if hasattr(self, function_name):
            return getattr(self, function_name)()

        logger.error(_("找不到单据类型，请联系系统管理员"))
        return False

    def check_dest_cluster(self):
        """检查目标环境是否已经存在该cluster"""

        if Cluster.objects.filter(name=self.info["cluster_name"], bk_biz_id=self.info["bk_biz_id"]).count() > 0:
            logger.error(
                "error: cluster:{} has of bk_biz_id:{} been existed".format(
                    self.info["cluster_name"], str(self.info["bk_biz_id"])
                )
            )
            raise ValueError(
                "error: cluster:{} has of bk_biz_id:{} been existed".format(
                    self.info["cluster_name"], str(self.info["bk_biz_id"])
                )
            )

    def check_machine_spec(self):
        """检查机器规格"""

        if self.info["cluster_type"] == ClusterType.MongoReplicaSet.value:
            if not self.info["replicaset_spec"]["spec_id"]:
                logger.error(
                    "error: machine spec of destination is not exist about {}".format(
                        ClusterType.MongoReplicaSet.value
                    )
                )
                raise ValueError(
                    "error: machine spec of destination is not exist about {}".format(
                        ClusterType.MongoReplicaSet.value
                    )
                )
        elif self.info["cluster_type"] == ClusterType.MongoShardedCluster.value:
            for key, value in self.info["cluster_spec"].items():
                if not value["spec_id"]:
                    logger.error(
                        "error: machine spec of destination is not exist about {} {}".format(
                            ClusterType.MongoShardedCluster.value, key
                        )
                    )
                    raise ValueError(
                        "error: machine spec of destination is not exist about {} {}".format(
                            ClusterType.MongoShardedCluster.value, key
                        )
                    )

    def save_config(self):
        """保存cluster的配置"""

        DBConfigApi.upsert_conf_item(
            {
                "conf_file_info": {
                    "conf_file": self.info["conf_file"],
                    "conf_type": self.info["conf_type"],
                    "namespace": self.info["namespace"],
                },
                "conf_items": self.info["conf_items"],
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "confirm": DEFAULT_CONFIG_CONFIRM,
                "req_type": ReqType.SAVE_AND_PUBLISH,
                "bk_biz_id": self.info["bk_biz_id"],
                "level_name": LevelName.CLUSTER,
                "level_value": self.info["cluster_name"],
            }
        )

    def upsert_dba(self):
        """更新dba"""

        DBAdministratorHandler.upsert_biz_admins(self.info["bk_biz_id"], self.info["db_admins"])

    def save_app_password(self):
        """保存appdba appmonitor密码到密码服务"""

        for user in [MongoDBManagerUser.AppDbaUser.value, MongoDBManagerUser.AppMonitorUser.value]:
            result = MongoDBPassword().get_password_from_db(
                ip=str(self.info["bk_biz_id"]), port=0, bk_cloud_id=0, username=user
            )
            if result["password"] is None:
                logger.error("user:{} get password fail from db, error:{}".format(user, result["info"]))
            if result["password"] == "":
                info = MongoDBPassword().save_password_to_db2(
                    instances=[
                        {
                            "ip": str(self.info["bk_biz_id"]),
                            "port": 0,
                            "bk_cloud_id": 0,
                        }
                    ],
                    username=user,
                    password=self.info[user],
                    operator="admin",
                )
                if info != "":
                    logger.error("user:{} save password:{} to db fail, error:{}".format(user, self.info[user], info))
                    return False

    def save_password(self):
        """保存密码到密码服务"""

        for username in self.info["usernames"]:
            for password_info in self.info["password_infos"]:
                result = MongoDBPassword().save_password_to_db2(
                    instances=password_info["nodes"],
                    username=username,
                    password=password_info["password"][username],
                    operator=self.info["operator"],
                )
                if result:
                    logger.error(
                        "nodes:{} save user:{} password:{} fail, error: {}".format(
                            password_info["nodes"], username, password_info["password"][username], result
                        )
                    )
                    return False

    def migrate_cluster(self):
        """迁移集群"""

        # 副本集判断机器是否复用
        if self.info["cluster_type"] == ClusterType.MongoReplicaSet.value:
            for node in self.info["replicaset_storages"]:
                if Machine.objects.filter(ip=node["ip"], bk_cloud_id=node["bk_cloud_id"]).count() > 0:
                    self.info["skip_machine"] = True
                    break
        # 写入meta
        try:
            if self.info["cluster_type"] == ClusterType.MongoReplicaSet.value:
                pkg_create_mongoset(
                    bk_biz_id=self.info["bk_biz_id"],
                    name=self.info["name"],
                    immute_domain=self.info["immute_domain"],
                    alias=self.info["alias"],
                    major_version=self.info["major_version"],
                    storages=self.info["storages"],
                    creator=self.info["creator"],
                    bk_cloud_id=self.info["bk_cloud_id"],
                    db_module_id=self.info["db_module_id"],
                    region=self.info["region"],
                    skip_machine=self.info["skip_machine"],
                    spec_id=self.info["spec_id"],
                    spec_config=self.info["spec_config"],
                    disaster_tolerance_level=self.info.get("disaster_tolerance_level", "NONE"),
                )
            elif self.info["cluster_type"] == ClusterType.MongoShardedCluster.value:
                pkg_create_mongo_cluster(
                    bk_biz_id=self.info["bk_biz_id"],
                    name=self.info["name"],
                    immute_domain=self.info["immute_domain"],
                    alias=self.info["alias"],
                    db_module_id=self.info["db_module_id"],
                    major_version=self.info["major_version"],
                    proxies=self.info["proxies"],
                    configs=self.info["configs"],
                    storages=self.info["storages"],
                    creator=self.info["creator"],
                    bk_cloud_id=self.info["bk_cloud_id"],
                    region=self.info["region"],
                    machine_specs=self.info["machine_specs"],
                    disaster_tolerance_level=self.info.get("disaster_tolerance_level", "NONE"),
                )
        except Exception as e:
            logger.error("add relationship to meta fail, error:{}".format(str(e)))
            return False
        logger.info("add mongodb relationship to meta successfully")
        return True

    def change_domain_app(self):
        """修改dns的app字段"""

        for domain in self.info["change_domain_app"]:
            domain_name = domain if domain.endswith(".") else "{}.".format(domain)
            try:
                DnsApi.update_domain_belong_app(
                    {
                        "app": self.info["app"],
                        "new_app": self.info["new_app"],
                        "domain_name": domain_name,
                        "bk_cloud_id": self.info["bk_cloud_id"],
                    }
                )
            except Exception as e:
                logger.error(
                    "change domain:{} dns app fail, from old app:{} to new app:{}, error:{}".format(
                        domain_name, self.info["app"], self.info["new_app"], str(e)
                    )
                )
                raise ValueError(
                    "change domain:{} dns app fail, from old app:{} to new app:{}, error:{}".format(
                        domain_name, self.info["app"], self.info["new_app"], str(e)
                    )
                )

    def shard_delete_domain(self):
        """shard删除domain"""

        dns = dns_manage.DnsManage(bk_biz_id=self.info["bk_biz_id"], bk_cloud_id=self.info["bk_cloud_id"])
        for delete_domain in self.info["delete_domain"]:
            dns.remove_domain_ip(del_instance_list=delete_domain["del_instance_list"], domain=delete_domain["domain"])

    def add_clb_domain(self):
        """添加clb到meta"""

        entry_type = ClusterEntryType.CLB
        cluster = Cluster.objects.get(
            bk_cloud_id=self.info["bk_cloud_id"], name=self.info["name"], bk_biz_id=self.info["bk_biz_id"]
        )
        proxy_objs = cluster.proxyinstance_set.all()
        clb_cluster_entry = ClusterEntry.objects.create(
            cluster=cluster,
            cluster_entry_type=entry_type,
            entry=self.info["clb"]["clb_ip"],
            creator=self.info["created_by"],
        )
        clb_cluster_entry.save()
        clb_cluster_entry.proxyinstance_set.add(*proxy_objs)
        clb_domain = ""
        if "clb_domain" in self.info["clb"]:
            clb_domain = self.info["clb"]["clb_domain"]
        if clb_domain != "":
            entry_type = ClusterEntryType.CLBDNS
            clbdns_cluster_entry = ClusterEntry.objects.create(
                cluster=cluster,
                cluster_entry_type=entry_type,
                forward_to_id=clb_cluster_entry.id,
                entry=clb_domain,
                creator=self.info["created_by"],
            )
            clbdns_cluster_entry.save()
            clbdns_cluster_entry.proxyinstance_set.add(*proxy_objs)
        clb_entry = CLBEntryDetail.objects.create(
            clb_ip=self.info["clb"]["clb_ip"],
            clb_id=self.info["clb"]["clb_id"],
            listener_id=self.info["clb"]["clb_listener_id"],
            clb_region=self.info["region"],
            entry_id=clb_cluster_entry.id,
            creator=self.info["created_by"],
        )
        clb_entry.save()
