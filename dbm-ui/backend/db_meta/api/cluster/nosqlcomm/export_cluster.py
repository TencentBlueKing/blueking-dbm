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
import json
import logging
import os
from datetime import datetime

from django.db import transaction
from django.utils.translation import gettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster, ClusterEntry
from backend.db_meta.models.cluster_entry import CLBEntryDetail, PolarisEntryDetail
from backend.db_meta.models.storage_set_dtl import NosqlStorageSetDtl
from backend.flow.consts import DEFAULT_DB_MODULE_ID, ConfigFileEnum, ConfigTypeEnum
from backend.flow.utils.base.payload_handler import PayloadHandler

logger = logging.getLogger("root")

# 支持的集群类型集合
_TWEMPROXY_CLUSTER_TYPES = (
    ClusterType.TendisTwemproxyRedisInstance.value,
    ClusterType.TwemproxyTendisSSDInstance.value,
)
_TENDISPLUS_CLUSTER_TYPES = (ClusterType.TendisPredixyTendisplusCluster.value,)
_ALL_SUPPORTED_CLUSTER_TYPES = _TWEMPROXY_CLUSTER_TYPES + _TENDISPLUS_CLUSTER_TYPES


def export_redis_cluster(cluster_id: int, slim: bool = False) -> dict:
    """
    导出 Redis 系列集群（Twemproxy / Tendisplus）元数据，自动根据集群类型处理差异。

    支持的集群类型：
      - TendisTwemproxyRedisInstance
      - TwemproxyTendisSSDInstance
      - TendisPredixyTendisplusCluster

    返回格式示例（Twemproxy 系列）:
    {
      "proxies": [{"spec_id": 78, "ip": "1.2.3.4", "port": 50000}, ...],
      "backends": [
        {
          "shard": "0-52499",          # Tendisplus 集群无此字段
          "nodes": {
            "master": {"spec_id": 77, "ip": "1.1.1.1", "port": 30000},
            "slave":  {"spec_id": 77, "ip": "1.1.1.2", "port": 30000}
          }
        },
        ...
      ],
      "entry": {"clb": {}, "polairs": {}},
      "passwords": {                   # slim=True 时存在，包含密码信息
        "redis_password": "xxx",
        "redis_proxy_password": "xxx",
        "redis_proxy_admin_password": "xxx"
      },
      "proxy_config":  {},             # slim=True 时不存在
      "redis_config":  {},             # slim=True 时不存在
      "backup_config": {},             # slim=True 时不存在
      "clusterinfo": {
        "name":          "xxx",
        "immute_domain": "xxx.db",
        "nodes_domain":  "",           # Tendisplus 集群为 "nodes.xxx.db"
        "alias":         "xxx",
        "cluster_type":  "TwemproxyRedisInstance",
        "db_version":    "Redis-2",
        "region":        "深圳",
        "developer":     "",
        "creater":       "xxx",
        "create_at":     "2014-03-26T10:34:21+08:00"
      }
    }

    :param cluster_id: 集群 ID
    :param slim:       精简模式，True 时去掉 proxy_config/redis_config/backup_config，
                       密码单独放到顶层 passwords 字段
    """
    cluster = Cluster.objects.get(id=cluster_id)
    logger.info(_("export_redis_cluster: 开始导出集群 {} (id={})").format(cluster.immute_domain, cluster_id))

    if cluster.cluster_type not in _ALL_SUPPORTED_CLUSTER_TYPES:
        raise ValueError(
            _("export_redis_cluster 不支持当前集群类型: {}，仅支持: {}").format(
                cluster.cluster_type, ", ".join(_ALL_SUPPORTED_CLUSTER_TYPES)
            )
        )

    is_tendisplus = cluster.cluster_type in _TENDISPLUS_CLUSTER_TYPES

    # ── 1. 导出 proxies ──────────────────────────────────────────────────────
    proxies = [
        {
            "spec_id": proxy.machine.spec_id,
            "spec_config": proxy.machine.spec_config,
            "ip": proxy.machine.ip,
            "port": proxy.port,
        }
        for proxy in cluster.proxyinstance_set.select_related("machine").order_by("machine__ip", "port")
    ]

    # ── 2. 导出 backends ─────────────────────────────────────────────────────
    # Twemproxy 系列：从 NosqlStorageSetDtl 获取分片范围
    # Tendisplus 系列：直接按 master/slave 角色遍历，无分片范围
    if is_tendisplus:
        shard_dtl_map = {}
    else:
        shard_dtl_map = {
            dtl.instance_id: dtl.seg_range
            for dtl in NosqlStorageSetDtl.objects.filter(cluster=cluster).select_related("instance")
        }

    master_instances = (
        cluster.storageinstance_set.select_related("machine")
        .filter(instance_inner_role=InstanceInnerRole.MASTER.value)
        .order_by("machine__ip", "port")
    )

    backends = []
    for master in master_instances:
        slave_tuple = master.as_ejector.select_related("receiver__machine").first()
        if slave_tuple is None:
            logger.warning(_("master {}:{} 没有对应的 slave，跳过").format(master.machine.ip, master.port))
            continue

        slave = slave_tuple.receiver
        backend = {
            "nodes": {
                "master": {
                    "spec_id": master.machine.spec_id,
                    "spec_config": master.machine.spec_config,
                    "ip": master.machine.ip,
                    "port": master.port,
                },
                "slave": {
                    "spec_id": slave.machine.spec_id,
                    "spec_config": slave.machine.spec_config,
                    "ip": slave.machine.ip,
                    "port": slave.port,
                },
            }
        }
        # Twemproxy 系列补充分片范围
        if not is_tendisplus:
            backend["shard"] = shard_dtl_map.get(master.id, "")
        backends.append(backend)

    # ── 3. 导出访问入口（CLB / Polaris）────────────────────────────────────
    clb_info = {}
    polaris_info = {}

    for cluster_entry in cluster.clusterentry_set.all():
        if cluster_entry.cluster_entry_type == ClusterEntryType.CLB.value:
            detail_obj = CLBEntryDetail.objects.filter(entry=cluster_entry).first()
            if detail_obj:
                clb_dns = ClusterEntry.objects.filter(
                    forward_to=cluster_entry,
                    cluster_entry_type=ClusterEntryType.CLBDNS.value,
                ).first()
                clb_info = {
                    "clb_ip": detail_obj.clb_ip,
                    "clb_id": detail_obj.clb_id,
                    "listener_id": detail_obj.listener_id,
                    "clb_region": detail_obj.clb_region,
                    "clb_port": detail_obj.clb_port,
                    "clb_domain": clb_dns.entry if clb_dns else "",
                    "entry": cluster_entry.entry,
                }

        elif cluster_entry.cluster_entry_type == ClusterEntryType.POLARIS.value:
            detail_obj = PolarisEntryDetail.objects.filter(entry=cluster_entry).first()
            if detail_obj:
                polaris_info = {
                    "polaris_name": detail_obj.polaris_name,
                    "polaris_l5": detail_obj.polaris_l5,
                    "polaris_token": detail_obj.polaris_token,
                    "alias_token": detail_obj.alias_token,
                    "entry": cluster_entry.entry,
                }

    entry = {"clb": clb_info, "polairs": polaris_info}

    # ── 4. 导出 proxy_config（代理配置 + 密码）──────────────────────────────
    # Twemproxy 系列使用 ConfigFileEnum.Twemproxy，Tendisplus 使用 ConfigFileEnum.Predixy
    namespace = cluster.cluster_type
    proxy_conf_file = ConfigFileEnum.Predixy.value if is_tendisplus else ConfigFileEnum.Twemproxy.value

    proxy_config = {}
    redis_config = {}
    passwd_ret = {}
    try:
        passwd_ret = PayloadHandler.redis_get_password_by_domain(cluster.immute_domain)
        proxy_resp = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(cluster.bk_biz_id),
                "level_name": LevelName.CLUSTER.value,
                "level_value": cluster.immute_domain,
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "conf_file": proxy_conf_file,
                "conf_type": ConfigTypeEnum.ProxyConf.value,
                "namespace": namespace,
                "format": FormatType.MAP.value,
            }
        )
        proxy_config_rsp = proxy_resp.get("content", {})
        proxy_config["password"] = passwd_ret.get("redis_proxy_password", "")
        proxy_config["redis_password"] = passwd_ret.get("redis_password", "")
        if is_tendisplus:
            proxy_config["redis_proxy_admin_password"] = passwd_ret.get("redis_proxy_admin_password", "")
            proxy_config["slowloglogslowerthan"] = proxy_config_rsp.get("slowloglogslowerthan", "")
        else:
            # Twemproxy：仅取关键字段
            proxy_config["mbuf-size"] = proxy_config_rsp.get("mbuf-size", "")
            proxy_config["hash_tag"] = proxy_config_rsp.get("hash_tag", "")
    except Exception as e:
        logger.error(_("获取集群 {} 密码失败: {}，密码将为空").format(cluster.immute_domain, e))
        logger.warning(_("获取集群 {} proxy_config 失败").format(cluster.immute_domain, e))

    # ── 5. 导出 redis_config（实例配置 + 密码）──────────────────────────────
    try:
        redis_resp = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(cluster.bk_biz_id),
                "level_name": LevelName.CLUSTER.value,
                "level_value": cluster.immute_domain,
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "conf_file": cluster.major_version,
                "conf_type": ConfigTypeEnum.DBConf.value,
                "namespace": namespace,
                "format": FormatType.MAP.value,
            }
        )
        redis_config_resp = redis_resp.get("content", {})
        redis_config["requirepass"] = passwd_ret.get("redis_password", "")
        if is_tendisplus:
            redis_config["kvstorecount"] = redis_config_resp.get("kvstorecount", "10")
        else:
            redis_config["databases"] = redis_config_resp.get("databases", "2")
    except Exception:
        logger.warning(_("获取集群 {} redis_config 失败").format(cluster.immute_domain))

    # ── 7. 获取 nodes_domain（仅 Tendisplus 集群有）─────────────────────────
    nodes_domain = ""
    if is_tendisplus:
        nodes_entry = cluster.clusterentry_set.filter(
            cluster_entry_type=ClusterEntryType.DNS.value,
            role=ClusterEntryRole.NODE_ENTRY.value,
        ).first()
        if nodes_entry:
            nodes_domain = nodes_entry.entry

    # ── 8. 集群基本信息 ───────────────────────────────────────────────────────
    create_at = cluster.create_at.isoformat() if cluster.create_at else ""

    clusterinfo = {
        "name": cluster.name,
        "immute_domain": cluster.immute_domain,
        "nodes_domain": nodes_domain,
        "alias": cluster.alias,
        "cluster_type": cluster.cluster_type,
        "db_version": cluster.major_version,
        "region": cluster.region,
        "developer": "",
        "creater": cluster.creator,
        "create_at": create_at,
    }

    if slim:
        # 精简模式：去掉三个 config，密码单独放到 passwords
        passwords = {
            "redis_password": passwd_ret.get("redis_password", ""),
            "redis_proxy_password": passwd_ret.get("redis_proxy_password", ""),
            "redis_proxy_admin_password": passwd_ret.get("redis_proxy_admin_password", ""),
        }
        logger.info(_("export_redis_cluster: 导出集群 {} 完成 (slim)").format(cluster.immute_domain))
        return {
            "proxies": proxies,
            "backends": backends,
            "entry": entry,
            "passwords": passwords,
            "clusterinfo": clusterinfo,
        }

    logger.info(_("export_redis_cluster: 导出集群 {} 完成").format(cluster.immute_domain))
    return {
        "proxies": proxies,
        "backends": backends,
        "entry": entry,
        "proxy_config": proxy_config,
        "redis_config": redis_config,
        "clusterinfo": clusterinfo,
    }


def export_biz_redis_clusters(bk_biz_id: int, output_dir: str = "/tmp") -> str:
    """
    导出指定业务下所有 Redis 集群（Twemproxy / Tendisplus）的元数据到 JSON 文件。

    去掉 proxy_config / redis_config / backup_config，密码单独保留在 passwords 字段。

    :param bk_biz_id:   业务 ID
    :param output_dir:  输出目录，默认 /tmp
    :return:            输出文件的完整路径
    """
    cluster_list_qs = list(
        Cluster.objects.filter(
            bk_biz_id=bk_biz_id,
            cluster_type__in=_ALL_SUPPORTED_CLUSTER_TYPES,
        )
    )

    # 取第一个集群的 db_module_id / bk_cloud_id 作为文件级元数据（同业务下通常一致）
    first_cluster = cluster_list_qs[0] if cluster_list_qs else None
    file_db_module_id = first_cluster.db_module_id if first_cluster else DEFAULT_DB_MODULE_ID
    file_bk_cloud_id = first_cluster.bk_cloud_id if first_cluster else 0

    cluster_list = []
    for cluster in cluster_list_qs:
        try:
            data = export_redis_cluster(cluster.id, slim=True)
            cluster_list.append(data)
            logger.info(_("export_biz_redis_clusters: 导出集群 {} 成功").format(cluster.immute_domain))
        except Exception as e:
            logger.warning(_("export_biz_redis_clusters: 导出集群 {} 失败: {}").format(cluster.immute_domain, e))

    # 文件顶层写入元数据，供导入时直接读取
    output_data = {
        "meta": {
            "bk_biz_id": bk_biz_id,
            "db_module_id": file_db_module_id,
            "bk_cloud_id": file_bk_cloud_id,
        },
        "clusters": cluster_list,
    }

    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, "redis_clusters_{}_{}.json".format(bk_biz_id, ts))
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info(_("export_biz_redis_clusters: 共导出 {} 个集群到 {}").format(len(cluster_list), output_file))
    return output_file


@transaction.atomic
def import_redis_cluster(
    bk_biz_id: int,
    db_module_id: int,
    cluster_data: dict,
    creator: str = "",
    bk_cloud_id: int = 0,
):
    """
    将 export_redis_cluster 导出的元数据重新写回，创建集群及其配置。

    machine_specs 自动从 cluster_data 中的 proxies/backends 的 spec_id 字段提取，无需额外传入。
    密码优先从 cluster_data["passwords"] 取（slim 模式导出），其次从 proxy_config 取（完整模式导出）。

    **幂等性说明**：本函数不具备幂等性。若目标集群的 immute_domain 在数据库中已存在，
    内部的 before_create_domain_precheck 会抛出异常，整个事务回滚。
    在批量导入场景（import_biz_redis_clusters）中，该异常会被捕获并记录到 failed 列表，
    不影响其他集群的导入。若需重新导入某个集群，请先手动删除已有的集群元数据。

    :param bk_biz_id:      业务 ID
    :param db_module_id:   DB 模块 ID
    :param cluster_data:   export_redis_cluster 返回的完整 dict
    :param creator:        操作人，默认取 clusterinfo.creater
    :param bk_cloud_id:    云区域 ID，默认取 0
    """
    from backend.db_meta.api.cluster.nosqlcomm.create_cluster import (
        pkg_create_tendisplus_cluster,
        pkg_create_twemproxy_cluster,
    )

    clusterinfo = cluster_data["clusterinfo"]
    proxies = cluster_data["proxies"]
    backends = cluster_data["backends"]
    # 兼容 slim 模式（passwords）和完整模式（proxy_config）
    passwords = cluster_data.get("passwords", {})
    proxy_config = cluster_data.get("proxy_config", {})

    cluster_type = clusterinfo["cluster_type"]
    immute_domain = clusterinfo["immute_domain"]
    name = clusterinfo["name"]
    alias = clusterinfo.get("alias", "")
    major_version = clusterinfo["db_version"]
    region = clusterinfo.get("region", "")
    creator = creator or clusterinfo.get("creater", "")

    is_tendisplus = cluster_type in _TENDISPLUS_CLUSTER_TYPES
    is_twemproxy = cluster_type in _TWEMPROXY_CLUSTER_TYPES

    if not is_tendisplus and not is_twemproxy:
        raise ValueError(
            _("import_redis_cluster 不支持当前集群类型: {}，仅支持: {}").format(
                cluster_type, ", ".join(_ALL_SUPPORTED_CLUSTER_TYPES)
            )
        )

    # ── 1. 从导出数据中提取 machine_specs ────────────────────────────────────
    proxy_spec_id = proxies[0].get("spec_id", 0) if proxies else 0
    proxy_spec_config = proxies[0].get("spec_config", {}) if proxies else {}
    redis_spec_id = 0
    redis_spec_config = {}
    if backends:
        master_node = backends[0].get("nodes", {}).get("master", {})
        redis_spec_id = master_node.get("spec_id", 0)
        redis_spec_config = master_node.get("spec_config", {})
    machine_specs = {
        "proxy": {"spec_id": proxy_spec_id, "spec_config": proxy_spec_config},
        "redis": {"spec_id": redis_spec_id, "spec_config": redis_spec_config},
    }

    # ── 2. 提取密码（slim 模式优先，兼容完整模式）────────────────────────────
    redis_password = passwords.get("redis_password") or proxy_config.get("redis_password", "")
    redis_proxy_password = passwords.get("redis_proxy_password") or proxy_config.get("password", "")
    redis_proxy_admin_password = passwords.get("redis_proxy_admin_password") or proxy_config.get(
        "redis_proxy_admin_password", ""
    )

    # ── 3. 创建集群元数据 ─────────────────────────────────────────────────────
    logger.info(_("import_redis_cluster: 开始导入集群 {}").format(immute_domain))
    if is_twemproxy:
        pkg_create_twemproxy_cluster(
            bk_biz_id=bk_biz_id,
            name=name,
            immute_domain=immute_domain,
            db_module_id=db_module_id,
            alias=alias,
            major_version=major_version,
            proxies=proxies,
            storages=backends,
            creator=creator,
            bk_cloud_id=bk_cloud_id,
            region=region,
            cluster_type=cluster_type,
            machine_specs=machine_specs,
            redis_password=redis_password,
            redis_proxy_password=redis_proxy_password,
        )
    else:
        pkg_create_tendisplus_cluster(
            bk_biz_id=bk_biz_id,
            name=name,
            immute_domain=immute_domain,
            db_module_id=db_module_id,
            alias=alias,
            major_version=major_version,
            proxies=proxies,
            storages=backends,
            creator=creator,
            bk_cloud_id=bk_cloud_id,
            region=region,
            machine_specs=machine_specs,
            redis_password=redis_password,
            redis_proxy_password=redis_proxy_password,
            redis_proxy_admin_password=redis_proxy_admin_password,
        )

    logger.info(_("import_redis_cluster: 导入集群 {} 完成").format(immute_domain))


def disable_redis_cluster(
    cluster_id: int,
) -> None:
    """
    禁用 Redis 集群并将其加入 DBHA 屏蔽切换列表。

    操作步骤：
      1. 将集群 phase 设置为 OFFLINE（禁用）
      2. 向 ClusterDBHAExt 表写入记录，屏蔽截止时间设为永久（9999-12-31）

    :param cluster_id:  集群 ID
    :param operator:    操作人，用于日志记录
    """
    from datetime import timezone

    from backend.db_meta.enums import ClusterPhase
    from backend.db_meta.models.cluster import ClusterDBHAExt

    cluster = Cluster.objects.get(id=cluster_id)

    # ── 1. 设置集群状态为禁用（OFFLINE）────────────────────────────────────
    old_phase = cluster.phase
    cluster.phase = ClusterPhase.OFFLINE.value
    cluster.alias = _("[已迁移-{}]{}".format(datetime.now().strftime("%Y%m%d"), cluster.alias))
    cluster.save(update_fields=["phase"])
    logger.info(
        _("disable_redis_cluster: 集群 {} (id={}) phase {} -> {}").format(
            cluster.immute_domain, cluster_id, old_phase, ClusterPhase.OFFLINE.value
        )
    )

    # ── 2. 写入 ClusterDBHAExt 屏蔽记录（永久屏蔽）──────────────────────
    now = datetime.now(timezone.utc)
    shield_end_time = datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    obj, created = ClusterDBHAExt.objects.update_or_create(
        cluster=cluster,
        defaults={"begin_time": now, "end_time": shield_end_time, "creator": "admin-disable"},
    )
    action = _("新建") if created else _("更新")
    logger.info(
        _("disable_redis_cluster: 集群 {} (id={}) DBHA 屏蔽记录已{}，截止 {}").format(
            cluster.immute_domain, cluster_id, action, shield_end_time.isoformat()
        )
    )


def import_biz_redis_clusters(
    json_file: str,
    creator: str = "",
) -> dict:
    """
    从 export_biz_redis_clusters 生成的 JSON 文件批量导入 Redis 集群元数据。

    bk_biz_id / db_module_id / bk_cloud_id 均从文件顶层 meta 字段自动读取，无需手动传入。

    :param json_file: JSON 文件路径（由 export_biz_redis_clusters 生成）
    :param creator:   操作人
    :return:          {"success": [...域名], "failed": [...域名]}
    """
    with open(json_file, "r", encoding="utf-8") as f:
        file_data = json.load(f)

    meta = file_data.get("meta", {})
    bk_biz_id = meta.get("bk_biz_id", 0)
    db_module_id = meta.get("db_module_id", DEFAULT_DB_MODULE_ID)
    bk_cloud_id = meta.get("bk_cloud_id", 0)
    clusters = file_data.get("clusters", [])

    logger.info(
        _("import_biz_redis_clusters: 读取文件 {}，bk_biz_id={}, db_module_id={}, bk_cloud_id={}, 共 {} 个集群").format(
            json_file, bk_biz_id, db_module_id, bk_cloud_id, len(clusters)
        )
    )

    success, failed = [], []
    for cluster_data in clusters:
        immute_domain = cluster_data.get("clusterinfo", {}).get("immute_domain", "unknown")
        try:
            import_redis_cluster(
                bk_biz_id=bk_biz_id,
                db_module_id=db_module_id,
                cluster_data=cluster_data,
                creator=creator,
                bk_cloud_id=bk_cloud_id,
            )
            success.append(immute_domain)
            logger.info(_("import_biz_redis_clusters: 导入集群 {} 成功").format(immute_domain))
        except Exception as e:
            failed.append(immute_domain)
            logger.error(_("import_biz_redis_clusters: 导入集群 {} 失败: {}").format(immute_domain, e))

    logger.info(_("import_biz_redis_clusters: 共 {} 个集群，成功 {}，失败 {}").format(len(clusters), len(success), len(failed)))
    return {"success": success, "failed": failed}


@transaction.atomic
def delete_redis_cluster_metadata(
    bk_biz_id: int,
    cluster_id: int,
    immute_domain: str,
) -> None:
    """
    删除 Redis 集群元数据（仅操作 DB 元数据，不涉及 CC/实例下架等操作）。

    为防止误操作，调用方必须同时提供 bk_biz_id、cluster_id、immute_domain 三个参数，
    三者必须与数据库中的记录完全一致，否则抛出异常并回滚。

    删除顺序：
      1. 清理 ClusterEntry 的 forward_to 自关联（避免外键约束）
      2. 删除所有 ClusterEntry
      3. 清理 ProxyInstance 与 StorageInstance 的关联关系（M2M）
      4. 删除所有 ProxyInstance 及其 Machine（若 Machine 上无其他实例）
      5. 删除所有 StorageInstance 及其 Machine（若 Machine 上无其他实例）
      6. 删除 Cluster 记录本身

    **注意**：本函数不会调用 CC 接口回收主机或删除服务实例，
    如需完整下架请使用 decommission.decommission_cluster。

    :param bk_biz_id:      业务 ID
    :param cluster_id:     集群 ID
    :param immute_domain:  集群不可变域名
    :raises ValueError:    三个参数与数据库记录不一致时抛出
    """
    output_file = export_biz_redis_clusters(bk_biz_id=bk_biz_id, output_dir="/app")
    logger.info(_("delete_redis_cluster_metadata: 集群元数据已备份到 {}").format(output_file))

    from backend.db_meta.models import Machine, ProxyInstance, StorageInstance

    # ── 参数校验：三个字段必须同时匹配 ──────────────────────────────────────
    try:
        cluster = Cluster.objects.get(id=cluster_id)
    except Cluster.DoesNotExist:
        raise ValueError(_("delete_redis_cluster_metadata: 集群 id={} 不存在").format(cluster_id))

    if cluster.bk_biz_id != bk_biz_id:
        raise ValueError(
            _("delete_redis_cluster_metadata: bk_biz_id 不匹配，期望 {}，实际 {}").format(cluster.bk_biz_id, bk_biz_id)
        )
    if cluster.immute_domain != immute_domain:
        raise ValueError(
            _("delete_redis_cluster_metadata: immute_domain 不匹配，期望 {}，实际 {}").format(
                cluster.immute_domain, immute_domain
            )
        )
    if cluster.cluster_type not in _ALL_SUPPORTED_CLUSTER_TYPES:
        raise ValueError(
            _("delete_redis_cluster_metadata 不支持当前集群类型: {}，仅支持: {}").format(
                cluster.cluster_type, ", ".join(_ALL_SUPPORTED_CLUSTER_TYPES)
            )
        )

    confirm = input(
        _("已将业务 {} 下所有 Redis 集群元数据备份至 {}。" "确认继续删除集群 {} (id={}) 的元数据？[yes/no]: ").format(
            bk_biz_id, output_file, immute_domain, cluster_id
        )
    )
    if confirm.strip().lower() != "yes":
        raise ValueError(_("delete_redis_cluster_metadata: 用户取消操作，集群 {} 元数据未删除").format(immute_domain))

    logger.info(
        _("delete_redis_cluster_metadata: 开始删除集群元数据 {} (id={}, bk_biz_id={})").format(
            immute_domain, cluster_id, bk_biz_id
        )
    )

    # ── 1. 清理 ClusterEntry 自关联（forward_to）────────────────────────────
    for entry_obj in cluster.clusterentry_set.filter(forward_to_id__isnull=False).all():
        entry_obj.forward_to_id = None
        entry_obj.save(update_fields=["forward_to_id"])

    # ── 2. 删除所有 ClusterEntry ─────────────────────────────────────────────
    deleted_entries, _deleted_detail = cluster.clusterentry_set.all().delete()
    logger.info(_("delete_redis_cluster_metadata: 删除 ClusterEntry {} 条").format(deleted_entries))

    # ── 3. 清理 ProxyInstance 关联关系并删除实例 ─────────────────────────────
    proxy_machines = set()
    for proxy_obj in cluster.proxyinstance_set.all():
        proxy_machines.add(proxy_obj.machine.ip)
        cluster.proxyinstance_set.remove(proxy_obj)
        proxy_obj.storageinstance.clear()
        proxy_obj.bind_entry.clear()
        proxy_obj.delete()
        logger.info(
            _("delete_redis_cluster_metadata: 删除 ProxyInstance {}:{}").format(proxy_obj.machine.ip, proxy_obj.port)
        )

    # 删除已无实例的 Proxy Machine
    for machine_ip in proxy_machines:
        if not ProxyInstance.objects.filter(machine__ip=machine_ip, machine__bk_cloud_id=cluster.bk_cloud_id).exists():
            machine_obj = Machine.objects.filter(ip=machine_ip, bk_cloud_id=cluster.bk_cloud_id).first()
            if machine_obj:
                machine_obj.delete()
                logger.info(_("delete_redis_cluster_metadata: 删除 Proxy Machine {}").format(machine_ip))

    # ── 4. 清理 StorageInstance 关联关系并删除实例 ───────────────────────────
    storage_machines = set()
    for storage_obj in cluster.storageinstance_set.all():
        storage_machines.add(storage_obj.machine.ip)
        cluster.storageinstance_set.remove(storage_obj)
        storage_obj.delete()
        logger.info(
            _("delete_redis_cluster_metadata: 删除 StorageInstance {}:{}").format(
                storage_obj.machine.ip, storage_obj.port
            )
        )

    # 删除已无实例的 Storage Machine
    for machine_ip in storage_machines:
        if not StorageInstance.objects.filter(
            machine__ip=machine_ip, machine__bk_cloud_id=cluster.bk_cloud_id
        ).exists():
            machine_obj = Machine.objects.filter(ip=machine_ip, bk_cloud_id=cluster.bk_cloud_id).first()
            if machine_obj:
                machine_obj.delete()
                logger.info(_("delete_redis_cluster_metadata: 删除 Storage Machine {}").format(machine_ip))

    # ── 5. 删除 Cluster 记录 ─────────────────────────────────────────────────
    cluster.delete()
    logger.info(_("delete_redis_cluster_metadata: 集群元数据 {} (id={}) 删除完成").format(immute_domain, cluster_id))
