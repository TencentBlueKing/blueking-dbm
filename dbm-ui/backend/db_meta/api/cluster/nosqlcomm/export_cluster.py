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

from django.utils.translation import gettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.enums import ClusterEntryType, ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.db_meta.models.cluster_entry import CLBEntryDetail, PolarisEntryDetail
from backend.db_meta.models.storage_set_dtl import NosqlStorageSetDtl
from backend.flow.consts import DEFAULT_DB_MODULE_ID, ConfigFileEnum, ConfigTypeEnum
from backend.flow.utils.base.payload_handler import PayloadHandler

logger = logging.getLogger("root")


def export_twemproxy_cluster(cluster_id: int) -> dict:
    """
    导出 TendisTwemproxyRedisInstance / TwemproxyTendisSSDInstance 集群元数据。

    返回格式示例:
    {
      "proxies": [
        {"spec_id": 78, "ip": "1.2.3.4", "port": 50000},
        ...
      ],
      "backends": [
        {
          "shard": "0-52499",
          "nodes": {
            "master": {"spec_id": 77, "ip": "1.1.1.1", "port": 30000},
            "slave":  {"spec_id": 77, "ip": "1.1.1.2", "port": 30000}
          }
        },
        ...
      ],
      "entry": {
        "clb": {},
        "polairs": {}
      },
      "proxy_config":  {},
      "redis_config":  {},
      "backup_config": {},
      "clusterinfo": {
        "name":          "xxx",
        "immute_domain": "xxx.db",
        "nodes_domain":  "",
        "alias":         "xxx",
        "cluster_type":  "TwemproxyRedisInstance",
        "db_version":    "Redis-2",
        "region":        "深圳",
        "developer":     "",
        "creater":       "xxx",
        "create_at":     "2014-03-26T10:34:21+08:00"
      }
    }
    """
    cluster = Cluster.objects.get(id=cluster_id)

    # 仅支持 Twemproxy 系列集群
    if cluster.cluster_type not in (
        ClusterType.TendisTwemproxyRedisInstance.value,
        ClusterType.TwemproxyTendisSSDInstance.value,
    ):
        raise ValueError(
            _(
                "export_twemproxy_cluster 仅支持 TendisTwemproxyRedisInstance / TwemproxyTendisSSDInstance，" "当前集群类型: {}"
            ).format(cluster.cluster_type)
        )

    # ── 1. 导出 proxies ──────────────────────────────────────────────────────
    proxies = []
    for proxy in cluster.proxyinstance_set.select_related("machine").order_by("machine__ip", "port"):
        proxies.append(
            {
                "spec_id": proxy.machine.spec_id,
                "ip": proxy.machine.ip,
                "port": proxy.port,
            }
        )

    # ── 2. 导出 backends（按分片规则组织 master/slave 对）────────────────────
    # 从 NosqlStorageSetDtl 获取 master 实例与分片范围的映射
    shard_dtl_map = {
        dtl.instance_id: dtl.seg_range
        for dtl in NosqlStorageSetDtl.objects.filter(cluster=cluster).select_related("instance")
    }

    # 获取集群内所有 master 实例
    master_instances = (
        cluster.storageinstance_set.select_related("machine")
        .filter(instance_inner_role=InstanceInnerRole.MASTER.value)
        .order_by("machine__ip", "port")
    )

    backends = []
    for master in master_instances:
        seg_range = shard_dtl_map.get(master.id, "")

        # 通过主从关系表找到对应的 slave
        slave_tuple = master.as_ejector.select_related("receiver__machine").first()
        if slave_tuple is None:
            logger.warning("master {}:{} 没有对应的 slave，跳过".format(master.machine.ip, master.port))
            continue

        slave = slave_tuple.receiver
        backends.append(
            {
                "shard": seg_range,
                "nodes": {
                    "master": {
                        "spec_id": master.machine.spec_id,
                        "ip": master.machine.ip,
                        "port": master.port,
                    },
                    "slave": {
                        "spec_id": slave.machine.spec_id,
                        "ip": slave.machine.ip,
                        "port": slave.port,
                    },
                },
            }
        )

    # ── 3. 导出访问入口（CLB / Polaris）────────────────────────────────────
    clb_info = {}
    polaris_info = {}

    for cluster_entry in cluster.clusterentry_set.all():
        if cluster_entry.cluster_entry_type == ClusterEntryType.CLB.value:
            detail_obj = CLBEntryDetail.objects.filter(entry=cluster_entry).first()
            if detail_obj:
                # 查找关联的 CLB DNS 入口
                from backend.db_meta.models import ClusterEntry as CE

                clb_dns = CE.objects.filter(
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

    # ── 4. 导出 proxy_config（Twemproxy 代理配置 + 密码）────────────────────
    # namespace 与集群类型保持一致（TwemproxyRedisInstance / TwemproxyTendisSSDInstance）
    namespace = cluster.cluster_type
    proxy_config = {}
    redis_config = {}
    backup_config = {}
    try:
        passwd_ret = PayloadHandler.redis_get_password_by_domain(cluster.immute_domain)
        proxy_resp = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(cluster.bk_biz_id),
                "level_name": LevelName.CLUSTER.value,
                "level_value": cluster.immute_domain,
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "conf_file": ConfigFileEnum.Twemproxy.value,
                "conf_type": ConfigTypeEnum.ProxyConf.value,
                "namespace": namespace,
                "format": FormatType.MAP.value,
            }
        )
        proxy_config_rsp = proxy_resp.get("content", {})
        # 补充密码字段
        proxy_config["mbuf-size"] = proxy_config_rsp.get("mbuf-size", "")
        proxy_config["hash_tag"] = proxy_config_rsp.get("hash_tag", "")
        proxy_config["password"] = passwd_ret.get("redis_proxy_password", "")
        proxy_config["redis_password"] = passwd_ret.get("redis_password", "")
    except Exception:
        logger.warning("获取集群 {} proxy_config 失败".format(cluster.immute_domain))

    # ── 5. 导出 redis_config（Redis 实例配置 + 密码）────────────────────────
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
        # 补充 requirepass
        redis_config["requirepass"] = passwd_ret.get("redis_password", "")
        redis_config["databases"] = redis_config_resp.get("databases", "2")
    except Exception:
        logger.warning("获取集群 {} redis_config 失败".format(cluster.immute_domain))

    # ── 6. 导出 backup_config（全备配置）────────────────────────────────────
    try:
        backup_resp = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(cluster.bk_biz_id),
                "level_name": LevelName.CLUSTER.value,
                "level_value": cluster.immute_domain,
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "conf_file": ConfigFileEnum.FullBackup.value,
                "conf_type": ConfigTypeEnum.Config.value,
                "namespace": namespace,
                "format": FormatType.MAP.value,
            }
        )
        backup_config = backup_resp.get("content", {})
    except Exception:
        logger.warning("获取集群 {} backup_config 失败".format(cluster.immute_domain))

    # ── 7. 集群基本信息 ───────────────────────────────────────────────────────
    create_at = ""
    if cluster.create_at:
        create_at = cluster.create_at.isoformat()

    clusterinfo = {
        "name": cluster.name,
        "immute_domain": cluster.immute_domain,
        "nodes_domain": "",
        "alias": cluster.alias,
        "cluster_type": cluster.cluster_type,
        "db_version": cluster.major_version,
        "region": cluster.region,
        "developer": "",
        "creater": cluster.creator,
        "create_at": create_at,
    }

    return {
        "proxies": proxies,
        "backends": backends,
        "entry": entry,
        "proxy_config": proxy_config,
        "redis_config": redis_config,
        "backup_config": backup_config,
        "clusterinfo": clusterinfo,
    }
