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
import logging.config
from typing import Dict, Optional

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache
from backend.flow.utils.mongodb.mongodb_repo import MongoRepository

from . import mongodb_cluster_autofix, mongodb_replace

logger = logging.getLogger("flow")


class MongoAutofixFlow(object):
    """MongoDB自愈flow"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        传入参数
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """

        self.root_id = root_id
        self.data = data
        self.autofix_info = self.data["infos"][0]

    def get_public_data(self) -> Dict:
        """参数公共部分"""

        bk_biz_id = self.autofix_info["bk_biz_id"]
        return {
            "bk_biz_id": bk_biz_id,
            "uid": self.data["uid"],
            "bk_app_abbr": AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr,
            "created_by": self.data["created_by"],
            "ticket_type": self.data["ticket_type"],
            "db_version": "",
            "infos": {"MongoReplicaSet": [], "MongoShardedCluster": []},
        }

    def shard_get_data(self) -> Dict:
        """分片集群获取参数"""

        flow_parameter = self.get_public_data()
        bk_cloud_id = self.autofix_info["bk_cloud_id"]
        cluster_id = self.autofix_info["cluster_ids"][0]
        cluster_info = MongoRepository().fetch_one_cluster(withDomain=False, id=cluster_id)
        flow_parameter["db_version"] = cluster_info.major_version
        config = cluster_info.get_config()
        shards = cluster_info.get_shards()
        cluster = {}
        mongos_nodes = []
        mongo_config = []
        mongodb = []
        # 获取mongos参数
        for mongos in self.autofix_info["mongos_list"]:
            target = self.autofix_info[mongos["ip"]][0]
            target["spec_id"] = mongos["spec_id"]
            mongos_nodes.append(
                {
                    "ip": mongos["ip"],
                    "bk_cloud_id": bk_cloud_id,
                    "spec_id": mongos["spec_id"],
                    "down": True,
                    "spec_config": mongos["spec_config"],
                    "target": target,
                    "instances": [
                        {
                            "cluster_id": cluster_id,
                            "cluster_name": cluster_info.name,
                            "db_version": cluster_info.major_version,
                            "domain": self.autofix_info["immute_domain"],
                            "port": int(cluster_info.get_mongos()[0].port),
                        }
                    ],
                }
            )
        for mongod in self.autofix_info["mongod_list"]:
            target = self.autofix_info[mongod["ip"]][0]
            target["spec_id"] = mongod["spec_id"]
            ip_info = {
                "ip": mongod["ip"],
                "bk_cloud_id": bk_cloud_id,
                "spec_id": mongod["spec_id"],
                "down": True,
                "spec_config": mongod["spec_config"],
                "target": target,
                "instances": [],
            }
            instances = []
            # config
            for member in config.members:
                if member.ip == mongod["ip"]:
                    instances.append(
                        {
                            "cluster_id": cluster_id,
                            "cluster_name": cluster_info.name,
                            "seg_range": config.set_name,
                            "db_version": cluster_info.major_version,
                            "port": member.port,
                        }
                    )
                    break
            if instances:
                ip_info["instances"] = instances
                mongo_config.append(ip_info)
                continue
            # shard
            for shard in shards:
                for member in shard:
                    if member.ip == mongod["ip"]:
                        instances.append(
                            {
                                "cluster_id": cluster_id,
                                "cluster_name": cluster_info.name,
                                "seg_range": shard.set_name,
                                "db_version": cluster_info.major_version,
                                "port": member.port,
                            }
                        )
                        break
            ip_info["instances"] = instances
            mongodb.append(ip_info)
        cluster["mongos"] = mongos_nodes
        cluster["mongo_config"] = mongo_config
        cluster["mongodb"] = mongodb
        flow_parameter["infos"]["MongoShardedCluster"].append(cluster)
        return flow_parameter

    def rs_get_data(self) -> Dict:
        """副本集获取参数"""

        flow_parameter = self.get_public_data()
        bk_cloud_id = self.autofix_info["bk_cloud_id"]
        cluster_ids = self.autofix_info["cluster_ids"]
        for mongod in self.autofix_info["mongod_list"]:
            instances = []
            for cluster_id in cluster_ids:
                cluster_info = MongoRepository().fetch_one_cluster(withDomain=True, id=cluster_id)
                flow_parameter["db_version"] = cluster_info.major_version
                for member in cluster_info.get_shards()[0].members:
                    if mongod["ip"] == member.ip:
                        instances.append(
                            {
                                "cluster_id": cluster_id,
                                "cluster_name": cluster_info.name,
                                "db_version": cluster_info.major_version,
                                "domain": member.domain,
                                "port": member.port,
                            }
                        )
            target = self.autofix_info[mongod["ip"]][0]
            target["spec_id"] = mongod["spec_id"]
            flow_parameter["infos"]["MongoReplicaSet"].append(
                {
                    "ip": mongod["ip"],
                    "bk_cloud_id": bk_cloud_id,
                    "spec_id": mongod["spec_id"],
                    "down": True,
                    "spec_config": mongod["spec_config"],
                    "target": target,
                    "instances": instances,
                }
            )
        return flow_parameter

    def autofix(self):
        """进行自愈"""

        # 副本集
        if self.autofix_info["cluster_type"] == ClusterType.MongoReplicaSet.value:
            mongodb_replace.MongoReplaceFlow(self.root_id, self.rs_get_data()).multi_host_replace_flow()
        # 分片集群
        elif self.autofix_info["cluster_type"] == ClusterType.MongoShardedCluster.value:
            mongodb_cluster_autofix.MongoClusterAutofixFlow(self.root_id, self.shard_get_data()).cluster_autofix_flow()
