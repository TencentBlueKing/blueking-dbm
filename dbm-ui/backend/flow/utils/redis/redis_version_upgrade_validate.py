# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

主从版(TendisRedisInstance) Redis 版本升级的 IP 对分桶与校验.

主从版一台机器上可能跑着多个集群的实例, 而升级(无论原地换二进制还是整机替换)都要做
主从切换, 所以必须以物理 (master_ip, slave_ip) 对为单位校验, 不能以集群为单位.
原地升级与整机替换升级对这一点的要求完全一致, 故统一实现在此.
"""
from typing import Dict, List, Set, Tuple

from django.utils.translation import gettext_lazy as _

from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.utils.redis.redis_proxy_util import (
    get_redis_version_by_ip,
    get_storage_version_names_by_cluster_type,
)
from backend.flow.utils.redis.redis_util import is_cross_engine_version_change, version_gt

PairKey = Tuple[str, str]

# 规则 3 的报错文案: 同一 IP 上的兄弟集群漏提交会导致该 IP 同时承载 master 和 slave 实例
_PAIR_SCOPE_ERR = _(
    "{} {} 上的集群 {} 未加入本次升级。 主从版升级会执行主从切换, 如果只切换部分集群, 会导致该 IP 同时承载 master 和 slave 实例, " "破坏角色一致性, 请将这些集群一并加入升级"
)
_ROLES = (
    ("as_master_cluster_ids", InstanceRole.REDIS_MASTER.value, "master_ip"),
    ("as_slave_cluster_ids", InstanceRole.REDIS_SLAVE.value, "slave_ip"),
)


def get_master_slave_ips(cluster: Cluster) -> PairKey:
    """取主从版集群的 (master_ip, slave_ip)"""
    master_inst = cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value).first()
    if not master_inst:
        raise Exception(_("集群 {} 未找到 master 实例").format(cluster.immute_domain))
    tuple_obj = master_inst.as_ejector.first()
    if not tuple_obj:
        raise Exception(_("集群 {} master {} 没有对应的 slave 记录").format(cluster.immute_domain, master_inst.ip_port))
    return master_inst.machine.ip, tuple_obj.receiver.machine.ip


def register_pair_entry(
    cluster: Cluster,
    target_version: str,
    ips_in_item: Set[str],
    pair_buckets: Dict[PairKey, Dict],
    ip_index: Dict[str, Dict],
    cluster_meta: Dict[int, Dict],
):
    """把单个集群的升级声明注册到 pair 桶与 IP 索引.

    只做单集群元信息解析 + 聚合, 完整校验在 validate_pair_buckets 里进行.

    @param ips_in_item: 本次要升级的 IP 集合, 必须是该集群主从对的子集且必须包含 slave_ip
      (主从版一律 slave 先升级). 整机替换的 "master 成对替换" 会同时换掉两台机器,
      调用方应传 {master_ip, slave_ip}.
    """
    cluster_id = cluster.id
    master_ip, slave_ip = get_master_slave_ips(cluster)

    unknown_ips = ips_in_item - {master_ip, slave_ip}
    if unknown_ips:
        raise Exception(
            _("集群 {} 的升级 IP {} 不属于该集群的主从对 ({}/{})").format(
                cluster.immute_domain, sorted(unknown_ips), master_ip, slave_ip
            )
        )
    if slave_ip not in ips_in_item:
        raise Exception(
            _("集群 {} 主从版升级必须包含 slave_ip={}, 当前只指定了 {}").format(cluster.immute_domain, slave_ip, sorted(ips_in_item))
        )
    upgrade_master = master_ip in ips_in_item

    cluster_meta[cluster_id] = {
        "cluster": cluster,
        "master_ip": master_ip,
        "slave_ip": slave_ip,
        "target_version": target_version,
        "upgrade_master": upgrade_master,
    }

    bucket = pair_buckets.setdefault(
        (master_ip, slave_ip),
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
        idx = ip_index.setdefault(
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


def validate_pair_buckets(
    pair_buckets: Dict[PairKey, Dict],
    ip_index: Dict[str, Dict],
    cluster_meta: Dict[int, Dict],
):
    """
    对 pair/IP 索引做五类校验, 并把通过校验的桶收敛成单值:
    1. 单 IP 目标版本一致;
    2. 单 IP 仅属一种 (master_ip, slave_ip) 拓扑;
    3. 单 IP 上兄弟集群必须全部在升级列表 (master 侧和 slave 侧分别校验);
    4. 同一 pair 内 upgrade scope 一致;
    5. 目标版本合法性 / 不允许降级 (每 pair 一次).
    """
    if not pair_buckets:
        return

    # 规则 3 说明:
    # master 侧: 该 IP 上所有 master 实例对应的集群都必须在
    # slave  侧: 该 IP 上所有 slave  实例对应的集群都必须在
    # 没有同时校验 "该 IP 上所有集群(不区分角色)" 因为一个 IP 作为 master 或 slave 只会有一种角色
    #
    # 完备性说明: 该校验只遍历 ip_index, 即只覆盖本次 infos 中出现过的 IP.
    # 看似可能漏掉 "整个 IP 都未出现在请求里" 的兄弟集群, 但 DBM 部署模型保证不会出现这种漏检:
    #   1. 非 TendisRedisInstance 集群之间不存在物理 IP 重叠;
    #   2. TendisRedisInstance 同一 (master_ip, slave_ip) pair 上的兄弟集群共享完全一致的角色映射,
    #      即如果 1.1.1.1 是集群 A 的 master, 它也是同 pair 上 B/C/... 所有兄弟集群的 master;
    #      不存在 "同一 IP 在 A 中是 master 而在 B 中是 slave" 的混合角色情况.
    # 因此只要请求里包含了该 pair 上的任一兄弟集群, 该 pair 的 master_ip 与 slave_ip 都会进入索引,
    # 下面通过 StorageInstance 的 DB 反查即可发现所有未提交的兄弟, 不存在静默跳过的盲区.
    for ip, info in ip_index.items():
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
        for key, role, label in _ROLES:
            if not (exp := info[key]):
                continue
            act = set(
                StorageInstance.objects.filter(machine__ip=ip, instance_role=role).values_list(
                    "cluster__id", flat=True
                )
            )
            if miss := act - exp:
                raise Exception(_PAIR_SCOPE_ERR.format(label, ip, sorted(miss)))

    # 一次遍历完成 pair 维度的规则 4/5 (顺序: scope 一致 → 版本合法 → 不降级 → finalize)
    for (master_ip, slave_ip), bucket in pair_buckets.items():
        # 规则 4: pair 内 upgrade scope 一致
        if len(bucket["upgrade_master_flags"]) > 1:
            raise Exception(
                _("IP对 {}/{} 上的集群 {} 升级范围不一致(是否升级 master 冲突), 请统一").format(
                    master_ip, slave_ip, sorted(bucket["cluster_ids"])
                )
            )

        # 规则 5: version-validity / downgrade 校验 (每 pair 执行一次)
        # 经过前面校验, 此处 target_versions 与 upgrade_master_flags 均已 size=1
        target_version = next(iter(bucket["target_versions"]))
        upgrade_master = next(iter(bucket["upgrade_master_flags"]))
        any_cluster_id = bucket["cluster_ids"][0]
        any_cluster = cluster_meta[any_cluster_id]["cluster"]
        valid_versions = get_storage_version_names_by_cluster_type(any_cluster.cluster_type, True)
        if target_version not in valid_versions:
            raise Exception(
                _("Redis集群 {} 目标版本 {} 不合法, 合法版本: {}").format(any_cluster.immute_domain, target_version, valid_versions)
            )

        # 不支持降级: 只需分别检查一次 master_ip / slave_ip (同 IP 上版本一致)
        ips_to_check: List[str] = [slave_ip] + ([master_ip] if upgrade_master else [])
        for ip in ips_to_check:
            cur_ver = get_redis_version_by_ip(any_cluster_id, ip)
            if is_cross_engine_version_change(cur_ver, target_version):
                raise Exception(
                    _("集群 {} IP {} 当前版本 {} 与目标版本 {} 引擎不同(Redis/Valkey), 不支持跨引擎版本升级, 请使用 DTS 数据迁移").format(
                        any_cluster.immute_domain, ip, cur_ver, target_version
                    )
                )
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
