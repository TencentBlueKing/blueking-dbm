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
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.api.cluster import nosqlcomm
from backend.db_meta.enums import ClusterType, InstanceRole, InstanceStatus
from backend.db_meta.enums.comm import RedisVerUpdateNodeType
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_services.redis.redis_dts.constants import REDIS_CONF_DEL_SLAVEOF
from backend.db_services.redis.util import is_redis_cluster_protocal, is_twemproxy_proxy_type
from backend.flow.consts import (
    DEFAULT_LAST_IO_SECOND_AGO,
    DEFAULT_MASTER_DIFF_TIME,
    SwitchType,
    SyncType,
    WriteContextOpType,
)
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import ClusterIPsDbmonInstallAtomJob, ClusterProxysUpgradeAtomJob
from backend.flow.engine.bamboo.scene.redis.atom_jobs.redis_makesync import RedisMakeSyncAtomJob
from backend.flow.plugins.components.collections.common.empty_node import EmptyNodeComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.exec_shell_script import ExecuteShellScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_config import RedisConfigComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.redis_update_version import RedisUpdateVersionComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.flow.utils.redis.redis_proxy_util import (
    async_multi_clusters_precheck,
    get_cache_backup_mode,
    get_cluster_info_by_cluster_id,
    get_cluster_info_by_ip,
    get_major_version_by_version_name,
    get_proxy_version_by_ip,
    get_proxy_version_names_by_cluster_type,
    get_redis_version_by_ip,
    get_storage_version_names_by_cluster_type,
    get_twemproxy_cluster_server_shards,
)
from backend.flow.utils.redis.redis_util import version_ge, version_gt

logger = logging.getLogger("flow")

# RedisCluster / Predixy* / Tendisplus 走自身 failover 协议或不需要 flush.
# 这里的 "after upgrade" 指 actuator 在 startRedis (新版本) 加载完毕之后立即 flushall:
# 与 dbactuator/pkg/atomjobs/atomredis/redis_version_update.go::flushDataAfterStart 保持对齐.
_FLUSH_AFTER_UPGRADE_SUPPORTED_CLUSTER_TYPES = {
    ClusterType.TendisTwemproxyRedisInstance.value,
    ClusterType.TendisRedisInstance.value,
    ClusterType.TwemproxyTendisSSDInstance.value,
}


@dataclass
class _ClusterUpgradeCtx:
    """(非 TendisRedisInstance) Backend 单 cluster 单 target_version 升级上下文."""

    pipeline: SubBuilder
    act_kwargs: ActKwargs
    cluster_meta_data: Dict
    ips: Set[str]
    target_major_version: str
    trans_files: Optional[GetFileList] = None
    # 流程中后段才会被填充, 见 _create_redis_cluster_upgrade_flow
    pairs_to_switch: List = field(default_factory=list)

    @property
    def cluster_id(self) -> int:
        return self.cluster_meta_data["cluster_id"]

    @property
    def first_master_ip(self) -> str:
        return next(iter(self.cluster_meta_data["master_ports"]))


@dataclass
class _InstancePairUpgradeCtx:
    """TendisRedisInstance: 以 (master_ip, slave_ip) 物理 pair 为单位的升级上下文."""

    sub_pipeline: SubBuilder
    act_kwargs: ActKwargs
    cluster_ids: List[int]
    per_cluster_meta: Dict[int, Dict]
    master_ip: str
    slave_ip: str
    master_ports_union: List[int]
    slave_ports_union: List[int]
    target_major_version: str
    upgrade_master: bool

    @property
    def anchor_meta(self) -> Dict:
        return self.per_cluster_meta[self.cluster_ids[0]]


class RedisClusterVersionUpdateOnline(object):
    """
    redis集群在线版本升级
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表,是dict格式
        """
        self.root_id = root_id
        self.data = data
        # cluster_id -> get_cluster_info_by_cluster_id() 返回的 meta dict
        # (master_ports / slave_ports / immute_domain / cluster_type / bk_cloud_id 等),
        # 主要给后续构建 sub_flow 时使用.
        self.cluster_cache: Dict[int, Dict] = {}
        # cluster_id -> Cluster ORM 对象, 仅 precheck 阶段使用:
        # 既要读 cluster_type / immute_domain 等标量, 也要走 ORM 关联
        self._cluster_objs: Dict[int, Cluster] = {}
        self.cluster_versions_ips = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
        # TendisRedisInstance专用:按 (master_ip, slave_ip) 分桶的升级单元
        # value 结构: {
        #     "target_version": str,        # 同一 IP 上所有集群的目标版本必须一致
        #     "cluster_ids": List[int],     # IP 对上所有参与升级的集群 id (经 precheck 校验完整)
        #     "upgrade_master": bool,       # False => 仅升级 slave; True => 主从都升级
        # }
        self.instance_pair_buckets: Dict[Tuple[str, str], Dict] = {}
        # TendisRedisInstance 辅助索引,仅用于 precheck 校验
        # key: ip (任一 master_ip 或 slave_ip)
        # value: {"target_versions": Set[str], "cluster_ids": Set[int], "pair_partners": Set[str],
        #         "as_master_cluster_ids": Set[int], "as_slave_cluster_ids": Set[int]}
        self.instance_ip_index: Dict[str, Dict] = {}
        # 记录每个 TendisRedisInstance cluster_id 的 pair 与目标版本,避免重复查询 meta
        self.instance_cluster_meta: Dict[int, Dict] = {}
        self.precheck()

    def precheck(self):
        """
        将 [infos] 解析为两类结构:
        1. 非 TendisRedisInstance: self.cluster_versions_ips[node_type][cluster_id][target_version] = {ips}
        2. TendisRedisInstance Backend: self.instance_pair_buckets[(master_ip, slave_ip)] = bucket
           同时构建 self.instance_ip_index 供 IP 维度校验使用

        校验覆盖:
        - 集群是否存在, 非 running 状态 proxy/redis, proxy/redis 连通性 (async_multi_clusters_precheck)
        - 版本信息合法性 / 是否降级 / master-slave 配对
        - TendisRedisInstance 专属的 IP/pair 维度校验 (见 _validate_instance_pair_buckets)
        """
        to_precheck_cluster_ids: List[int] = []
        for input_item in self.data["infos"]:
            cluster_ids = RedisClusterVersionUpdateOnline.get_cluster_ids_from_info_item(input_item)
            to_precheck_cluster_ids.extend(cluster_ids)
        # 并发检查多个cluster的proxy、redis实例状态
        async_multi_clusters_precheck(to_precheck_cluster_ids)

        for input_item in self.data["infos"]:
            self._index_info_item(input_item)

        self._validate_proxy_buckets()
        self._validate_backend_buckets()
        self._validate_instance_pair_buckets()

    def _make_act_kwargs(self) -> ActKwargs:
        """构造默认的 ActKwargs (绑定 CommonContext + 启用 trans_data 合并)."""
        kw = ActKwargs()
        kw.set_trans_data_dataclass = CommonContext.__name__
        kw.is_update_trans_data = True
        return kw

    def _get_cluster(self, cluster_id: int) -> Cluster:
        """带缓存的 Cluster ORM 取数, 避免 precheck 阶段对同一 cluster 重复 SELECT."""
        cluster = self._cluster_objs.get(cluster_id)
        if cluster is None:
            cluster = Cluster.objects.get(id=cluster_id)
            self._cluster_objs[cluster_id] = cluster
        return cluster

    def _index_info_item(self, input_item: Dict):
        """解析单条 info 项, 分流到 cluster_versions_ips 或 instance_pair_buckets."""
        cluster_ids = self.get_cluster_ids_from_info_item(input_item)
        node_type = input_item.get("node_type")
        if node_type not in (RedisVerUpdateNodeType.Proxy.value, RedisVerUpdateNodeType.Backend.value):
            raise Exception(
                _("未知的结点类型: '{}' 必须是 '{}' 或 '{}'").format(
                    node_type, RedisVerUpdateNodeType.Proxy.value, RedisVerUpdateNodeType.Backend.value
                )
            )
        if not input_item.get("target_versions") or len(input_item["target_versions"]) == 0:
            raise Exception(_("redis集群 {} 目标版本为空?").format(cluster_ids))

        for cid in cluster_ids:
            cid = int(cid)
            if node_type == RedisVerUpdateNodeType.Backend.value:
                cluster = self._get_cluster(cid)
                if cluster.cluster_type == ClusterType.TendisRedisInstance:
                    self._index_instance_backend_entry(cluster, input_item)
                    continue
            # 非 TendisRedisInstance Backend / 所有 Proxy 沿用旧索引
            for target in input_item["target_versions"]:
                self.cluster_versions_ips[node_type][cid][target["version"]].add(target["ip"])

    def _index_instance_backend_entry(self, cluster: Cluster, input_item: Dict):
        """TendisRedisInstance Backend 分支: 校验单 version 并调用 _register_instance_info_item."""
        versions_in_item = {t["version"] for t in input_item["target_versions"]}
        if len(versions_in_item) > 1:
            # 同 IP 对无法承载多版本
            raise Exception(
                _("集群 {} 的 target_versions 里包含多个 version {}, 主从版升级不支持此组合").format(
                    cluster.immute_domain, versions_in_item
                )
            )
        target_version = next(iter(versions_in_item))
        ips_in_item = {t["ip"] for t in input_item["target_versions"]}
        self._register_instance_info_item(cluster, target_version, ips_in_item)

    def _validate_proxy_buckets(self):
        """Proxy 升降级合法性检查."""
        for cluster_id, target_pairs in self.cluster_versions_ips["Proxy"].items():
            cluster = self._get_cluster(cluster_id)
            valid_versions = get_proxy_version_names_by_cluster_type(cluster.cluster_type, True)
            for target_version, ips in target_pairs.items():
                if target_version not in valid_versions:
                    raise Exception(
                        _("Redis集群 {}, 目标版本 {} 不合法, 合法的版本: {}").format(
                            cluster.immute_domain, target_version, valid_versions
                        )
                    )
                ip_cur_ver = {ip: get_proxy_version_by_ip(cluster_id, ip) for ip in ips}
                if all(target_version == ip_cur_ver[ip] for ip in ips):
                    raise Exception(
                        _("集群 {} 所有proxy当前版本等于目标版本: {}, 无需执行").format(cluster.immute_domain, target_version)
                    )

    def _validate_backend_buckets(self):
        """非 TendisRedisInstance 的 Backend 升级合法性检查."""
        for cluster_id, target_pairs in self.cluster_versions_ips["Backend"].items():
            cluster = self._get_cluster(cluster_id)
            if len(target_pairs) > 1:
                raise Exception(
                    _("集群 {} Backend 不允许在同一单据中升级到多个目标版本: {}").format(
                        cluster.immute_domain, sorted(target_pairs.keys())
                    )
                )
            valid_versions = get_storage_version_names_by_cluster_type(cluster.cluster_type, True)
            for target_version, ips in target_pairs.items():
                self._validate_backend_target_pair(cluster, valid_versions, target_version, ips)

    def _validate_backend_target_pair(
        self, cluster: Cluster, valid_versions: List[str], target_version: str, ips: Set[str]
    ):
        """对单个 (target_version, ips) 组合做版本合法性 / 降级 / master-slave 配对校验."""
        if target_version not in valid_versions:
            raise Exception(
                _("Redis集群 {}, 目标版本 {} 不合法, 合法的版本: {}").format(cluster.immute_domain, target_version, valid_versions)
            )
        cluster_id = cluster.id
        ip_cur_ver = {ip: get_redis_version_by_ip(cluster_id, ip) for ip in ips}
        cluster_info = get_cluster_info_by_cluster_id(cluster_id)
        master_ip_to_slave_ip = cluster_info.get("master_ip_to_slave_ip", {})
        master_ports = cluster_info.get("master_ports", {})
        slave_ports = cluster_info.get("slave_ports", {})

        for ip in ips:
            if version_gt(ip_cur_ver[ip], target_version):
                raise Exception(
                    _("集群 {} storage IP {} 当前版本 {} > 目标版本: {},不支持降级").format(
                        cluster.immute_domain, ip, ip_cur_ver[ip], target_version
                    )
                )
            if ip in master_ports:
                self._validate_master_slave_pairing(cluster, ip, ips, master_ip_to_slave_ip)
            elif ip not in slave_ports:
                raise Exception(_("集群 {} IP {} 既不是master也不是slave").format(cluster.immute_domain, ip))

    def _validate_master_slave_pairing(
        self,
        cluster: Cluster,
        master_ip: str,
        ips: Set[str],
        master_ip_to_slave_ip: Dict[str, str],
    ):
        """非 TendisRedisInstance Backend: master 升级必须与对应 slave 同批提交, 不允许"只升 master"."""
        slave_ip = master_ip_to_slave_ip.get(master_ip)
        if not slave_ip:
            raise Exception(_("集群 {} Master {} 没有找到对应的 Slave").format(cluster.immute_domain, master_ip))
        if slave_ip not in ips:
            raise Exception(
                _("集群 {} 的 Master {} 升级必须同时将对应 Slave {} 加入升级列表, 当前 ips={}").format(
                    cluster.immute_domain, master_ip, slave_ip, sorted(ips)
                )
            )

    def _register_instance_info_item(self, cluster: Cluster, target_version: str, ips_in_item: Set[str]):
        """
        TendisRedisInstance 单条 info 项注册到 pair 桶与 IP 索引.
        仅做单集群元信息解析 + 聚合, 完整校验在 _validate_instance_pair_buckets 里进行.
        """
        cluster_id = cluster.id
        master_inst = cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value).first()
        if not master_inst:
            raise Exception(_("集群 {} 未找到 master 实例").format(cluster.immute_domain))
        tuple_obj = master_inst.as_ejector.first()
        if not tuple_obj:
            raise Exception(_("集群 {} master {} 没有对应的 slave 记录").format(cluster.immute_domain, master_inst.ip_port))
        slave_inst = tuple_obj.receiver
        master_ip, slave_ip = master_inst.machine.ip, slave_inst.machine.ip

        # 用户在 info 项里声明的 ips 必须全部属于这个 pair
        unknown_ips = ips_in_item - {master_ip, slave_ip}
        if unknown_ips:
            raise Exception(
                _("集群 {} 的 target_versions 中 IP {} 不属于该集群的主从对 ({}/{})").format(
                    cluster.immute_domain, sorted(unknown_ips), master_ip, slave_ip
                )
            )
        if slave_ip not in ips_in_item:
            # 主从版升级必须包含 slave (slave 先升级)
            raise Exception(
                _("集群 {} 主从版升级必须包含 slave_ip={}, 当前只指定了 {}").format(
                    cluster.immute_domain, slave_ip, sorted(ips_in_item)
                )
            )
        upgrade_master = master_ip in ips_in_item

        # 记录 cluster 级别 meta, 给后续 sub_flow 复用
        self.instance_cluster_meta[cluster_id] = {
            "cluster": cluster,
            "master_ip": master_ip,
            "slave_ip": slave_ip,
            "target_version": target_version,
            "upgrade_master": upgrade_master,
        }

        # 聚合到 pair 桶
        pair_key = (master_ip, slave_ip)
        bucket = self.instance_pair_buckets.setdefault(
            pair_key,
            {
                "target_versions": set(),
                "cluster_ids": [],
                "upgrade_master_flags": set(),
            },
        )
        bucket["target_versions"].add(target_version)
        if cluster_id not in bucket["cluster_ids"]:
            bucket["cluster_ids"].append(cluster_id)
        bucket["upgrade_master_flags"].add(upgrade_master)

        # 聚合到 IP 索引 (用于跨 pair 校验)
        for ip, role_key in ((master_ip, "as_master_cluster_ids"), (slave_ip, "as_slave_cluster_ids")):
            idx = self.instance_ip_index.setdefault(
                ip,
                {
                    "target_versions": set(),
                    "cluster_ids": set(),
                    "pair_partners": set(),
                    "as_master_cluster_ids": set(),
                    "as_slave_cluster_ids": set(),
                },
            )
            idx["target_versions"].add(target_version)
            idx["cluster_ids"].add(cluster_id)
            idx["pair_partners"].add(slave_ip if ip == master_ip else master_ip)
            idx[role_key].add(cluster_id)

    def _validate_instance_pair_buckets(self):
        """
        对 TendisRedisInstance 的 pair/IP 索引做五类校验:
        1. 单 IP 目标版本一致;
        2. 单 IP 仅属一种 (master_ip, slave_ip) 拓扑;
        3. 单 IP 上兄弟集群必须全部在升级列表 (master 侧和 slave 侧分别校验);
        4. 同一 pair 内 upgrade scope 一致;
        5. 复用 backend 的 version-validity / downgrade 校验 (每 pair 一次).
        """
        if not self.instance_pair_buckets:
            return

        # 规则 3 用到的常量, 提到循环外避免重复构造
        # master 侧: 该 IP 上所有 master 实例对应的集群都必须在
        # slave  侧: 该 IP 上所有 slave  实例对应的集群都必须在
        # 没有同时校验 "该 IP 上所有集群(不区分角色)" 因为一个 IP 作为 master 或 slave 只会有一种角色
        #
        # 完备性说明: 该校验只遍历 instance_ip_index, 即只覆盖本次 infos 中出现过的 IP.
        # 看似可能漏掉 "整个 IP 都未出现在请求里" 的兄弟集群, 但 DBM 部署模型保证不会出现这种漏检:
        #   1. 非 TendisRedisInstance 集群之间不存在物理 IP 重叠;
        #   2. TendisRedisInstance 同一 (master_ip, slave_ip) pair 上的兄弟集群共享完全一致的角色映射,
        #      即如果 1.1.1.1 是集群 A 的 master, 它也是同 pair 上 B/C/... 所有兄弟集群的 master;
        #      不存在 "同一 IP 在 A 中是 master 而在 B 中是 slave" 的混合角色情况.
        # 因此只要请求里包含了该 pair 上的任一兄弟集群, 该 pair 的 master_ip 与 slave_ip 都会进入索引,
        # 下面通过 StorageInstance 的 DB 反查即可发现所有未提交的兄弟, 不存在静默跳过的盲区.
        _pair_scope_err = _(
            "{} {} 上的集群 {} 未加入本次升级。"
            "主从版升级会执行主从切换, 如果只切换部分集群, 会导致该 IP 同时承载 master 和 slave 实例, "
            "破坏角色一致性, 请将这些集群一并加入升级"
        )
        _roles = (
            ("as_master_cluster_ids", InstanceRole.REDIS_MASTER.value, "master_ip"),
            ("as_slave_cluster_ids", InstanceRole.REDIS_SLAVE.value, "slave_ip"),
        )

        for ip, info in self.instance_ip_index.items():
            # 规则 2: 一 IP 一 pair 拓扑 (拓扑不一致时其他校验都不再可信, 优先报)
            if len(info["pair_partners"]) > 1:
                raise Exception(_("IP {} 存在多种主从配对 {}, 当前流程不支持此拓扑").format(ip, sorted(info["pair_partners"])))

            # 规则 1: 单 IP 目标版本一致
            if len(info["target_versions"]) > 1:
                raise Exception(
                    _("IP {} 上的集群 {} 目标版本不一致: {}。同一 IP 上所有集群必须升级到同一版本").format(
                        ip, sorted(info["cluster_ids"]), sorted(info["target_versions"])
                    )
                )

            # 规则 3: 单 IP 上兄弟集群必须全部在升级列表 (主/从两侧分别校验)
            for key, role, label in _roles:
                if not (exp := info[key]):
                    continue
                act = set(
                    StorageInstance.objects.filter(machine__ip=ip, instance_role=role).values_list(
                        "cluster__id", flat=True
                    )
                )
                if miss := act - exp:
                    raise Exception(_pair_scope_err.format(label, ip, sorted(miss)))

        # 一次遍历完成 pair 维度的规则 4/5 (顺序: scope 一致 → 版本合法 → 不降级 → finalize)
        for (master_ip, slave_ip), bucket in self.instance_pair_buckets.items():
            # 规则 4: pair 内 upgrade scope 一致
            if len(bucket["upgrade_master_flags"]) > 1:
                raise Exception(
                    _("IP对 {}/{} 上的集群 {} 升级范围不一致(是否升级 master 冲突), 请统一").format(
                        master_ip, slave_ip, sorted(bucket["cluster_ids"])
                    )
                )

            # 规则 5: version-validity / downgrade / slave-upgraded-too 校验 (每 pair 执行一次)
            # 经过前面校验, 此处 target_versions 与 upgrade_master_flags 均已 size=1
            target_version = next(iter(bucket["target_versions"]))
            upgrade_master = next(iter(bucket["upgrade_master_flags"]))
            any_cluster_id = bucket["cluster_ids"][0]
            any_cluster = self.instance_cluster_meta[any_cluster_id]["cluster"]
            valid_versions = get_storage_version_names_by_cluster_type(any_cluster.cluster_type, True)
            if target_version not in valid_versions:
                raise Exception(
                    _("Redis集群 {} 目标版本 {} 不合法, 合法版本: {}").format(
                        any_cluster.immute_domain, target_version, valid_versions
                    )
                )

            # 不支持降级: 只需分别检查一次 master_ip / slave_ip (同 IP 上版本一致)
            ips_to_check = [slave_ip] + ([master_ip] if upgrade_master else [])
            for ip in ips_to_check:
                cur_ver = get_redis_version_by_ip(any_cluster_id, ip)
                if version_gt(cur_ver, target_version):
                    raise Exception(
                        _("IP对 {}/{} 上 IP {} 当前版本 {} > 目标版本 {}, 不支持降级").format(
                            master_ip, slave_ip, ip, cur_ver, target_version
                        )
                    )

            # finalize bucket: 收敛到单值便于下游消费
            bucket["target_version"] = target_version
            bucket["upgrade_master"] = upgrade_master
            bucket.pop("target_versions", None)
            bucket.pop("upgrade_master_flags", None)

    @staticmethod
    def get_cluster_ids_from_info_item(info_item: Dict) -> List[int]:
        # 兼容传入cluster_id 和 cluster_ids 两种方式
        cluster_ids = []
        if "cluster_ids" in info_item and info_item["cluster_ids"]:
            cluster_ids = info_item["cluster_ids"]
        else:
            cluster_ids.append(info_item["cluster_id"])
        return cluster_ids

    def version_update_flow(self):
        """
        Redis集群在线版本升级流程
        ========================

        升级包含 Proxy升级 和 Backend升级

        Proxy升级流程
        --------------
        - 遍历任务列表 `self.cluster_versions_ips["Proxy"]` 并行执行Proxy升级原子任务

        Backend升级流程
        ----------------
        1. Backend升级涉及多种架构
           ┌─ RedisCluster 集群架构
           │  ├─ Twemproxy 架构
           │  └─ Predixy 架构
           └─ TendisRedisInstance 主从架构

        2. 升级步骤
           - 对于 RedisCluster 架构：
             1. 先升级所有指定的 Slave 节点
             2. 对指定的 Master (如果有) 实例发起主从切换或 Failover 操作
             3. 升级指定的 Master 节点

           - 对于 TendisRedisInstance 架构：
             1. 类似 Twemproxy，但一个 cluster_id 只涉及一个 Master 和一个 Slave
             2. 仅升级 Slave：无需切换操作
             3. 同时升级 Master 和 Slave：
                - 先升级 Slave 节点
                - 执行切换操作
                - 升级 Master 节点
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)

        # 先升级 proxy
        proxy_to_upgrade = self.cluster_versions_ips.get("Proxy")
        if proxy_to_upgrade:
            proxy_pipelines = []
            for cluster_id, target_pairs in proxy_to_upgrade.items():
                proxy_process = self._create_proxy_upgrade_sub_flow(cluster_id, target_pairs)
                proxy_pipelines.append(proxy_process)
            if proxy_pipelines:
                redis_pipeline.add_parallel_sub_pipeline(proxy_pipelines)

        # 再升级 storage
        storage_pipelines = []
        # 非 TendisRedisInstance 的 Backend: 保留原始按 cluster_id 派发
        storage_to_upgrade = self.cluster_versions_ips.get("Backend")
        if storage_to_upgrade:
            for cluster_id, target_pairs in storage_to_upgrade.items():
                storage_process = self._create_storage_upgrade_sub_flow(cluster_id, target_pairs)
                storage_pipelines.append(storage_process)
        # TendisRedisInstance: 按 (master_ip, slave_ip) 派发, 每个 pair 一条 sub_flow
        for pair_key, bucket in self.instance_pair_buckets.items():
            storage_pipelines.append(self._create_instance_pair_upgrade_sub_flow(pair_key, bucket))
        if storage_pipelines:
            redis_pipeline.add_parallel_sub_pipeline(storage_pipelines)

        redis_pipeline.run_pipeline()

    def _create_proxy_upgrade_sub_flow(self, cluster_id, version_pairs: dict):
        """创建代理升级子流水线"""
        version_pipelines = []
        cluster_meta_data = get_cluster_info_by_cluster_id(cluster_id)
        act_kwargs = self._make_act_kwargs()

        for version, ips in version_pairs.items():
            sub_process = ClusterProxysUpgradeAtomJob(
                self.root_id,
                self.data,
                act_kwargs,
                {
                    "cluster_domain": cluster_meta_data["immute_domain"],
                    "target_ips": ips,
                    "target_version": version,
                },
            )
            version_pipelines.append(sub_process)

        cluster_process_builder = SubBuilder(root_id=self.root_id, data=self.data)
        if version_pipelines:
            cluster_process_builder.add_parallel_sub_pipeline(sub_flow_list=version_pipelines)
            self._add_data_update_tail_sub_pipeline(
                cluster_process_builder,
                parallel_acts=[
                    self._build_freshing_version_act(cluster_meta_data, self.MetaUpdateOption.UPDATE_PROXY)
                ],
                sub_name=_("Proxy数据更新收尾"),
            )
        return cluster_process_builder.build_sub_process(_("集群{}-Proxy升级").format(cluster_meta_data["cluster_name"]))

    def _create_storage_upgrade_sub_flow(self, cluster_id, version_pairs: dict):
        """创建存储升级子流水线(非 TendisRedisInstance 架构)"""
        act_kwargs = self._make_act_kwargs()
        # 加个缓存
        if not self.cluster_cache.get(cluster_id):
            self.cluster_cache[cluster_id] = get_cluster_info_by_cluster_id(cluster_id)
        cluster_meta_data = self.cluster_cache[cluster_id]
        act_kwargs.bk_cloud_id = cluster_meta_data["bk_cloud_id"]
        act_kwargs.cluster.update(cluster_meta_data)

        # TendisRedisInstance 走 _create_instance_pair_upgrade_sub_flow, 不会走到这里
        if cluster_meta_data["cluster_type"] == ClusterType.TendisRedisInstance:
            raise Exception(
                _("TendisRedisInstance 集群 {} 应通过 instance_pair_buckets 派发").format(cluster_meta_data["immute_domain"])
            )

        trans_files = GetFileList(db_type=DBType.Redis)

        version_pipelines = []
        target_major_versions = []
        cc_update_acts = []
        role_meta_acts = []
        dbmon_reinstall_ips = set()
        for target_version, ips in version_pairs.items():
            target_major_version = get_major_version_by_version_name(target_version)
            target_major_versions.append(target_major_version)
            target_process, target_cc_update_acts, target_role_meta_acts = self._create_redis_cluster_upgrade_flow(
                act_kwargs, cluster_meta_data, target_major_version, ips, trans_files
            )
            version_pipelines.append(target_process)
            cc_update_acts.extend(target_cc_update_acts)
            role_meta_acts.extend(target_role_meta_acts)
            dbmon_reinstall_ips.update(ips)

        sub_builder = SubBuilder(root_id=self.root_id, data=self.data)
        self._add_built_act(sub_builder, self._build_payload_init_act(cluster_meta_data))
        sub_builder.add_parallel_sub_pipeline(sub_flow_list=version_pipelines)
        newest_version = self._get_newest_version(cluster_meta_data["major_version"], target_major_versions)
        version_update_acts = [
            self._build_cluster_major_version_act(cluster_meta_data, [cluster_id], newest_version),
            self._build_freshing_version_act(cluster_meta_data, self.MetaUpdateOption.UPDATE_STORAGE),
            *self._build_dbconfig_version_acts([cluster_meta_data], newest_version),
        ]
        self._add_backend_data_update_tail_sub_pipeline(
            sub_builder,
            cc_update_acts=cc_update_acts,
            role_meta_acts=role_meta_acts,
            version_update_acts=version_update_acts,
        )
        self._add_dbmon_reinstall_sub_pipeline(sub_builder, act_kwargs, cluster_meta_data, dbmon_reinstall_ips)

        return sub_builder.build_sub_process(sub_name=_("集群{}-Backend升级".format(cluster_meta_data["cluster_name"])))

    def _create_instance_pair_upgrade_sub_flow(self, pair_key: Tuple[str, str], bucket: Dict) -> SubBuilder:
        """
        TendisRedisInstance: 以 (master_ip, slave_ip) 为单位派发一条升级 sub_flow.
        """
        master_ip, slave_ip = pair_key
        cluster_ids: List[int] = list(bucket["cluster_ids"])
        target_version: str = bucket["target_version"]
        upgrade_master: bool = bucket["upgrade_master"]
        target_major_version = get_major_version_by_version_name(target_version)

        act_kwargs = self._make_act_kwargs()
        # 用桶内第一个 cluster 的 meta 填充通用字段 (bk_cloud_id 等跨兄弟集群一致)
        anchor_cluster_id = cluster_ids[0]
        if not self.cluster_cache.get(anchor_cluster_id):
            self.cluster_cache[anchor_cluster_id] = get_cluster_info_by_cluster_id(anchor_cluster_id)
        anchor_meta = self.cluster_cache[anchor_cluster_id]
        act_kwargs.bk_cloud_id = anchor_meta["bk_cloud_id"]

        sub_builder = self.redisinstance_version_update_sub_flow(
            sub_kwargs=act_kwargs,
            cluster_ids=cluster_ids,
            master_ip=master_ip,
            slave_ip=slave_ip,
            target_major_version=target_major_version,
            upgrade_master=upgrade_master,
        )
        return sub_builder

    def _create_redis_cluster_upgrade_flow(
        self, act_kwargs, cluster_meta_data, target_major_version, ips, trans_files
    ):
        """创建Redis集群升级流水线"""
        ctx = _ClusterUpgradeCtx(
            pipeline=SubBuilder(root_id=self.root_id, data=self.data),
            act_kwargs=act_kwargs,
            cluster_meta_data=cluster_meta_data,
            ips=ips,
            target_major_version=target_major_version,
            trans_files=trans_files,
        )

        # 下发介质包
        self._add_media_transfer_act(ctx)
        # 卸载 dbmon
        self._add_dbmon_uninstall_act(ctx)
        # 升级 Slave 节点
        self._add_slave_upgrade_acts(ctx)
        # 获取需要切换的主从对 (并写回 ctx, 后续 handler 复用)
        ctx.pairs_to_switch = self._get_pairs_to_switch(ctx)

        # 处理不同类型的集群升级
        cluster_type = cluster_meta_data["cluster_type"]
        if is_redis_cluster_protocal(cluster_type) and ctx.pairs_to_switch:
            self._handle_redis_cluster_upgrade(ctx)
        elif is_twemproxy_proxy_type(cluster_type) and ctx.pairs_to_switch:
            self._handle_twemproxy_cluster_upgrade(ctx)

        cc_update_acts, role_meta_acts = [], []
        # 构造元数据更新节点，由外层 Backend 数据更新收尾统一挂载到 dbmon 重装前
        if ctx.pairs_to_switch:
            cc_update_acts, role_meta_acts = self._build_metadata_update_acts(ctx)

        return (
            ctx.pipeline.build_sub_process(sub_name=_("目标版本-{}".format(target_major_version))),
            cc_update_acts,
            role_meta_acts,
        )

    def _add_media_transfer_act(self, ctx: _ClusterUpgradeCtx):
        """添加目标 IP 下发介质包的动作."""
        ctx.act_kwargs.exec_ip = list(ctx.ips)
        ctx.act_kwargs.file_list = ctx.trans_files.redis_cluster_version_update(ctx.target_major_version)
        ctx.pipeline.add_act(
            act_name=_("目标IP 下发介质包"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(ctx.act_kwargs),
        )

    def _add_dbmon_uninstall_act(self, ctx: _ClusterUpgradeCtx):
        """添加卸载dbmon的动作"""
        ctx.act_kwargs.cluster = {}
        sub_builder = ClusterIPsDbmonInstallAtomJob(
            self.root_id,
            self.data,
            ctx.act_kwargs,
            {
                "cluster_domain": ctx.cluster_meta_data["immute_domain"],
                "ips": list(ctx.ips),
                "is_stop": True,
            },
        )
        ctx.pipeline.add_sub_pipeline(sub_builder)

    def _add_slave_upgrade_acts(self, ctx: _ClusterUpgradeCtx):
        """添加Slave升级动作"""
        ctx.act_kwargs.cluster = {}
        acts_list = []
        for ip, ports in ctx.cluster_meta_data["slave_ports"].items():
            # 跳过没有指定的 Slave
            if ip not in ctx.ips:
                continue
            ctx.act_kwargs.exec_ip = ip
            ctx.act_kwargs.cluster["ip"] = ip
            ctx.act_kwargs.cluster["ports"] = ports
            ctx.act_kwargs.cluster["password"] = ctx.cluster_meta_data["redis_password"]
            ctx.act_kwargs.cluster["db_version"] = ctx.target_major_version
            ctx.act_kwargs.cluster["role"] = InstanceRole.REDIS_SLAVE.value
            ctx.act_kwargs.cluster["cluster_type"] = ctx.cluster_meta_data["cluster_type"]
            ctx.act_kwargs.get_redis_payload_func = (
                RedisActPayload.redis_cluster_version_update_online_payload.__name__
            )
            acts_list.append(
                {
                    "act_name": _("old_slave:{} 版本升级").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(ctx.act_kwargs),
                }
            )
        if acts_list:
            ctx.pipeline.add_parallel_acts(acts_list=acts_list)
        else:
            ctx.pipeline.add_act(act_name=_("无Slave需随Master升级"), act_component_code=EmptyNodeComponent.code, kwargs={})

    def _get_pairs_to_switch(self, ctx: _ClusterUpgradeCtx) -> List:
        """获取需要切换的主从对"""
        return [pair for pair in ctx.cluster_meta_data["master_slave_ins_pairs"] if pair["master"]["ip"] in ctx.ips]

    def _handle_redis_cluster_upgrade(self, ctx: _ClusterUpgradeCtx):
        """处理Redis Cluster类型的升级"""
        # 切换
        ctx.act_kwargs.exec_ip = ctx.first_master_ip
        ctx.act_kwargs.cluster = {
            "redis_password": ctx.cluster_meta_data["redis_password"],
            "redis_master_slave_pairs": ctx.pairs_to_switch,
            "force": False,
        }
        ctx.act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_failover.__name__
        ctx.pipeline.add_act(
            act_name=_("{} 集群:{}执行 cluster failover").format(
                ctx.first_master_ip, ctx.cluster_meta_data["cluster_name"]
            ),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(ctx.act_kwargs),
        )
        # 升级
        ctx.act_kwargs.cluster = {}
        acts_list = []
        for ip, ports in ctx.cluster_meta_data["master_ports"].items():
            if ip not in ctx.ips:
                continue
            ctx.act_kwargs.exec_ip = ip
            ctx.act_kwargs.cluster["ip"] = ip
            ctx.act_kwargs.cluster["ports"] = ports
            ctx.act_kwargs.cluster["password"] = ctx.cluster_meta_data["redis_password"]
            ctx.act_kwargs.cluster["db_version"] = ctx.target_major_version
            ctx.act_kwargs.cluster["role"] = InstanceRole.REDIS_SLAVE.value
            ctx.act_kwargs.cluster["cluster_type"] = ctx.cluster_meta_data["cluster_type"]
            ctx.act_kwargs.get_redis_payload_func = (
                RedisActPayload.redis_cluster_version_update_online_payload.__name__
            )
            acts_list.append(
                {
                    "act_name": _("new slave:{} 版本升级").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(ctx.act_kwargs),
                }
            )
        ctx.pipeline.add_parallel_acts(acts_list=acts_list)

    def _handle_twemproxy_cluster_upgrade(self, ctx: _ClusterUpgradeCtx):
        """处理Twemproxy类型的集群升级"""
        # 主从切换
        self._add_twemproxy_switch_acts(ctx)
        # 清理slaveof配置
        self._add_slaveof_cleanup_acts(ctx)
        # 升级old_master
        self._add_old_master_upgrade_acts(ctx)
        # old_master做new_slave
        self._add_master_to_slave_sync_acts(ctx)

    def _add_twemproxy_switch_acts(self, ctx: _ClusterUpgradeCtx):
        """添加Twemproxy主从切换动作"""
        first_master_ip = ctx.first_master_ip
        ctx.act_kwargs.exec_ip = first_master_ip
        ctx.act_kwargs.cluster = {}
        ctx.act_kwargs.cluster["cluster_id"] = ctx.cluster_id
        ctx.act_kwargs.cluster["immute_domain"] = ctx.cluster_meta_data["immute_domain"]
        ctx.act_kwargs.cluster["cluster_type"] = ctx.cluster_meta_data["cluster_type"]
        ctx.act_kwargs.cluster["switch_condition"] = {
            "is_check_sync": True,  # 不强制切换
            "slave_master_diff_time": DEFAULT_MASTER_DIFF_TIME,
            "last_io_second_ago": DEFAULT_LAST_IO_SECOND_AGO,
            "can_write_before_switch": True,
            "sync_type": SyncType.SYNC_MS.value,
        }

        # 切换前的检查
        ctx.act_kwargs.cluster["switch_info"] = ctx.pairs_to_switch
        ctx.act_kwargs.get_redis_payload_func = RedisActPayload.redis__switch_precheck_4_scene.__name__
        ctx.pipeline.add_act(
            act_name=_("切换检查-{}-{}").format(ctx.cluster_meta_data["immute_domain"], first_master_ip),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(ctx.act_kwargs),
        )
        # 先将 old_slave 切换成 new_master
        ctx.act_kwargs.cluster["switch_info"] = ctx.pairs_to_switch
        ctx.act_kwargs.get_redis_payload_func = RedisActPayload.redis__switch_4_scene.__name__
        ctx.pipeline.add_act(
            act_name=_("集群:{} 主从切换").format(ctx.cluster_meta_data["cluster_name"]),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(ctx.act_kwargs),
        )

        ctx.act_kwargs.cluster["instances"] = nosqlcomm.other.get_cluster_proxies(
            cluster_id=ctx.act_kwargs.cluster["cluster_id"]
        )
        ctx.act_kwargs.get_redis_payload_func = RedisActPayload.redis_twemproxy_backends_4_scene.__name__
        ctx.pipeline.add_act(
            act_name=_("{}-检查切换状态").format(first_master_ip),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(ctx.act_kwargs),
        )

    def _add_slaveof_cleanup_acts(self, ctx: _ClusterUpgradeCtx):
        """添加清理slaveof配置的动作"""
        acts_list = []
        ctx.act_kwargs.cluster = {}
        for master_ip, master_ports in ctx.cluster_meta_data["master_ports"].items():
            if master_ip not in ctx.ips:
                continue
            slave_ip = ctx.cluster_meta_data["master_ip_to_slave_ip"][master_ip]
            slave_ports = ctx.cluster_meta_data["slave_ports"][slave_ip]

            ctx.act_kwargs.exec_ip = master_ip
            ctx.act_kwargs.write_op = WriteContextOpType.APPEND.value
            ports_str = "\n".join(str(port) for port in master_ports)
            ctx.act_kwargs.cluster["shell_command"] = REDIS_CONF_DEL_SLAVEOF.format(ports_str)
            acts_list.append(
                {
                    "act_name": _("old_master:{} 删除slaveof配置").format(master_ip),
                    "act_component_code": ExecuteShellScriptComponent.code,
                    "kwargs": asdict(ctx.act_kwargs),
                }
            )

            ctx.act_kwargs.exec_ip = slave_ip
            ctx.act_kwargs.write_op = WriteContextOpType.APPEND.value
            ports_str = "\n".join(str(port) for port in slave_ports)
            ctx.act_kwargs.cluster["shell_command"] = REDIS_CONF_DEL_SLAVEOF.format(ports_str)
            acts_list.append(
                {
                    "act_name": _("old_slave:{} 删除slaveof配置").format(slave_ip),
                    "act_component_code": ExecuteShellScriptComponent.code,
                    "kwargs": asdict(ctx.act_kwargs),
                }
            )
        ctx.pipeline.add_parallel_acts(acts_list=acts_list)

    def _add_old_master_upgrade_acts(self, ctx: _ClusterUpgradeCtx):
        """添加old_master升级动作"""
        ctx.act_kwargs.cluster = {}
        ctx.act_kwargs.write_op = None
        acts_list = []
        for ip, ports in ctx.cluster_meta_data["master_ports"].items():
            if ip not in ctx.ips:
                continue
            ctx.act_kwargs.exec_ip = ip
            ctx.act_kwargs.cluster["ip"] = ip
            ctx.act_kwargs.cluster["ports"] = ports
            ctx.act_kwargs.cluster["password"] = ctx.cluster_meta_data["redis_password"]
            ctx.act_kwargs.cluster["db_version"] = ctx.target_major_version
            # role 取当前运行态而非 act_name 暗示的目标态: 此时进程仍以 master 运行,
            # 降级到 slave 在后续 _add_master_to_slave_sync_acts 才发生, actuator 的 isAllInstanceMaster 据此校验.
            ctx.act_kwargs.cluster["role"] = InstanceRole.REDIS_MASTER.value
            cluster_type = ctx.cluster_meta_data["cluster_type"]
            ctx.act_kwargs.cluster["cluster_type"] = cluster_type
            # 仅 TwemproxyRedisInstance / RedisInstance / TwemproxyTendisSSDInstance 三种支持
            ctx.act_kwargs.cluster["flush_after_upgrade"] = (
                cluster_type in _FLUSH_AFTER_UPGRADE_SUPPORTED_CLUSTER_TYPES
            )
            ctx.act_kwargs.get_redis_payload_func = (
                RedisActPayload.redis_cluster_version_update_online_payload.__name__
            )
            acts_list.append(
                {
                    "act_name": _("new slave:{} 版本升级").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(ctx.act_kwargs),
                }
            )
        ctx.pipeline.add_parallel_acts(acts_list=acts_list)

    def _add_master_to_slave_sync_acts(self, ctx: _ClusterUpgradeCtx):
        """添加old_master做new_slave的同步动作"""
        bk_biz_id = ctx.cluster_meta_data["bk_biz_id"]
        cluster_id = ctx.cluster_id
        twemproxy_server_shards = get_twemproxy_cluster_server_shards(bk_biz_id, cluster_id, {})
        child_pipelines = []
        ctx.act_kwargs.cluster = {}
        ctx.act_kwargs.cluster["bk_biz_id"] = bk_biz_id
        ctx.act_kwargs.cluster["bk_cloud_id"] = ctx.cluster_meta_data["bk_cloud_id"]
        ctx.act_kwargs.cluster["immute_domain"] = ctx.cluster_meta_data["immute_domain"]
        ctx.act_kwargs.cluster["cluster_type"] = ctx.cluster_meta_data["cluster_type"]
        ctx.act_kwargs.cluster["cluster_name"] = ctx.cluster_meta_data["cluster_name"]
        masterip_to_slaveip = ctx.cluster_meta_data["master_ip_to_slave_ip"]
        for master_ip, ports in ctx.cluster_meta_data["master_ports"].items():
            if master_ip not in ctx.ips:
                continue
            master_ports = ctx.cluster_meta_data["master_ports"][master_ip]
            slave_ip = masterip_to_slaveip[master_ip]
            slave_ports = ctx.cluster_meta_data["slave_ports"][slave_ip]
            sync_param = {
                "sync_type": SyncType.SYNC_MS,
                "origin_1": slave_ip,
                "sync_dst1": master_ip,
                "ins_link": [],
                "server_shards": twemproxy_server_shards.get(slave_ip, {}),
                "cache_backup_mode": get_cache_backup_mode(bk_biz_id, cluster_id),
            }
            for idx, port in enumerate(master_ports):
                sync_param["ins_link"].append(
                    {
                        "origin_1": str(slave_ports[idx]),
                        "sync_dst1": str(port),
                    }
                )
            sync_builder = RedisMakeSyncAtomJob(
                root_id=self.root_id, ticket_data=self.data, sub_kwargs=ctx.act_kwargs, params=sync_param
            )
            child_pipelines.append(sync_builder)
        ctx.pipeline.add_parallel_sub_pipeline(child_pipelines)

    def _build_metadata_update_acts(self, ctx: _ClusterUpgradeCtx) -> Tuple[List[Dict], List[Dict]]:
        """构造切换后、dbmon 重装前必须完成的 CC 和主从元数据更新动作."""
        # 修改元数据指向(old_masters和proxy关系断开,new_master增加和proxy关系)
        # 更新 cluster.nosqlstoragesetdtl_set
        # new_masters 设置 instance_role 为 InstanceRole.REDIS_MASTER.value
        # 最后娜动CC模块
        cluster_meta_data = ctx.cluster_meta_data
        bk_biz_id = cluster_meta_data["bk_biz_id"]
        ctx.act_kwargs.cluster = {}
        ctx.act_kwargs.cluster["bk_biz_id"] = bk_biz_id
        ctx.act_kwargs.cluster["bk_cloud_id"] = cluster_meta_data["bk_cloud_id"]
        ctx.act_kwargs.cluster["immute_domain"] = cluster_meta_data["immute_domain"]
        ctx.act_kwargs.cluster["cluster_type"] = cluster_meta_data["cluster_type"]
        ctx.act_kwargs.cluster["cluster_name"] = cluster_meta_data["cluster_name"]
        ctx.act_kwargs.cluster["cluster_id"] = ctx.cluster_id
        ctx.act_kwargs.cluster["switch_condition"] = {
            "is_check_sync": True,  # 不强制切换
            "slave_master_diff_time": DEFAULT_MASTER_DIFF_TIME,
            "last_io_second_ago": DEFAULT_LAST_IO_SECOND_AGO,
            "can_write_before_switch": True,
            "sync_type": SyncType.SYNC_MS.value,
        }
        ctx.act_kwargs.cluster["sync_relation"] = []
        masterip_to_slaveip = cluster_meta_data["master_ip_to_slave_ip"]
        for master_ip, ports in cluster_meta_data["master_ports"].items():
            # Master 没升级的情况下没有发生切换，跳过
            if master_ip not in ctx.ips:
                continue
            master_ports = cluster_meta_data["master_ports"][master_ip]
            slave_ip = masterip_to_slaveip[master_ip]
            slave_ports = cluster_meta_data["slave_ports"][slave_ip]
            for idx, port in enumerate(master_ports):
                ctx.act_kwargs.cluster["sync_relation"].append(
                    {
                        "ejector": {
                            "ip": master_ip,
                            "port": int(port),
                        },
                        "receiver": {
                            "ip": slave_ip,
                            "port": int(slave_ports[idx]),
                        },
                    }
                )
        ctx.act_kwargs.cluster["meta_func_name"] = RedisDBMeta.tendis_switch_4_scene.__name__
        cc_update_act = {
            "act_name": _("CC信息更新"),
            "act_component_code": RedisDBMetaComponent.code,
            "kwargs": asdict(ctx.act_kwargs),
        }
        # 主从元数据交换,StorageInstanceTuple中,master变slave,slave变master
        acts_list = []
        for master_ip, master_ports in cluster_meta_data["master_ports"].items():
            # Master 没有升级的情况下没有切换发生，跳过
            if master_ip not in ctx.ips:
                continue
            ctx.act_kwargs.cluster["meta_update_ip"] = master_ip
            slave_ip = masterip_to_slaveip[master_ip]
            ctx.act_kwargs.cluster["meta_update_ports"] = master_ports
            ctx.act_kwargs.cluster["meta_update_status"] = InstanceStatus.RUNNING.value
            ctx.act_kwargs.cluster["meta_func_name"] = RedisDBMeta.instances_failover_4_scene.__name__
            acts_list.append(
                {
                    "act_name": _("old_master({})-old_slave({})-刷新集群元数据的主从信息".format(master_ip, slave_ip)),
                    "act_component_code": RedisDBMetaComponent.code,
                    "kwargs": asdict(ctx.act_kwargs),
                }
            )
        return [cc_update_act], acts_list

    def _add_dbmon_reinstall_sub_pipeline(
        self, pipeline, act_kwargs: ActKwargs, cluster_meta_data: Dict, ips: Set[str]
    ):
        """为指定 IP 重装 dbmon; dbmon payload 会在执行时按最新元数据动态生成."""
        act_kwargs.cluster = {}
        sub_builder = ClusterIPsDbmonInstallAtomJob(
            self.root_id,
            self.data,
            act_kwargs,
            {
                "cluster_domain": cluster_meta_data["immute_domain"],
                "ips": sorted(ips),
                "is_stop": False,
            },
        )
        pipeline.add_sub_pipeline(sub_builder)

    def redisinstance_version_update_sub_flow(
        self,
        sub_kwargs: ActKwargs,
        cluster_ids: List[int],
        master_ip: str,
        slave_ip: str,
        target_major_version: str,
        upgrade_master: bool,
    ) -> SubBuilder:
        """
        TendisRedisInstance (主从版) 升级 sub_flow, 输入由 (master_ip, slave_ip) pair 与
        用户请求的 cluster_ids 决定, 不再通过 get_cluster_info_by_ip 向兄弟集群"漏散".
        @param cluster_ids 经 precheck 校验的、pair 上所有待升级集群 id (含 sibling)
        @param master_ip / slave_ip pair 的物理 IP
        @param target_major_version 目标主版本 (如 'Redis-6')
        @param upgrade_master True: master/slave 都升级并切换; False: 仅升级 slave
        """
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
        act_kwargs = deepcopy(sub_kwargs)
        act_kwargs.cluster = {}

        # 1) 解析每个 cluster_id 的 meta, 同时聚合 master_ip/slave_ip 上的端口
        per_cluster_meta: Dict[int, Dict] = {}
        master_ports_union: List[int] = []
        slave_ports_union: List[int] = []
        for cid in cluster_ids:
            cm = self.cluster_cache.get(cid)
            if cm is None:
                cm = get_cluster_info_by_cluster_id(cid)
                self.cluster_cache[cid] = cm
            per_cluster_meta[cid] = cm
            # 预期每个 cluster 的 master/slave 恰好落在 pair 的两个 IP 上
            if master_ip not in cm["master_ports"] or slave_ip not in cm["slave_ports"]:
                raise Exception(
                    _("集群 {} 的主从拓扑 {} 与 pair ({}/{}) 不一致").format(
                        cm["immute_domain"], cm.get("master_ip_to_slave_ip"), master_ip, slave_ip
                    )
                )
            master_ports_union.extend(cm["master_ports"][master_ip])
            slave_ports_union.extend(cm["slave_ports"][slave_ip])

        # 2) defense-in-depth: pair 的 union 端口必须等于 master_ip/slave_ip 上实际存在的端口集合,
        #    否则说明 precheck 漏掉了 sibling, 必须在任何 act 执行前直接失败.
        #    与 precheck 规则 3 刻意重叠 (一个走 cluster 维度, 一个走 ports 维度).
        host_master_info = get_cluster_info_by_ip(master_ip)
        host_slave_info = get_cluster_info_by_ip(slave_ip)
        if set(host_master_info["ports"]) != set(master_ports_union):
            raise Exception(
                _("master_ip {} 上实际端口 {} 与请求升级端口集合 {} 不一致, " "可能存在未加入升级的兄弟集群, 请检查 precheck").format(
                    master_ip, sorted(host_master_info["ports"]), sorted(master_ports_union)
                )
            )
        if set(host_slave_info["ports"]) != set(slave_ports_union):
            raise Exception(
                _("slave_ip {} 上实际端口 {} 与请求升级端口集合 {} 不一致, " "可能存在未加入升级的兄弟集群, 请检查 precheck").format(
                    slave_ip, sorted(host_slave_info["ports"]), sorted(slave_ports_union)
                )
            )

        # 3) 初始化配置 (用 anchor cluster 填充 act_kwargs.cluster 即可)
        anchor_cid = cluster_ids[0]
        anchor_meta = per_cluster_meta[anchor_cid]
        act_kwargs.bk_cloud_id = anchor_meta["bk_cloud_id"]
        act_kwargs.cluster.update(anchor_meta)
        sub_pipeline.add_act(
            act_name=_("初始化配置"),
            act_component_code=GetRedisActPayloadComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 4) 介质下发: 只升级 slave 时不需要下发到 master_ip
        all_ips = [master_ip, slave_ip] if upgrade_master else [slave_ip]
        act_kwargs.exec_ip = all_ips
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs.file_list = trans_files.redis_cluster_version_update(target_major_version)
        sub_pipeline.add_act(
            act_name=_("主从IP 下发介质包"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 5) 关闭 bkdbmon (每台主机一次, 不按 cluster 维度并发重复)
        stop_dbmon_acts = []
        for ip in all_ips:
            act_kwargs.exec_ip = ip
            act_kwargs.cluster = {"ip": ip, "is_stop": True}
            act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install_list_new.__name__
            stop_dbmon_acts.append(
                {
                    "act_name": _("{}-暂停bkdbmon").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=stop_dbmon_acts)

        # 6) 升级 slave (host 级别一次完成所有端口)
        act_kwargs.cluster = {}
        act_kwargs.exec_ip = slave_ip
        act_kwargs.cluster["ip"] = slave_ip
        act_kwargs.cluster["ports"] = slave_ports_union
        act_kwargs.cluster["db_version"] = target_major_version
        act_kwargs.cluster["role"] = InstanceRole.REDIS_SLAVE.value
        act_kwargs.cluster["cluster_type"] = anchor_meta["cluster_type"]
        act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_version_update_online_payload.__name__
        sub_pipeline.add_act(
            act_name=_("old_slave:{} 版本升级至 {}").format(slave_ip, target_major_version),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 7) 仅升级 slave 时, 后续的切换/元数据翻转全部跳过; 直接重启 dbmon 结束
        if upgrade_master:
            ctx = _InstancePairUpgradeCtx(
                sub_pipeline=sub_pipeline,
                act_kwargs=act_kwargs,
                cluster_ids=cluster_ids,
                per_cluster_meta=per_cluster_meta,
                master_ip=master_ip,
                slave_ip=slave_ip,
                master_ports_union=master_ports_union,
                slave_ports_union=slave_ports_union,
                target_major_version=target_major_version,
                upgrade_master=upgrade_master,
            )
            self._add_instance_switch_and_master_upgrade(ctx)
        else:
            self._add_data_update_tail_sub_pipeline(
                sub_pipeline,
                parallel_acts=[
                    self._build_freshing_version_act(per_cluster_meta[cid], self.MetaUpdateOption.UPDATE_STORAGE)
                    for cid in cluster_ids
                ],
                sub_name=_("数据更新收尾"),
            )

        # 8) 重装 dbmon (每台主机一次)
        restart_dbmon_acts = []
        for ip in all_ips:
            act_kwargs.exec_ip = ip
            act_kwargs.cluster = {"ip": ip, "is_stop": False}
            act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install_list_new.__name__
            restart_dbmon_acts.append(
                {
                    "act_name": _("{}-重装bkdbmon").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=restart_dbmon_acts)

        return sub_pipeline.build_sub_process(
            sub_name=_("主从pair {}/{} 目标版本-{}").format(master_ip, slave_ip, target_major_version)
        )

    def _add_instance_switch_and_master_upgrade(self, ctx: _InstancePairUpgradeCtx):
        """
        TendisRedisInstance 升级流程中 "升级 master + 主从切换 + 元数据/同步/版本收尾" 部分.
        阶段顺序刻意先做 precheck 再做 switch, 以将 "点 of no return" 前的所有可预见错误暴露出来,
        减少 half-switched 状态; 每个 per-cluster 并发 act 都带上 cluster_id + immute_domain 便于定位失败集群.
        """
        sub_pipeline = ctx.sub_pipeline
        act_kwargs = ctx.act_kwargs
        cluster_ids = ctx.cluster_ids
        per_cluster_meta = ctx.per_cluster_meta
        master_ip = ctx.master_ip
        slave_ip = ctx.slave_ip
        master_ports_union = ctx.master_ports_union
        slave_ports_union = ctx.slave_ports_union
        target_major_version = ctx.target_major_version

        # 7.1) slave 上执行 config set, 准备承担写角色
        act_kwargs.cluster = {}
        act_kwargs.exec_ip = slave_ip
        act_kwargs.cluster["ip"] = slave_ip
        act_kwargs.cluster["ports"] = slave_ports_union
        act_kwargs.cluster["role"] = InstanceRole.REDIS_SLAVE.value
        act_kwargs.cluster["sync_to_config_file"] = True
        act_kwargs.cluster["config_set_map"] = {"slave-read-only": "no", "appendonly": "no"}
        act_kwargs.get_redis_payload_func = RedisActPayload.redis_config_set.__name__
        sub_pipeline.add_act(
            act_name=_("old_slave:{} slave-read-only设置为no").format(slave_ip),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 7.2) 人工确认 (切换前)
        sub_pipeline.add_act(act_name=_("人工确认(切换前)"), act_component_code=PauseComponent.code, kwargs={})

        # 7.3) 域名切换: 用 precheck 校验过的 cluster_ids, 不再从 IP 反查 sibling
        act_kwargs.cluster = {
            "cluster_ids": cluster_ids,
            "meta_func_name": RedisDBMeta.switch_dns_for_redis_instance_version_upgrade.__name__,
        }
        sub_pipeline.add_act(
            act_name=_("cluster:{} 域名指向修改").format(cluster_ids),
            act_component_code=RedisDBMetaComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 7.4) 切换前 precheck: 全部并发执行, 任一失败则立刻 abort, 点 of no return 之前
        base_switch_kwargs = deepcopy(act_kwargs)
        base_switch_kwargs.cluster = {
            "db_version": "",
            "immute_domain": "",
            "cluster_type": "",
            "switch_condition": {
                "switch_option": SwitchType.SWITCH_WITH_CONFIRM.value,
                "is_check_sync": True,
                "sync_type": SyncType.SYNC_MS.value,
                "slave_master_diff_time": DEFAULT_MASTER_DIFF_TIME,
                "last_io_second_ago": DEFAULT_LAST_IO_SECOND_AGO,
                "can_write_before_switch": True,
            },
            "switch_info": [],
        }
        precheck_acts = []
        base_switch_kwargs.get_redis_payload_func = RedisActPayload.redis__switch_precheck_4_scene.__name__
        for cid in cluster_ids:
            cm = per_cluster_meta[cid]
            precheck_args = deepcopy(base_switch_kwargs)
            precheck_args.cluster["cluster_id"] = cm["cluster_id"]
            precheck_args.cluster["db_version"] = cm["major_version"]
            precheck_args.cluster["immute_domain"] = cm["immute_domain"]
            precheck_args.cluster["cluster_type"] = cm["cluster_type"]
            precheck_args.cluster["switch_info"] = cm["master_slave_ins_pairs"]
            precheck_acts.append(
                {
                    "act_name": _("Slave-{}-提升前的切换检查").format(slave_ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(precheck_args),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=precheck_acts)

        # 7.5) 真正执行切换, 点 of no return; 每个 act_name 里携带 cluster_id + immute_domain 便于定位
        switch_acts = []
        base_switch_kwargs.get_redis_payload_func = RedisActPayload.redis__switch_4_scene.__name__
        for cid in cluster_ids:
            cm = per_cluster_meta[cid]
            switch_args = deepcopy(base_switch_kwargs)
            switch_args.cluster["cluster_id"] = cm["cluster_id"]
            switch_args.cluster["db_version"] = cm["major_version"]
            switch_args.cluster["immute_domain"] = cm["immute_domain"]
            switch_args.cluster["cluster_type"] = cm["cluster_type"]
            switch_args.cluster["switch_info"] = cm["master_slave_ins_pairs"]
            switch_acts.append(
                {
                    "act_name": _("Slave({})-提升为master").format(slave_ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(switch_args),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=switch_acts)

        # 7.6) 切换后再次人工确认: 让运维有机会检查集群状态 (新 master 可写 / client 流量切过去)
        sub_pipeline.add_act(act_name=_("人工确认(请验证流量已切到新master)"), act_component_code=PauseComponent.code, kwargs={})

        # 7.7) 升级 old master (此时已是 new_slave 角色)
        act_kwargs.cluster = {}
        act_kwargs.exec_ip = master_ip
        act_kwargs.cluster["ip"] = master_ip
        act_kwargs.cluster["ports"] = master_ports_union
        act_kwargs.cluster["db_version"] = target_major_version
        act_kwargs.cluster["role"] = InstanceRole.REDIS_MASTER.value
        act_kwargs.cluster["cluster_type"] = ctx.anchor_meta["cluster_type"]
        act_kwargs.cluster["flush_after_upgrade"] = (
            ctx.anchor_meta["cluster_type"] in _FLUSH_AFTER_UPGRADE_SUPPORTED_CLUSTER_TYPES
        )
        act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_version_update_online_payload.__name__
        sub_pipeline.add_act(
            act_name=_("new_slave({})-版本升级至 {}").format(master_ip, target_major_version),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 7.8) 重建同步: old_master -> new_master, 每个 cluster 一条 sync 子流程.
        # 同步参数显式传入, 不依赖主从角色元数据已翻转.
        sync_pipelines = []
        for cid in cluster_ids:
            cm = per_cluster_meta[cid]
            ports_on_master_ip = cm["master_ports"][master_ip]
            ports_on_slave_ip = cm["slave_ports"][slave_ip]
            sync_kwargs = deepcopy(act_kwargs)
            sync_kwargs.cluster = {
                "bk_biz_id": cm["bk_biz_id"],
                "bk_cloud_id": cm["bk_cloud_id"],
                "immute_domain": cm["immute_domain"],
                "cluster_name": cm["cluster_name"],
                "cluster_type": cm["cluster_type"],
            }
            sync_param = {
                "sync_type": SyncType.SYNC_MS,
                "origin_1": slave_ip,
                "sync_dst1": master_ip,
                "ins_link": [],
                "server_shards": {},
                "cache_backup_mode": get_cache_backup_mode(cm["bk_biz_id"], cm["cluster_id"]),
            }
            for idx, port in enumerate(ports_on_master_ip):
                sync_param["ins_link"].append(
                    {
                        "origin_1": str(ports_on_slave_ip[idx]),
                        "sync_dst1": str(port),
                    }
                )
            sync_pipelines.append(
                RedisMakeSyncAtomJob(
                    root_id=self.root_id, ticket_data=self.data, sub_kwargs=sync_kwargs, params=sync_param
                )
            )
        if sync_pipelines:
            sub_pipeline.add_parallel_sub_pipeline(sync_pipelines)

        # 7.9) 数据更新收尾: 先翻转主从元数据, 再并发刷新版本 / dbconfig / 实例版本.
        anchor_cm = ctx.anchor_meta
        newest_version = (
            target_major_version
            if version_ge(target_major_version, anchor_cm["major_version"])
            else anchor_cm["major_version"]
        )
        cluster_meta_list = [per_cluster_meta[cid] for cid in cluster_ids]
        self._add_data_update_tail_sub_pipeline(
            sub_pipeline,
            ordered_acts=[self._build_redis_instance_role_meta_act(cluster_ids)],
            parallel_acts=[
                self._build_cluster_major_version_act(anchor_cm, cluster_ids, newest_version),
                *self._build_dbconfig_version_acts(cluster_meta_list, newest_version),
                *[
                    self._build_freshing_version_act(meta, self.MetaUpdateOption.UPDATE_STORAGE)
                    for meta in cluster_meta_list
                ],
            ],
            sub_name=_("数据更新收尾"),
        )

    @staticmethod
    def _get_newest_version(current_version: str, target_versions: List[str]) -> str:
        """从当前版本和本次目标版本中取最大主版本."""
        newest_version = current_version
        for target_version in target_versions:
            if version_ge(target_version, newest_version):
                newest_version = target_version
        return newest_version

    @staticmethod
    def _add_built_act(pipeline, act: Dict):
        """将 _build_*_act 返回的 dict 挂到 pipeline 上."""
        pipeline.add_act(
            act_name=act["act_name"],
            act_component_code=act["act_component_code"],
            kwargs=act["kwargs"],
        )

    def _add_data_update_tail_sub_pipeline(
        self,
        pipeline,
        ordered_acts: Optional[List[Dict]] = None,
        parallel_acts: Optional[List[Dict]] = None,
        sub_name: str = None,
    ):
        """把数据更新节点收口到单个尾部子流程中, 同时保留必要的串行/并行关系."""
        ordered_acts = ordered_acts or []
        parallel_acts = parallel_acts or []
        if not ordered_acts and not parallel_acts:
            return

        tail_builder = SubBuilder(root_id=self.root_id, data=self.data)
        for act in ordered_acts:
            self._add_built_act(tail_builder, act)

        if len(parallel_acts) == 1:
            self._add_built_act(tail_builder, parallel_acts[0])
        elif len(parallel_acts) > 1:
            tail_builder.add_parallel_acts(acts_list=parallel_acts)

        pipeline.add_sub_pipeline(tail_builder.build_sub_process(sub_name or _("数据更新收尾")))

    def _add_backend_data_update_tail_sub_pipeline(
        self,
        pipeline,
        cc_update_acts: Optional[List[Dict]] = None,
        role_meta_acts: Optional[List[Dict]] = None,
        version_update_acts: Optional[List[Dict]] = None,
    ):
        """非 RedisInstance backend 的统一数据更新收尾, 严格放在 dbmon 重装前."""
        cc_update_acts = cc_update_acts or []
        role_meta_acts = role_meta_acts or []
        version_update_acts = version_update_acts or []
        if not cc_update_acts and not role_meta_acts and not version_update_acts:
            return

        tail_builder = SubBuilder(root_id=self.root_id, data=self.data)
        for act in cc_update_acts:
            self._add_built_act(tail_builder, act)

        if len(role_meta_acts) == 1:
            self._add_built_act(tail_builder, role_meta_acts[0])
        elif len(role_meta_acts) > 1:
            tail_builder.add_parallel_acts(acts_list=role_meta_acts)

        if len(version_update_acts) == 1:
            self._add_built_act(tail_builder, version_update_acts[0])
        elif len(version_update_acts) > 1:
            tail_builder.add_parallel_acts(acts_list=version_update_acts)

        pipeline.add_sub_pipeline(tail_builder.build_sub_process(_("Backend数据更新收尾")))

    def _build_payload_init_act(self, cluster_meta_data: Dict) -> Dict:
        """构造 payload 初始化节点, 供需要 RedisActPayload 的收尾组件使用."""
        act_kwargs = self._make_act_kwargs()
        act_kwargs.bk_cloud_id = cluster_meta_data["bk_cloud_id"]
        act_kwargs.cluster.update(cluster_meta_data)
        return {
            "act_name": _("初始化配置"),
            "act_component_code": GetRedisActPayloadComponent.code,
            "kwargs": asdict(act_kwargs),
        }

    def _build_cluster_major_version_act(
        self, cluster_meta_data: Dict, cluster_ids: List[int], db_version: str
    ) -> Dict:
        """构造集群 major_version 刷新 act."""
        act_kwargs = self._make_act_kwargs()
        act_kwargs.cluster = {
            "bk_biz_id": cluster_meta_data["bk_biz_id"],
            "bk_cloud_id": cluster_meta_data["bk_cloud_id"],
            "cluster_ids": cluster_ids,
            "db_version": db_version,
            "meta_func_name": RedisDBMeta.redis_cluster_version_update.__name__,
        }
        return {
            "act_name": _("刷新集群元数据的版本信息"),
            "act_component_code": RedisDBMetaComponent.code,
            "kwargs": asdict(act_kwargs),
        }

    def _build_dbconfig_version_acts(self, cluster_meta_list: List[Dict], target_version: str) -> List[Dict]:
        """构造 dbconfig 版本迁移动作; 目标版本不变时不加 no-op 节点."""
        acts = []
        for cluster_meta_data in cluster_meta_list:
            if cluster_meta_data["major_version"] == target_version:
                continue
            act_kwargs = self._make_act_kwargs()
            act_kwargs.cluster = {
                "bk_biz_id": cluster_meta_data["bk_biz_id"],
                "cluster_domain": cluster_meta_data["immute_domain"],
                "current_version": cluster_meta_data["major_version"],
                "target_version": target_version,
                "cluster_type": cluster_meta_data["cluster_type"],
            }
            act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_version_update_dbconfig.__name__
            acts.append(
                {
                    "act_name": _("{}-dbconfig更新版本").format(cluster_meta_data["immute_domain"]),
                    "act_component_code": RedisConfigComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        return acts

    def _build_redis_instance_role_meta_act(self, cluster_ids: List[int]) -> Dict:
        """构造 RedisInstance 主从角色元数据翻转 act."""
        act_kwargs = self._make_act_kwargs()
        act_kwargs.cluster = {
            "cluster_ids": cluster_ids,
            "meta_func_name": RedisDBMeta.update_meta_for_redis_instance_version_upgrade.__name__,
        }
        return {
            "act_name": _("刷新集群元数据的主从信息"),
            "act_component_code": RedisDBMetaComponent.code,
            "kwargs": asdict(act_kwargs),
        }

    def _build_freshing_version_act(self, cluster_meta_data, switch) -> Dict:
        """构造单个 cluster 的版本元数据刷新 act (不挂到 pipeline 上)."""
        valid_options = self.MetaUpdateOption.get_valid_options()
        if switch not in valid_options:
            raise Exception(_("未知的版本元数据更新对象: {} 可选的值: {}").format(switch, ", ".join(valid_options)))
        act_kwargs = self._make_act_kwargs()
        act_kwargs.cluster["cluster_id"] = cluster_meta_data["cluster_id"]
        act_kwargs.cluster["bk_biz_id"] = cluster_meta_data["bk_biz_id"]
        act_kwargs.cluster[switch] = True
        return {
            "act_name": _("刷新实例元数据版本信息({})").format(switch),
            "act_component_code": RedisUpdateVersionComponent.code,
            "kwargs": asdict(act_kwargs),
        }

    def _add_freshing_version_act(self, pipeline, cluster_meta_data, switch):
        """刷新版本元数据信息 (单 cluster, 串行节点)."""
        act = self._build_freshing_version_act(cluster_meta_data, switch)
        pipeline.add_act(
            act_name=act["act_name"],
            act_component_code=act["act_component_code"],
            kwargs=act["kwargs"],
        )

    def _add_freshing_version_acts_parallel(self, pipeline, cluster_meta_list: List[Dict], switch):
        """多 cluster 版本元数据并发刷新; cluster_meta_list 为空时不加节点."""
        if not cluster_meta_list:
            return
        acts = [self._build_freshing_version_act(meta, switch) for meta in cluster_meta_list]
        pipeline.add_parallel_acts(acts_list=acts)

    class MetaUpdateOption:
        """Redis cluster metadata update options"""

        UPDATE_PROXY = "update_proxy"
        UPDATE_STORAGE = "update_storage"
        UPDATE_ALL = "update_all"

        @classmethod
        def get_valid_options(cls):
            """Get all valid update options"""
            return [cls.UPDATE_PROXY, cls.UPDATE_STORAGE, cls.UPDATE_ALL]
