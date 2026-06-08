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
import os
import re
from typing import Dict, List, Tuple

from django.utils.translation import gettext as _

from backend.components import DRSApi
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance, StorageInstanceTuple
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException

logger = logging.getLogger("root")

SHOW_GLOBAL_VARIABLES = "SHOW GLOBAL VARIABLES"

# 单次 v2_mysql_rpc 携带的实例地址上限，避免 TenDBCluster 等大集群一次请求过大
_SHOW_GLOBAL_VARIABLES_RPC_BATCH_SIZE = 50

# 目录/路径/文件类变量名后缀(小写匹配), 这类配置不属于核心关键参数, 过滤掉
_PATH_LIKE_NAME_SUFFIXES = ("dir", "_file", "_path", "_home")
# 目录/路径/文件类变量名关键字(小写匹配)
_PATH_LIKE_NAME_KEYWORDS = ("socket", "secure_file_priv", "log_error", "character_sets_dir")

# 数据盘挂载点前缀 /data、/data1 …（与 flow 中 disk_benchmark 等约定一致）
_DATA_MOUNT_PREFIX_RE = re.compile(r"^(/data[0-9]*)(/|$)")


def _is_path_like_variable(name: str, value: str) -> bool:
    """判断变量是否为目录/路径/文件类配置(需被过滤)。"""
    lname = name.lower()
    if lname.endswith(_PATH_LIKE_NAME_SUFFIXES):
        return True
    if any(keyword in lname for keyword in _PATH_LIKE_NAME_KEYWORDS):
        return True
    # 值为绝对路径的变量(如 datadir、log_bin、relay_log、slow_query_log_file、ssl_* 等)一并过滤
    if value and value.startswith("/"):
        return True
    return False


def _filter_variables(table_data: List[Dict]) -> Dict[str, str]:
    """黑名单过滤: 去除目录/路径/文件类配置, 仅保留核心关键参数。"""
    variables = {}
    for row in table_data:
        name = row.get("Variable_name", "")
        value = row.get("Value", "")
        if not name:
            continue
        if _is_path_like_variable(name, value):
            continue
        variables[name] = value
    return variables


def _extract_datadir_from_table(table_data: List[Dict]) -> str:
    """从 SHOW GLOBAL VARIABLES 原始结果中取出 datadir（过滤前读取）。"""
    for row in table_data:
        if (row.get("Variable_name") or "").lower() == "datadir":
            return (row.get("Value") or "").strip()
    return ""


def _datadir_derived_fields(datadir_value: str) -> Dict[str, str]:
    """
    由 MySQL datadir 推导展示字段:
    - datadir: 原始值
    - data_dir_mount: 符合 /data、/data1 等约定的数据盘挂载点前缀；无法匹配时为空
    """
    raw = (datadir_value or "").strip()
    if not raw:
        return {"datadir": "", "data_dir_mount": ""}

    mount_match = _DATA_MOUNT_PREFIX_RE.match(os.path.normpath(raw))
    data_dir_mount = mount_match.group(1) if mount_match else ""

    return {"datadir": raw, "data_dir_mount": data_dir_mount}


def _query_variables_for_addresses(
    bk_cloud_id: int,
    addresses: List[str],
) -> Tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, str]]]:
    """批量执行 SHOW GLOBAL VARIABLES, 返回 (过滤后变量表, 各地址 datadir 衍生字段)。

    按批调用 DRS，避免单请求携带过多地址导致超时或响应过大。
    """
    if not addresses:
        return {}, {}

    addr_to_variables: Dict[str, Dict[str, str]] = {}
    addr_to_datadir_meta: Dict[str, Dict[str, str]] = {}

    for batch_start in range(0, len(addresses), _SHOW_GLOBAL_VARIABLES_RPC_BATCH_SIZE):
        batch_addrs = addresses[batch_start : batch_start + _SHOW_GLOBAL_VARIABLES_RPC_BATCH_SIZE]
        raw_drs_res = DRSApi.v2_mysql_rpc(
            {"addresses": batch_addrs, "cmds": [SHOW_GLOBAL_VARIABLES], "bk_cloud_id": bk_cloud_id}
        )
        if len(raw_drs_res) != len(batch_addrs):
            raise DBMMcpBaseException(msg=_("DRS 返回结果条数({})与请求地址数({})不一致").format(len(raw_drs_res), len(batch_addrs)))

        for address, address_res in zip(batch_addrs, raw_drs_res):
            if address_res["error_msg"]:
                raise DBMMcpBaseException(msg=address_res["error_msg"])
            cmd_res = address_res["cmd_results"][0]
            if cmd_res["error_msg"]:
                raise DBMMcpBaseException(msg=_("{}: {}").format(address, cmd_res["error_msg"]))
            table_data = cmd_res["table_data"]
            addr_to_datadir_meta[address] = _datadir_derived_fields(_extract_datadir_from_table(table_data))
            addr_to_variables[address] = _filter_variables(table_data)

    return addr_to_variables, addr_to_datadir_meta


def _collect_query_addresses(cluster_obj: Cluster) -> List[str]:
    """收集需要查询的实例地址: 所有存储实例 + (TenDBCluster 的 spider 接入层)。"""
    addresses = [inst.ip_port for inst in cluster_obj.storageinstance_set.all()]
    if cluster_obj.cluster_type == ClusterType.TenDBCluster:
        addresses += [proxy.ip_port for proxy in cluster_obj.proxyinstance_set.all()]
    return addresses


def _build_storage_item(
    inst: StorageInstance,
    addr_to_variables: Dict[str, Dict[str, str]],
    addr_to_datadir_meta: Dict[str, Dict[str, str]],
) -> Dict:
    address = inst.ip_port
    meta = addr_to_datadir_meta.get(address, {"datadir": "", "data_dir_mount": ""})
    return {
        "address": address,
        "instance_role": inst.instance_role,
        "machine_type": inst.machine_type,
        "version": inst.version or "",
        **meta,
        "variables": addr_to_variables.get(address, {}),
    }


def _build_spider_item(
    proxy: ProxyInstance,
    addr_to_variables: Dict[str, Dict[str, str]],
    addr_to_datadir_meta: Dict[str, Dict[str, str]],
) -> Dict:
    address = proxy.ip_port
    meta = addr_to_datadir_meta.get(address, {"datadir": "", "data_dir_mount": ""})
    return {
        "address": address,
        "instance_role": proxy.tendbclusterspiderext.spider_role,
        "machine_type": proxy.machine_type,
        "version": proxy.version or "",
        **meta,
        "variables": addr_to_variables.get(address, {}),
    }


def _tendbsingle_variables(
    cluster_obj: Cluster,
    addr_to_variables: Dict[str, Dict[str, str]],
    addr_to_datadir_meta: Dict[str, Dict[str, str]],
) -> Dict:
    """TenDBSingle：单实例集群，无独立从库侧，不查询 StorageInstanceTuple。

    仅取 `instance_role=ORPHAN` 的存储实例作为 `master`（按 id 排序后取首个，通常仅一条）；
    `slaves` 恒为空列表，避免为不存在的复制组做多余元数据访问。
    """
    master = cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.ORPHAN).order_by("id").first()

    return {
        "master": _build_storage_item(master, addr_to_variables, addr_to_datadir_meta) if master else None,
        "slaves": [],
    }


def _tendbha_variables(
    cluster_obj: Cluster,
    addr_to_variables: Dict[str, Dict[str, str]],
    addr_to_datadir_meta: Dict[str, Dict[str, str]],
) -> Dict:
    tuples = list(
        StorageInstanceTuple.objects.filter(ejector__cluster=cluster_obj)
        .select_related("ejector", "receiver")
        .order_by("ejector_id", "receiver_id")
    )
    if not tuples:
        logger.warning(
            _("TenDBHA 集群 id={} 无 StorageInstanceTuple 记录，cluster_runtime_variables 返回空 master/slaves").format(
                cluster_obj.id
            )
        )
        return {"master": None, "slaves": []}

    ejector_ids = {tp.ejector_id for tp in tuples}
    if len(ejector_ids) == 1:
        master_inst = tuples[0].ejector
        canonical_ejector_id = master_inst.id
    else:
        canonical_ejector_id = min(ejector_ids)
        master_inst = next(tp.ejector for tp in tuples if tp.ejector_id == canonical_ejector_id)
        logger.warning(
            _(
                "TenDBHA 集群 id={} 的 StorageInstanceTuple 出现多个不同 ejector_id={}，"
                "仅采用 ejector_id={} 的复制组构造扁平化 master/slaves，其余 tuple 已从 slaves 聚合中排除"
            ).format(cluster_obj.id, sorted(ejector_ids), canonical_ejector_id)
        )

    seen_receiver_ids = set()
    slaves: List[StorageInstance] = []
    for tp in tuples:
        if tp.ejector_id != canonical_ejector_id:
            continue
        if tp.receiver_id in seen_receiver_ids:
            continue
        seen_receiver_ids.add(tp.receiver_id)
        slaves.append(tp.receiver)

    return {
        "master": _build_storage_item(master_inst, addr_to_variables, addr_to_datadir_meta),
        "slaves": [_build_storage_item(slave, addr_to_variables, addr_to_datadir_meta) for slave in slaves],
    }


def _tendbcluster_variables(
    cluster_obj: Cluster,
    addr_to_variables: Dict[str, Dict[str, str]],
    addr_to_datadir_meta: Dict[str, Dict[str, str]],
) -> Dict:
    spiders = [
        _build_spider_item(proxy, addr_to_variables, addr_to_datadir_meta)
        for proxy in cluster_obj.proxyinstance_set.select_related("tendbclusterspiderext", "machine").all()
    ]

    shards: Dict[str, Dict] = {}
    for shard in cluster_obj.tendbclusterstorageset_set.select_related(
        "storage_instance_tuple__ejector__machine",
        "storage_instance_tuple__receiver__machine",
    ).order_by("shard_id"):
        tp = shard.storage_instance_tuple
        shards[str(shard.shard_id)] = {
            "master": _build_storage_item(tp.ejector, addr_to_variables, addr_to_datadir_meta),
            "slave": _build_storage_item(tp.receiver, addr_to_variables, addr_to_datadir_meta),
        }

    return {"spiders": spiders, "shards": shards}


def cluster_runtime_variables(cluster_obj: Cluster) -> Dict:
    """查询集群所有角色实例的运行时核心配置(已过滤目录/路径类), 带版本信息; 另返回 datadir 及推导的 data_dir_mount。"""
    addr_to_variables, addr_to_datadir_meta = _query_variables_for_addresses(
        bk_cloud_id=cluster_obj.bk_cloud_id, addresses=_collect_query_addresses(cluster_obj)
    )

    if cluster_obj.cluster_type == ClusterType.TenDBSingle:
        return _tendbsingle_variables(cluster_obj, addr_to_variables, addr_to_datadir_meta)
    elif cluster_obj.cluster_type == ClusterType.TenDBHA:
        return _tendbha_variables(cluster_obj, addr_to_variables, addr_to_datadir_meta)
    else:
        return _tendbcluster_variables(cluster_obj, addr_to_variables, addr_to_datadir_meta)
