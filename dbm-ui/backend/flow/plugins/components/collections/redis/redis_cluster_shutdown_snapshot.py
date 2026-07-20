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
from typing import Dict, List

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.components import DRSApi
from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceRole, InstanceStatus
from backend.db_meta.models import Cluster
from backend.db_meta.models.storage_set_dtl import NosqlStorageSetDtl
from backend.db_services.redis.util import is_redis_cluster_protocal
from backend.flow.consts import RedisRole
from backend.flow.models import RedisClusterShutdownMetaSnapshot
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.redis.redis_cluster_nodes import decode_cluster_nodes

logger = logging.getLogger("flow")


class RedisClusterShutdownMetaSnapshotService(BaseService):
    """
    redis集群下架前，保存集群完整元数据快照，用于审计与追溯
    需要保存：业务、域名、端口、架构类型、proxy密码、redis密码、
             proxy列表、主从关系(含分片/slot范围)、地区、规格、版本
    """

    @staticmethod
    def _get_slot_map_by_cluster_nodes(cluster: Cluster) -> Dict[int, str]:
        """
        redis_cluster协议集群(TendisPredixyRedisCluster/TendisPredixyTendisplusCluster/RedisCluster)
        没有NosqlStorageSetDtl记录，slot分布信息只存在于redis自身的集群拓扑中，
        需通过实时执行'cluster nodes'命令获取各master节点的slot分布
        """
        one_master = cluster.storageinstance_set.filter(
            instance_role=InstanceRole.REDIS_MASTER.value, status=InstanceStatus.RUNNING
        ).first()
        if one_master is None:
            return {}
        try:
            passwd_ret = PayloadHandler.redis_get_cluster_password(cluster)
            resp = DRSApi.redis_rpc(
                {
                    "addresses": ["{}:{}".format(one_master.machine.ip, one_master.port)],
                    "db_num": 0,
                    "password": passwd_ret.get("redis_password"),
                    "command": "cluster nodes",
                    "bk_cloud_id": cluster.bk_cloud_id,
                }
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.warning("获取集群{}的slot分布失败:{}".format(cluster.immute_domain, e))
            return {}
        if not resp or not resp[0].get("result"):
            return {}

        _, node_map = decode_cluster_nodes(resp[0]["result"])
        addr_to_instance_id = {
            "{}:{}".format(inst.machine.ip, inst.port): inst.id
            for inst in cluster.storageinstance_set.select_related("machine").all()
        }
        slot_map: Dict[int, str] = {}
        for addr, node in node_map.items():
            if node.get_role() != RedisRole.MASTER.value or node.slot_cnt == 0:
                continue
            instance_id = addr_to_instance_id.get(addr)
            if instance_id is not None:
                slot_map[instance_id] = node.slot_src_str
        return slot_map

    @staticmethod
    def _get_shard_map(cluster: Cluster) -> Dict[int, str]:
        """
        获取分片/slot分布：
        - redis_cluster协议集群(TendisPredixyRedisCluster/TendisPredixyTendisplusCluster/RedisCluster)：
          没有NosqlStorageSetDtl记录，需通过'cluster nodes'命令实时获取slot分布
        - Twemproxy系列集群：分片范围记录在NosqlStorageSetDtl中，直接读取
        - 其余(主从版)：没有分片/slot概念，返回空字典
        """
        if is_redis_cluster_protocal(cluster.cluster_type):
            return RedisClusterShutdownMetaSnapshotService._get_slot_map_by_cluster_nodes(cluster)
        if cluster.cluster_type not in ClusterType.redis_cluster_types():
            return {}
        return {
            dtl.instance_id: dtl.seg_range
            for dtl in NosqlStorageSetDtl.objects.filter(cluster=cluster).select_related("instance")
        }

    def _snapshot_cluster_meta(self, cluster: Cluster) -> Dict:
        proxy_objs = list(cluster.proxyinstance_set.select_related("machine").order_by("machine__ip", "port"))
        proxies = ["{}:{}".format(proxy.machine.ip, proxy.port) for proxy in proxy_objs]

        master_objs = list(
            cluster.storageinstance_set.select_related("machine")
            .filter(instance_inner_role=InstanceInnerRole.MASTER.value)
            .order_by("machine__ip", "port")
        )

        # master -> slave 主从关系，并附带分片范围（仅Twemproxy系列集群有意义），通过StorageInstanceTuple关联
        shard_map = self._get_shard_map(cluster)
        master_slave_pairs: List[Dict] = []
        for master_obj in master_objs:
            tuple_obj = master_obj.as_ejector.first()
            slave_addr = ""
            if tuple_obj is not None:
                slave_addr = "{}:{}".format(tuple_obj.receiver.machine.ip, tuple_obj.receiver.port)
            master_slave_pairs.append(
                {
                    "master": "{}:{}".format(master_obj.machine.ip, master_obj.port),
                    "slave": slave_addr,
                    "seg_range": shard_map.get(master_obj.id, ""),
                }
            )

        # 规格信息：记录proxy和后端(master)机器涉及的spec_id（按role+spec_id去重，spec_id为0表示未关联规格，同样记录）
        seen_role_specs = set()
        spec_config: List[Dict] = []
        for proxy in proxy_objs:
            key = ("proxy", proxy.machine.spec_id)
            if key not in seen_role_specs:
                seen_role_specs.add(key)
                spec_config.append({"role": "proxy", "spec_id": proxy.machine.spec_id})
        for master_obj in master_objs:
            key = ("backend", master_obj.machine.spec_id)
            if key not in seen_role_specs:
                seen_role_specs.add(key)
                spec_config.append({"role": "backend", "spec_id": master_obj.machine.spec_id})

        try:
            passwords = PayloadHandler.redis_get_cluster_password(cluster)
        except Exception as e:  # pylint: disable=broad-except
            self.log_error(_("获取集群{}密码失败:{}，密码将为空").format(cluster.immute_domain, e))
            passwords = {}

        port = proxy_objs[0].port if proxy_objs else (master_objs[0].port if master_objs else None)

        return {
            "bk_biz_id": cluster.bk_biz_id,
            "cluster_id": cluster.id,
            "cluster_name": cluster.name,
            "domain_name": cluster.immute_domain,
            "port": port,
            "cluster_type": cluster.cluster_type,
            "db_version": cluster.major_version,
            "region": cluster.region,
            "proxy_password": passwords.get("redis_proxy_password", ""),
            "redis_password": passwords.get("redis_password", ""),
            "proxies": proxies,
            "master_slave_pairs": master_slave_pairs,
            "spec_config": spec_config,
        }

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        root_id = self.runtime_attrs.get("root_pipeline_id")

        bk_biz_id = kwargs["bk_biz_id"]
        cluster_id = kwargs["cluster_id"]

        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        except Cluster.DoesNotExist:
            self.log_error(_("集群不存在: bk_biz_id={}, cluster_id={}").format(bk_biz_id, cluster_id))
            return False

        snapshot = self._snapshot_cluster_meta(cluster)
        RedisClusterShutdownMetaSnapshot.objects.create(root_id=root_id, **snapshot)

        self.log_info(
            _("已保存集群{}(id={})下架前元数据快照: proxy={}台, 主从对={}对").format(
                cluster.immute_domain,
                cluster.id,
                len(snapshot["proxies"]),
                len(snapshot["master_slave_pairs"]),
            )
        )
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class RedisClusterShutdownMetaSnapshotComponent(Component):
    name = __name__
    code = "redis_cluster_shutdown_meta_snapshot"
    bound_service = RedisClusterShutdownMetaSnapshotService
