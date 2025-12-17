"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.utils.translation import gettext as _

from backend.db_meta.enums.cluster_type import ClusterType
from backend.flow.engine.validate.mongodb_base_validate import MongoDBBaseValidator
from backend.flow.utils.mongodb.mongodb_repo import MongoRepository


class MongodbInstanceMigrateValidator(MongoDBBaseValidator):
    """
    mongodb实例迁移的校验类
    判断传入flow的data参数合法性
    校验内容：
    每行入参校验：
        检验1：集群否是同一个集群类型
        检验2：校验副本集的节点数是否一致
        检验3：校验副本集的亲和性是否一致
        检验4：校验副本集的实例数是否一致
        检验5：校验副本集的port是否有重合
        检验6：校验副本集的地域是否一致
        检验7：校验副本集的db版本是否一致

    """

    cluster_type: str = ""
    row_replica_set_clusster_info: list = None
    replica_set_all_cluster_id: list = []
    row_clusster_info: list = None
    cluster_shard_by_id: dict = {}

    def __check_cluster(self, info, index):
        """
        检查实例迁移的合法性
        """

        self.row_replica_set_clusster_info = []
        self.row_clusster_info = []
        cluster_ids = []
        if self.cluster_type == ClusterType.MongoReplicaSet.value:
            cluster_ids = info["cluster_ids"]
            self.replica_set_all_cluster_id.extend(cluster_ids)
        elif self.cluster_type == ClusterType.MongoShardedCluster.value:
            cluster_id = info["cluster_id"]
            cluster_ids = [cluster_id]
            if str(cluster_id) not in self.cluster_shard_by_id:
                self.cluster_shard_by_id[str(cluster_id)] = []
            self.cluster_shard_by_id[str(cluster_id)].extend(info.get("shard_name"))
        for cluster_id in cluster_ids:
            cluster_info = MongoRepository().fetch_one_cluster(id=cluster_id)
            if not cluster_info:
                error_msg = _("mongodb集群{}不存在").format(cluster_id)
                return [
                    {"field": "cluster_ids", "index": index, "row_key": info.get("row_key", ""), "errors": error_msg}
                ]
            if self.cluster_type == ClusterType.MongoReplicaSet.value:
                self.row_replica_set_clusster_info.append(cluster_info)
            elif self.cluster_type == ClusterType.MongoShardedCluster.value:
                self.row_clusster_info.append(cluster_info)

        return []

    def __check_cluster_type(self, info, index):
        """
        检查集群类型是否一致
        """

        if self.cluster_type == ClusterType.MongoReplicaSet.value:
            for cluster in self.row_replica_set_clusster_info:
                if cluster.cluster_type != self.cluster_type:
                    error_msg = _("集群{}的类型不属于{}").format(cluster.name, self.cluster_type)
                    return [
                        {
                            "field": "cluster_ids",
                            "index": index,
                            "row_key": info.get("row_key", ""),
                            "errors": error_msg,
                        }
                    ]
        elif self.cluster_type == ClusterType.MongoShardedCluster.value:
            for cluster in self.row_clusster_info:
                if cluster.cluster_type != self.cluster_type:
                    error_msg = _("集群{}的类型不属于{}").format(cluster.name, self.cluster_type)
                    return [
                        {
                            "field": "cluster_ids",
                            "index": index,
                            "row_key": info.get("row_key", ""),
                            "errors": error_msg,
                        }
                    ]
        return []

    def __check_replica_set_nodes(self, info, index):
        """
        检查副本集的节点数是否一致
        """

        node_set = set()
        node_info, msg = {}, ""
        for cluster in self.row_replica_set_clusster_info:
            node_num = len(cluster.get_shards()[0].members)
            if str(node_num) not in node_info:
                node_info[str(node_num)] = []
            node_info[str(node_num)].append(cluster.name)
            if node_num not in node_set:
                node_set.add(node_num)

        for node_num, cluster_names in node_info.items():
            msg += _("节点数为{}的集群有{}个，分别为{}\n").format(node_num, len(cluster_names), cluster_names)

        if len(node_set) > 1:
            error_msg = _("副本集的节点数不一致，详细信息为{}").format(msg)
            return [{"field": "cluster_ids", "index": index, "row_key": info.get("row_key", ""), "errors": error_msg}]
        return []

    def __check_replica_set_affinity(self, info, index):
        """
        检查副本集的亲和性是否一致
        """

        affinity_set = set()
        affinity_info, msg = {}, ""
        for cluster in self.row_replica_set_clusster_info:
            affinity = cluster.affinity
            if affinity not in affinity_info:
                affinity_info[affinity] = []
            affinity_info[affinity].append(cluster.name)
            if affinity not in affinity_set:
                affinity_set.add(affinity)

        for affinity, cluster_names in affinity_info.items():
            msg += _("亲和性为{}的集群有{}个，分别为{}\n").format(affinity, len(cluster_names), cluster_names)
        if len(affinity_set) > 1:
            error_msg = _("副本集的亲和性不一致，亲和性信息为{}").format(msg)
            return [{"field": "cluster_ids", "index": index, "row_key": info.get("row_key", ""), "errors": error_msg}]
        return []

    def __check_replica_set_port(self, info, index):
        """
        检查副本集和分片集群shard的port是否有重合
        """

        port_set = set()
        port_info, msg = {}, ""
        if self.cluster_type == ClusterType.MongoReplicaSet.value:
            for cluster in self.row_replica_set_clusster_info:
                port = cluster.get_shards()[0].members[0].port
                if str(port) not in port_info:
                    port_info[str(port)] = []
                port_info[str(port)].append(cluster.name)
                if port not in port_set:
                    port_set.add(port)

            for port, cluster_names in port_info.items():
                msg += _("port为{}的集群有{}个，分别为{}\n").format(port, len(cluster_names), cluster_names)
            if len(port_set) < len(self.row_replica_set_clusster_info):
                error_msg = _("副本集的port有重复，port信息为{}").format(msg)
                return [
                    {"field": "cluster_ids", "index": index, "row_key": info.get("row_key", ""), "errors": error_msg}
                ]
        elif self.cluster_type == ClusterType.MongoShardedCluster.value:
            shard_name = info.get("shard_name")
            for cluster in self.row_clusster_info:
                shards = cluster.get_shards()
                for shard in shards:
                    if shard.set_name in shard_name:
                        port = shard.members[0].port
                        if str(port) not in port_info:
                            port_info[str(port)] = []
                        port_info[str(port)].append(shard.set_name)
                        if port not in port_set:
                            port_set.add(port)
            for port, set_name_list in port_info.items():
                msg += _("port为{}的shard有{}个，分别为{}\n").format(port, len(set_name_list), set_name_list)
            if len(port_set) < len(shard_name):
                error_msg = _("分片集群shard的port有重复，port信息为{}").format(msg)
                return [
                    {"field": "cluster_ids", "index": index, "row_key": info.get("row_key", ""), "errors": error_msg}
                ]
        return []

    def __check_replica_set_region(self, info, index):
        """
        检查副本集的地域是否一致
        """

        region_set = set()
        region_info, msg = {}, ""
        for cluster in self.row_replica_set_clusster_info:
            region = cluster.region
            if region not in region_info:
                region_info[region] = []
            region_info[region].append(cluster.name)
            if region not in region_set:
                region_set.add(region)

        for region, cluster_names in region_info.items():
            msg += _("地域为{}的集群有{}个，分别为{}\n").format(region, len(cluster_names), cluster_names)
        if len(region_set) > 1:
            error_msg = _("副本集的地域不一致，地域信息为{}").format(msg)
            return [{"field": "cluster_ids", "index": index, "row_key": info.get("row_key", ""), "errors": error_msg}]
        return []

    def __check_replica_set_db_version(self, info, index):
        """
        检查副本集的db版本是否一致
        """

        db_version_set = set()
        db_version_info, msg = {}, ""
        for cluster in self.row_replica_set_clusster_info:
            db_version = cluster.major_version
            if db_version not in db_version_info:
                db_version_info[db_version] = []
            db_version_info[db_version].append(cluster.name)
            if db_version not in db_version_set:
                db_version_set.add(db_version)
        for db_version, cluster_names in db_version_info.items():
            msg += _("db版本为{}的集群有{}个，分别为{}\n").format(db_version, len(cluster_names), cluster_names)
        if len(db_version_set) > 1:
            error_msg = _("副本集的db版本不一致，db版本信息为{}").format(msg)
            return [{"field": "db_version", "index": index, "row_key": info.get("row_key", ""), "errors": error_msg}]
        return []

    def run_check_for_info(self, info, index):
        """
        发起校验
        """

        if self.cluster_type == ClusterType.MongoReplicaSet.value:
            error_msgs = self.__check_cluster(info, index)
            if error_msgs:
                return error_msgs
            error_msgs = self.__check_cluster_type(info, index)
            if error_msgs:
                return error_msgs
            error_msgs = self.__check_replica_set_nodes(info, index)
            if error_msgs:
                return error_msgs
            error_msgs = self.__check_replica_set_affinity(info, index)
            if error_msgs:
                return error_msgs
            error_msgs = self.__check_replica_set_port(info, index)
            if error_msgs:
                return error_msgs
            error_msgs = self.__check_replica_set_region(info, index)
            if error_msgs:
                return error_msgs
            error_msgs = self.__check_replica_set_db_version(info, index)
            if error_msgs:
                return error_msgs
        elif self.cluster_type == ClusterType.MongoShardedCluster.value:
            error_msgs = self.__check_cluster(info, index)
            if error_msgs:
                return error_msgs
            error_msgs = self.__check_cluster_type(info, index)
            if error_msgs:
                return error_msgs
            error_msgs = self.__check_replica_set_port(info, index)
            if error_msgs:
                return error_msgs

        return []

    def pre_check_reapeat_instance(self):
        """检查迁移重复的实例"""

        if self.cluster_type == ClusterType.MongoReplicaSet.value:
            unique_cluster_id = set()
            repeat_cluster_id = set()
            for cluster_id in self.replica_set_all_cluster_id:
                if cluster_id not in unique_cluster_id:
                    unique_cluster_id.add(cluster_id)
                else:
                    repeat_cluster_id.add(cluster_id)
            if repeat_cluster_id:
                cluster_name = [
                    MongoRepository().fetch_one_cluster(id=cluster_id).name for cluster_id in repeat_cluster_id
                ]
                return _("单据中副本集的集群重复，重复的集群为{}").format(cluster_name)
        elif self.cluster_type == ClusterType.MongoShardedCluster.value:
            error_msgs = ""
            for cluster_id, shard_name in self.cluster_shard_by_id.items():
                unique_shard_name = set()
                repeat_shard_name = set()
                for shard in shard_name:
                    if shard not in unique_shard_name:
                        unique_shard_name.add(shard)
                    else:
                        repeat_shard_name.add(shard)
                if repeat_shard_name:
                    cluster_name = MongoRepository().fetch_one_cluster(id=cluster_id).name
                    error_msgs += _("单据中分片集群{}的shard有重复，重复的shard为{}\n").format(cluster_name, list(repeat_shard_name))
            return error_msgs

    def __call__(self):
        """
        发起校验, 实例函数化
        """

        self.replica_set_all_cluster_id = []
        self.row_clusster_info = []
        self.cluster_shard_by_id = {}
        self.cluster_type = self.data["cluster_type"]  # MongoReplicaSet
        # 阶段1 检测每个行的数据合法性
        error_msgs = []
        for index, info in enumerate(self.data["infos"]):
            error_msgs += self.run_check_for_info(info=info, index=index)
        if error_msgs:
            return error_msgs

        # 阶段2 聚合校验
        error_msg = self.pre_check_reapeat_instance()
        if error_msg:
            return error_msg
        return None
