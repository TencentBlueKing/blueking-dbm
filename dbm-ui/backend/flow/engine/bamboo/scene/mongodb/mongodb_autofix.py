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
from typing import Dict, List, Optional

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache, StorageInstance
from backend.db_services.mongodb.autofix.models import MongoAutofixCore
from backend.flow.utils.mongodb.mongodb_repo import MongoRepository
from backend.ticket.builders.mongodb.inst_desc import build_mongo_inst_desc

from .mongodb_machine_replace import MongoMachineReplaceFlow

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
        }

    def _rs_instances_for_fault_ip(self, fault_ip: str, cluster_ids: List[int]) -> List[dict]:
        """
        组装待替换实例描述。
        优先按故障 IP 在当前 meta 中匹配；若 CMR 已切到新机（重试场景），再按申请到的 target IP /
        Core.ports 回退，避免 instances=[] 导致 get_host_replace IndexError。
        """
        applied = self.autofix_info.get(fault_ip) or []
        target_ip = (applied[0] or {}).get("ip") if applied else None
        instances: List[dict] = []

        for cluster_id in cluster_ids:
            cluster_info = MongoRepository().fetch_one_cluster(with_domain=True, id=cluster_id)
            members = cluster_info.get_shards()[0].members
            matched = [m for m in members if m.ip == fault_ip]
            if not matched and target_ip:
                matched = [m for m in members if m.ip == target_ip]
                if matched:
                    logger.warning(
                        "mongo autofix rs_get_data fault_ip=%s not in meta, fallback target_ip=%s",
                        fault_ip,
                        target_ip,
                    )
            for member in matched:
                instances.append(
                    {
                        "cluster_id": cluster_id,
                        "cluster_name": cluster_info.name,
                        "db_version": cluster_info.major_version,
                        "domain": member.domain,
                        "port": member.port,
                    }
                )

        if instances:
            return instances

        # 再回退：Core.ports + 新机 StorageInstance（meta 已切、Repository 仍对不上时）
        core = (
            MongoAutofixCore.objects.filter(ticket_id=self.data.get("uid"), ip=fault_ip).order_by("-id").first()
            or MongoAutofixCore.objects.filter(ip=fault_ip).order_by("-id").first()
        )
        ports = list((core.ports if core else None) or [])
        if target_ip and ports:
            qs = (
                StorageInstance.objects.filter(machine__ip=target_ip, port__in=ports)
                .select_related("machine")
                .prefetch_related("cluster", "bind_entry")
            )
            for si in qs:
                desc = build_mongo_inst_desc(si, {})
                instances.append(desc)
            if instances:
                logger.warning(
                    "mongo autofix rs_get_data fallback StorageInstance target=%s ports=%s count=%s",
                    target_ip,
                    ports,
                    len(instances),
                )
                return instances

        raise ValueError(
            _("mongo autofix 无法组装替换实例: fault_ip={} target_ip={} cluster_ids={} " "(meta 可能已切机且无 ports 可回退)").format(
                fault_ip, target_ip, cluster_ids
            )
        )

    def shard_get_data(self) -> Dict:
        """分片集群获取参数（MongoClusterAutofixFlow 读取 infos[MongoShardedCluster][0]）"""

        flow_parameter = self.get_public_data()
        flow_parameter["infos"] = {ClusterType.MongoShardedCluster.value: []}
        bk_cloud_id = self.autofix_info["bk_cloud_id"]
        cluster_id = self.autofix_info["cluster_ids"][0]
        cluster_info = MongoRepository().fetch_one_cluster(id=cluster_id)
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
        flow_parameter["infos"][ClusterType.MongoShardedCluster.value].append(cluster)
        return flow_parameter

    def rs_get_data(self) -> Dict:
        """副本集获取参数（对齐 MONGODB_REPLICASET_CUTOFF → MongoReplaceFlow 入参）"""

        flow_parameter = self.get_public_data()
        flow_parameter["cluster_type"] = ClusterType.MongoReplicaSet.value
        flow_parameter["infos"] = []
        bk_cloud_id = self.autofix_info["bk_cloud_id"]
        cluster_ids = self.autofix_info["cluster_ids"]
        for mongod in self.autofix_info["mongod_list"]:
            instances = self._rs_instances_for_fault_ip(mongod["ip"], cluster_ids)
            if instances:
                flow_parameter["db_version"] = instances[0].get("db_version") or flow_parameter["db_version"]
            target = self.autofix_info[mongod["ip"]][0]
            target["spec_id"] = mongod["spec_id"]
            # replicaset_replace 在非 shard 场景取 info["mongodb"][0]
            flow_parameter["infos"].append(
                {
                    "cluster_id": cluster_ids[0] if len(cluster_ids) == 1 else cluster_ids,
                    "mongodb": [
                        {
                            "ip": mongod["ip"],
                            "bk_cloud_id": bk_cloud_id,
                            "spec_id": mongod["spec_id"],
                            "down": True,
                            "spec_config": mongod["spec_config"],
                            "target": target,
                            "instances": instances,
                        }
                    ],
                }
            )
        return flow_parameter

    def autofix(self):
        """进行自愈：payload 适配后统一走 MongoMachineReplaceFlow。"""

        if self.autofix_info["cluster_type"] == ClusterType.MongoReplicaSet.value:
            flow_data = self.rs_get_data()
        elif self.autofix_info["cluster_type"] == ClusterType.MongoShardedCluster.value:
            flow_data = self.shard_get_data()
        else:
            raise ValueError("unsupported autofix cluster_type={}".format(self.autofix_info.get("cluster_type")))
        MongoMachineReplaceFlow(self.root_id, flow_data).multi_host_replace_flow()
