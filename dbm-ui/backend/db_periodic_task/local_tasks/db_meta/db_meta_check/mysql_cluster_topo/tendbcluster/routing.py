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
import re
import time
from typing import Any, Callable, List, Set, Tuple

from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.check_response import CheckResponse
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.decorator import checker_wrapper
from backend.db_report.enums import MetaCheckSubType
from backend.db_report.models import MetaCheckReport

logger = logging.getLogger("root")


def _retry_rpc_call(
    rpc_func: Callable, rpc_params: dict, max_retries: int = 3, retry_interval: float = 1.0
) -> Tuple[Any, str]:
    """
    重试执行 RPC 调用

    @param rpc_func: RPC 调用函数（如 DRSApi.rpc）
    @param rpc_params: RPC 调用参数
    @param max_retries: 最大重试次数，默认3次
    @param retry_interval: 重试间隔时间（秒），默认1秒
    @return: (result, error_msg) 元组，成功时 result 不为 None，失败时 error_msg 不为空
    """
    last_error = None

    for attempt in range(max_retries + 1):  # 总共尝试 max_retries+1 次
        try:
            res = rpc_func(rpc_params)

            if res[0]["error_msg"]:
                last_error = res[0]["error_msg"]
                if attempt < max_retries:
                    time.sleep(retry_interval)  # 重试前等待
                    continue  # 重试
                # 最后一次尝试失败
                return None, last_error

            # 调用成功
            return res, None

        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                time.sleep(retry_interval)  # 重试前等待
                continue  # 重试
            # 最后一次尝试失败
            return None, last_error

    # 理论上不应该到达这里
    return None, last_error or _("未知错误")


def _extract_shard_id_from_server_name(server_name: str, prefix: str) -> int:
    """
    从 Server_name 中提取分片序号
    例如：SPT0 -> 0, SPT_SLAVE10 -> 10
    """
    if server_name.startswith(prefix):
        suffix = server_name[len(prefix) :]
        # 提取数字后缀
        match = re.search(r"\d+$", suffix)
        if match:
            return int(match.group())
    return -1


@checker_wrapper
def _cluster_routing_check(c: Cluster) -> List[CheckResponse]:
    """
    检查 TendbCluster 实际路由和元数据是否对应
    - 在 primary tdbctl 执行 select * from mysql.servers 获取实际路由信息
    - 检查 spider 节点在路由中是否存在
    - 检查后端分片的序号是否一致
    - 检查中控的是否和元数据对得上
    """
    bad = []

    # 获取 primary tdbctl 地址
    try:
        primary_tdbctl = c.tendbcluster_ctl_primary_address()
    except Exception as e:
        bad.append(
            CheckResponse(
                msg=_("获取 primary tdbctl 地址失败: {}").format(str(e)),
                check_subtype=MetaCheckSubType.TenDBClusterRoutingTdbctlNotMatch,
            )
        )
        return bad

    # 在 primary tdbctl 执行 SQL 获取路由信息，最多重试3次
    rpc_params = {
        "addresses": [primary_tdbctl],
        "cmds": ["select * from mysql.servers"],
        "force": False,
        "bk_cloud_id": c.bk_cloud_id,
    }

    res, error_msg = _retry_rpc_call(DRSApi.rpc, rpc_params, max_retries=3)

    if error_msg:
        bad.append(
            CheckResponse(
                msg=_("查询 mysql.servers 失败（已重试3次）: {}").format(error_msg),
                check_subtype=MetaCheckSubType.TenDBClusterRoutingSpiderNotMatch,
            )
        )
        return bad

    routing_data = res[0]["cmd_results"][0]["table_data"]

    # 调用三个子检查函数
    bad.extend(_check_spider_routing(c, routing_data))
    bad.extend(_check_shard_routing(c, routing_data))
    bad.extend(_check_tdbctl_routing(c, routing_data))

    return bad


def _check_spider_routing(c: Cluster, routing_data: List[dict]) -> List[CheckResponse]:
    """
    检查 spider_master 和 spider_slave 节点在中控路由中是否存在
    - spider_master 对应路由中 Wrapper="SPIDER"
    - spider_slave 对应路由中 Wrapper="SPIDER_SLAVE"
    """
    bad = []

    # 从元数据获取 SPIDER_MASTER 节点
    metadata_master_spiders = set()
    for spider in c.proxyinstance_set.filter(
        tendbclusterspiderext__spider_role__in=[
            TenDBClusterSpiderRole.SPIDER_MASTER.value,
            TenDBClusterSpiderRole.SPIDER_MNT.value,
        ]
    ):
        spider_address = f"{spider.machine.ip}{IP_PORT_DIVIDER}{spider.port}"
        metadata_master_spiders.add(spider_address)

    # 从元数据获取 SPIDER_SLAVE 节点
    metadata_slave_spiders = set()
    for spider in c.proxyinstance_set.filter(
        tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE.value
    ):
        spider_address = f"{spider.machine.ip}{IP_PORT_DIVIDER}{spider.port}"
        metadata_slave_spiders.add(spider_address)

    # 从路由表提取 SPIDER 记录（对应 spider_master）
    routing_master_spiders = set()
    for row in routing_data:
        if row.get("Wrapper") == "SPIDER":
            host = row.get("Host", "")
            port = row.get("Port", "")
            if host and port:
                routing_address = f"{host}{IP_PORT_DIVIDER}{port}"
                routing_master_spiders.add(routing_address)

    # 从路由表提取 SPIDER_SLAVE 记录（对应 spider_slave）
    routing_slave_spiders = set()
    for row in routing_data:
        if row.get("Wrapper") == "SPIDER_SLAVE":
            host = row.get("Host", "")
            port = row.get("Port", "")
            if host and port:
                routing_address = f"{host}{IP_PORT_DIVIDER}{port}"
                routing_slave_spiders.add(routing_address)

    # 检查 spider_master 节点
    missing_master_spiders = metadata_master_spiders - routing_master_spiders
    if missing_master_spiders:
        bad.append(
            CheckResponse(
                msg=_("spider_master 节点在中控路由中不存在: {}").format(", ".join(sorted(missing_master_spiders))),
                check_subtype=MetaCheckSubType.TenDBClusterRoutingSpiderNotMatch,
            )
        )

    extra_master_spiders = routing_master_spiders - metadata_master_spiders
    if extra_master_spiders:
        bad.append(
            CheckResponse(
                msg=_("中控路由中存在多余的 spider_master 节点: {}").format(", ".join(sorted(extra_master_spiders))),
                check_subtype=MetaCheckSubType.TenDBClusterRoutingSpiderNotMatch,
            )
        )

    # 检查 spider_slave 节点
    missing_slave_spiders = metadata_slave_spiders - routing_slave_spiders
    if missing_slave_spiders:
        bad.append(
            CheckResponse(
                msg=_("spider_slave 节点在中控路由中不存在: {}").format(", ".join(sorted(missing_slave_spiders))),
                check_subtype=MetaCheckSubType.TenDBClusterRoutingSpiderNotMatch,
            )
        )

    extra_slave_spiders = routing_slave_spiders - metadata_slave_spiders
    if extra_slave_spiders:
        bad.append(
            CheckResponse(
                msg=_("中控路由中存在多余的 spider_slave 节点: {}").format(", ".join(sorted(extra_slave_spiders))),
                check_subtype=MetaCheckSubType.TenDBClusterRoutingSpiderNotMatch,
            )
        )

    return bad


def _check_shard_routing(c: Cluster, routing_data: List[dict]) -> List[CheckResponse]:
    """
    检查后端分片的序号是否一致
    """
    bad = []

    # 从元数据获取所有分片信息
    metadata_master_shards: Set[int] = set()
    metadata_slave_shards: Set[int] = set()

    for shard in c.tendbclusterstorageset_set.all():
        shard_id = shard.shard_id
        # ejector 总是 master，receiver 总是 slave
        metadata_master_shards.add(shard_id)
        metadata_slave_shards.add(shard_id)

    # 从路由表提取分片序号
    routing_master_shards: Set[int] = set()
    routing_slave_shards: Set[int] = set()

    for row in routing_data:
        wrapper = row.get("Wrapper", "")
        server_name = row.get("Server_name", "")

        if wrapper == "mysql":
            # 提取 SPT{数字} 格式的分片序号
            shard_id = _extract_shard_id_from_server_name(server_name, "SPT")
            if shard_id >= 0:
                routing_master_shards.add(shard_id)
        elif wrapper == "mysql_slave":
            # 提取 SPT_SLAVE{数字} 格式的分片序号
            shard_id = _extract_shard_id_from_server_name(server_name, "SPT_SLAVE")
            if shard_id >= 0:
                routing_slave_shards.add(shard_id)

    # 检查 master 分片序号
    missing_master_shards = metadata_master_shards - routing_master_shards
    if missing_master_shards:
        bad.append(
            CheckResponse(
                msg=_("master 分片序号在路由中不存在: {}").format(", ".join(map(str, sorted(missing_master_shards)))),
                check_subtype=MetaCheckSubType.TenDBClusterRoutingShardNotMatch,
            )
        )

    extra_master_shards = routing_master_shards - metadata_master_shards
    if extra_master_shards:
        bad.append(
            CheckResponse(
                msg=_("路由中存在多余的 master 分片序号: {}").format(", ".join(map(str, sorted(extra_master_shards)))),
                check_subtype=MetaCheckSubType.TenDBClusterRoutingShardNotMatch,
            )
        )

    # 检查 slave 分片序号
    missing_slave_shards = metadata_slave_shards - routing_slave_shards
    if missing_slave_shards:
        bad.append(
            CheckResponse(
                msg=_("slave 分片序号在路由中不存在: {}").format(", ".join(map(str, sorted(missing_slave_shards)))),
                check_subtype=MetaCheckSubType.TenDBClusterRoutingShardNotMatch,
            )
        )

    extra_slave_shards = routing_slave_shards - metadata_slave_shards
    if extra_slave_shards:
        bad.append(
            CheckResponse(
                msg=_("路由中存在多余的 slave 分片序号: {}").format(", ".join(map(str, sorted(extra_slave_shards)))),
                check_subtype=MetaCheckSubType.TenDBClusterRoutingShardNotMatch,
            )
        )

    return bad


def _check_tdbctl_routing(c: Cluster, routing_data: List[dict]) -> List[CheckResponse]:
    """
    检查中控节点是否和元数据对得上
    中控只部署在 spider_master 节点上
    """
    bad = []

    # 从元数据获取所有 spider master 节点，计算中控地址
    metadata_tdbctl_addresses = set()
    for spider_master in c.proxyinstance_set.filter(
        tendbclusterspiderext__spider_role__in=[
            TenDBClusterSpiderRole.SPIDER_MASTER,
            TenDBClusterSpiderRole.SPIDER_MNT,
        ]
    ):
        tdbctl_address = f"{spider_master.machine.ip}{IP_PORT_DIVIDER}{spider_master.port + 1000}"
        metadata_tdbctl_addresses.add(tdbctl_address)

    # 从路由表提取 TDBCTL 记录
    routing_tdbctl_addresses = set()
    for row in routing_data:
        if row.get("Wrapper") == "TDBCTL":
            host = row.get("Host", "")
            port = row.get("Port", "")
            if host and port:
                tdbctl_address = f"{host}{IP_PORT_DIVIDER}{port}"
                routing_tdbctl_addresses.add(tdbctl_address)

    # 检查元数据中的中控地址是否都在路由中存在
    missing_tdbctl = metadata_tdbctl_addresses - routing_tdbctl_addresses
    if missing_tdbctl:
        bad.append(
            CheckResponse(
                msg=_("中控节点在路由中不存在: {}").format(", ".join(sorted(missing_tdbctl))),
                check_subtype=MetaCheckSubType.TenDBClusterRoutingTdbctlNotMatch,
            )
        )

    # 检查路由中是否有多余的中控
    extra_tdbctl = routing_tdbctl_addresses - metadata_tdbctl_addresses
    if extra_tdbctl:
        bad.append(
            CheckResponse(
                msg=_("路由中存在多余的中控节点: {}").format(", ".join(sorted(extra_tdbctl))),
                check_subtype=MetaCheckSubType.TenDBClusterRoutingTdbctlNotMatch,
            )
        )

    return bad


def test_cluster_routing_check(cluster_id: int) -> None:
    """
    测试函数：检查指定集群的路由信息
    方便测试使用，只需要传入 cluster_id 即可

    @param cluster_id: 集群ID
    @return: 检查结果列表
    """
    logger.info(gettext("开始检查集群路由信息，集群ID: {}").format(cluster_id))

    qs = Cluster.objects.filter(cluster_type=ClusterType.TenDBCluster).prefetch_related(
        "clusterentry_set__proxyinstance_set",
        "clusterentry_set__storageinstance_set",
        "proxyinstance_set__storageinstance",
        "storageinstance_set__as_receiver__ejector__cluster",
        "storageinstance_set__as_ejector__receiver__cluster",
        "storageinstance_set__cluster",
        "proxyinstance_set__cluster",
        "tendbclusterstorageset_set",
        "proxyinstance_set__tendbclusterspiderext",
    )

    try:
        cluster_obj = qs.get(id=cluster_id)
        logger.info(gettext("获取集群信息成功，集群域名: {}").format(cluster_obj.immute_domain))
    except Cluster.DoesNotExist:
        logger.error(gettext("集群不存在，集群ID: {}").format(cluster_id))
        return
    except Exception as e:
        logger.error(gettext("获取集群信息失败，集群ID: {}，错误: {}").format(cluster_id, str(e)))
        return

    reports = []
    r: MetaCheckReport
    for r in _cluster_routing_check(cluster_obj):
        reports.append(r)
        r.save()
        logger.debug(gettext("保存检查报告: {} - {}").format(r.subtype, r.msg))

    if reports:
        logger.warning(
            gettext("集群路由检查完成，发现 {} 个问题，集群ID: {}，集群域名: {}").format(len(reports), cluster_id, cluster_obj.immute_domain)
        )
    else:
        logger.info(gettext("集群路由检查完成，未发现问题，集群ID: {}，集群域名: {}").format(cluster_id, cluster_obj.immute_domain))

    return
