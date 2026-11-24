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
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from django.utils.translation import gettext as _

from backend.components import DRSApi
from backend.db_meta.enums import ClusterType, InstanceRole, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance, StorageInstanceTuple

logger = logging.getLogger("root")

SHOW_GLOBAL_VARIABLES = "SHOW GLOBAL VARIABLES"

# 单次 v2_mysql_rpc 携带的实例地址上限，避免 TenDBCluster 等大集群一次请求过大
DEFAULT_RPC_BATCH_SIZE = 50

# TenDBCluster 运行时配置采集/对比仅纳入 spider_master，不采集 spider_slave（及 slave 运维节点）
TENDBCLUSTER_SPIDER_ROLES_FOR_RUNTIME = (TenDBClusterSpiderRole.SPIDER_MASTER.value,)

# 数据盘挂载点前缀 /data、/data1 …（与 flow 中 disk_benchmark 等约定一致）
_DATA_MOUNT_PREFIX_RE = re.compile(r"^(/data[0-9]*)(/|$)")

# 安全变量名正则：只允许字母、数字与下划线
_SAFE_VARIABLE_NAME_RE = re.compile(r"^[a-zA-Z0-9_]+$")


class ClusterVariableQueryError(Exception):
    """采集集群运行时变量时发生的 DRS/校验异常。"""


def build_show_variables_sql(variable_names: Optional[Sequence[str]] = None) -> str:
    """构造 SHOW GLOBAL VARIABLES SQL；传入白名单时下推 WHERE Variable_name IN (...)。"""
    if not variable_names:
        return SHOW_GLOBAL_VARIABLES

    cleaned: List[str] = []
    seen = set()
    for raw_name in variable_names:
        name = (raw_name or "").strip()
        if not name:
            continue
        if not _SAFE_VARIABLE_NAME_RE.match(name):
            raise ClusterVariableQueryError(_("非法的 MySQL 变量名: {}").format(name))
        if name not in seen:
            seen.add(name)
            cleaned.append(name)

    if not cleaned:
        return SHOW_GLOBAL_VARIABLES

    in_clause = ",".join(f"'{name}'" for name in cleaned)
    return f"{SHOW_GLOBAL_VARIABLES} WHERE Variable_name IN ({in_clause})"


def extract_datadir_from_table(table_data: List[Dict]) -> str:
    """从 SHOW GLOBAL VARIABLES 原始结果中取出 datadir（过滤前读取）。"""
    for row in table_data:
        if (row.get("Variable_name") or "").lower() == "datadir":
            return (row.get("Value") or "").strip()
    return ""


def datadir_derived_fields(datadir_value: str) -> Dict[str, str]:
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


def _default_table_to_dict(table_data: List[Dict]) -> Dict[str, str]:
    variables: Dict[str, str] = {}
    for row in table_data:
        name = row.get("Variable_name", "")
        if name:
            variables[name] = row.get("Value", "")
    return variables


def _parse_drs_batch_results(
    batch_addrs: List[str],
    raw_drs_res: List[Dict],
    *,
    fail_fast: bool,
    variable_filter: Callable[[List[Dict]], Dict[str, str]],
    extract_datadir: bool,
    addr_to_variables: Dict[str, Dict[str, str]],
    addr_to_datadir_meta: Dict[str, Dict[str, str]],
    addr_errors: Dict[str, str],
) -> None:
    """解析单批 DRS 返回结果，强制按返回体 address 对齐避免乱序错位。"""
    if fail_fast and len(raw_drs_res) != len(batch_addrs):
        raise ClusterVariableQueryError(_("DRS 返回结果条数({})与请求地址数({})不一致").format(len(raw_drs_res), len(batch_addrs)))

    batch_addr_set = set(batch_addrs)
    for address_res in raw_drs_res:
        address = (address_res.get("address") or "").strip()
        if not address:
            if fail_fast:
                raise ClusterVariableQueryError(_("DRS 返回结果缺少 address 字段"))
            continue
        if address not in batch_addr_set:
            if fail_fast:
                raise ClusterVariableQueryError(_("DRS 返回未请求的地址 {}，本批请求: {}").format(address, batch_addrs))
            continue

        if address_res.get("error_msg"):
            if fail_fast:
                raise ClusterVariableQueryError(address_res["error_msg"])
            addr_errors[address] = str(address_res["error_msg"])
            continue

        cmd_results = address_res.get("cmd_results") or []
        if not cmd_results:
            err = _("DRS 返回空的 cmd_results")
            if fail_fast:
                raise ClusterVariableQueryError(_("{}: {}").format(address, err))
            addr_errors[address] = str(err)
            continue

        cmd_res = cmd_results[0]
        if cmd_res.get("error_msg"):
            err = _("{}: {}").format(address, cmd_res["error_msg"])
            if fail_fast:
                raise ClusterVariableQueryError(err)
            addr_errors[address] = str(cmd_res["error_msg"])
            continue

        table_data = cmd_res.get("table_data") or []
        if extract_datadir:
            addr_to_datadir_meta[address] = datadir_derived_fields(extract_datadir_from_table(table_data))
        addr_to_variables[address] = variable_filter(table_data)

    missing = [addr for addr in batch_addrs if addr not in addr_to_variables and addr not in addr_errors]
    if missing:
        if fail_fast:
            raise ClusterVariableQueryError(_("DRS 未返回下列地址的结果: {}").format(missing))
        for addr in missing:
            addr_errors[addr] = _("DRS 未返回该地址的查询结果")


def query_variables_for_addresses(
    bk_cloud_id: int,
    addresses: List[str],
    *,
    variable_names: Optional[Sequence[str]] = None,
    fail_fast: bool = True,
    variable_filter: Optional[Callable[[List[Dict]], Dict[str, str]]] = None,
    extract_datadir: bool = False,
    rpc_func: Optional[Callable[[Dict], List[Dict]]] = None,
    batch_size: int = DEFAULT_RPC_BATCH_SIZE,
) -> Tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, str]], Dict[str, str]]:
    """批量执行 SHOW GLOBAL VARIABLES，返回 (变量表, datadir 衍生信息, 失败地址错误信息)。

    按批调用 DRS 并强制按返回体 address 建索引；fail_fast=False 时单地址或单批失败不中断其余地址。
    """
    unique_addresses = list(dict.fromkeys(addresses or []))
    if not unique_addresses:
        return {}, {}, {}

    cmd = build_show_variables_sql(variable_names)
    filter_fn = variable_filter or _default_table_to_dict
    rpc_callable = rpc_func or DRSApi.v2_mysql_rpc

    addr_to_variables: Dict[str, Dict[str, str]] = {}
    addr_to_datadir_meta: Dict[str, Dict[str, str]] = {}
    addr_errors: Dict[str, str] = {}

    for batch_start in range(0, len(unique_addresses), batch_size):
        batch_addrs = unique_addresses[batch_start : batch_start + batch_size]
        try:
            raw_drs_res = rpc_callable({"addresses": batch_addrs, "cmds": [cmd], "bk_cloud_id": bk_cloud_id})
        except Exception as exc:  # noqa: BLE001
            if fail_fast:
                raise ClusterVariableQueryError(str(exc)) from exc
            for addr in batch_addrs:
                addr_errors[addr] = str(exc)
            continue

        _parse_drs_batch_results(
            batch_addrs=batch_addrs,
            raw_drs_res=raw_drs_res or [],
            fail_fast=fail_fast,
            variable_filter=filter_fn,
            extract_datadir=extract_datadir,
            addr_to_variables=addr_to_variables,
            addr_to_datadir_meta=addr_to_datadir_meta,
            addr_errors=addr_errors,
        )

    return addr_to_variables, addr_to_datadir_meta, addr_errors


def iter_tendbcluster_spider_proxies(cluster_obj: Cluster):
    """TenDBCluster 参与配置采集的 Spider：仅 spider_master。"""
    return (
        cluster_obj.proxyinstance_set.select_related("tendbclusterspiderext", "machine")
        .filter(tendbclusterspiderext__spider_role__in=TENDBCLUSTER_SPIDER_ROLES_FOR_RUNTIME)
        .all()
    )


def _collect_query_addresses(cluster_obj: Cluster, *, only_standby_slaves: bool = False) -> List[str]:
    """收集需要查询的实例地址：存储实例 + (TenDBCluster 的 spider_master)。

    only_standby_slaves=True 时，TenDBHA 仅采集 master 与 is_stand_by=True 的从库，跳过普通只读从库。
    """
    storage_instances = cluster_obj.storageinstance_set.all()
    if only_standby_slaves and cluster_obj.cluster_type == ClusterType.TenDBHA:
        addresses = [
            inst.ip_port
            for inst in storage_instances
            if inst.instance_role == InstanceRole.BACKEND_MASTER.value or bool(getattr(inst, "is_stand_by", False))
        ]
    else:
        addresses = [inst.ip_port for inst in storage_instances]
    if cluster_obj.cluster_type == ClusterType.TenDBCluster:
        addresses += [proxy.ip_port for proxy in iter_tendbcluster_spider_proxies(cluster_obj)]
    return addresses


def _build_storage_item(
    inst: StorageInstance,
    addr_to_variables: Dict[str, Dict[str, str]],
    addr_to_datadir_meta: Dict[str, Dict[str, str]],
    *,
    storage_filter: Optional[Callable[[Dict[str, str]], Dict[str, str]]] = None,
    extract_datadir: bool = False,
) -> Dict:
    address = inst.ip_port
    raw_vars = addr_to_variables.get(address)
    if raw_vars is None:
        variables = None
    else:
        variables = storage_filter(raw_vars) if storage_filter else dict(raw_vars)

    item = {
        "address": address,
        "instance_role": inst.instance_role,
        "machine_type": inst.machine_type,
        "version": inst.version or "",
        "is_stand_by": bool(getattr(inst, "is_stand_by", False)),
        "variables": variables,
    }
    if extract_datadir:
        meta = addr_to_datadir_meta.get(address, {"datadir": "", "data_dir_mount": ""})
        item.update(meta)
    return item


def _build_spider_item(
    proxy: ProxyInstance,
    addr_to_variables: Dict[str, Dict[str, str]],
    addr_to_datadir_meta: Dict[str, Dict[str, str]],
    *,
    spider_filter: Optional[Callable[[Dict[str, str]], Dict[str, str]]] = None,
    extract_datadir: bool = False,
) -> Dict:
    address = proxy.ip_port
    raw_vars = addr_to_variables.get(address)
    if raw_vars is None:
        variables = None
    else:
        variables = spider_filter(raw_vars) if spider_filter else dict(raw_vars)

    item = {
        "address": address,
        "instance_role": proxy.tendbclusterspiderext.spider_role,
        "machine_type": proxy.machine_type,
        "version": proxy.version or "",
        "variables": variables,
    }
    if extract_datadir:
        meta = addr_to_datadir_meta.get(address, {"datadir": "", "data_dir_mount": ""})
        item.update(meta)
    return item


def _tendbsingle_variables(
    cluster_obj: Cluster,
    addr_to_variables: Dict[str, Dict[str, str]],
    addr_to_datadir_meta: Dict[str, Dict[str, str]],
    *,
    storage_filter: Optional[Callable[[Dict[str, str]], Dict[str, str]]] = None,
    extract_datadir: bool = False,
) -> Dict:
    master = cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.ORPHAN).order_by("id").first()
    return {
        "master": (
            _build_storage_item(
                master,
                addr_to_variables,
                addr_to_datadir_meta,
                storage_filter=storage_filter,
                extract_datadir=extract_datadir,
            )
            if master
            else None
        ),
        "slaves": [],
    }


def _tendbha_variables(
    cluster_obj: Cluster,
    addr_to_variables: Dict[str, Dict[str, str]],
    addr_to_datadir_meta: Dict[str, Dict[str, str]],
    *,
    db_alias: Optional[str] = None,
    storage_filter: Optional[Callable[[Dict[str, str]], Dict[str, str]]] = None,
    extract_datadir: bool = False,
) -> Dict:
    tuple_qs = StorageInstanceTuple.objects.using(db_alias) if db_alias else StorageInstanceTuple.objects
    tuples = list(
        tuple_qs.filter(ejector__cluster=cluster_obj)
        .select_related("ejector", "receiver")
        .order_by("ejector_id", "receiver_id")
    )
    if not tuples:
        logger.warning(_("TenDBHA 集群 id={} 无 StorageInstanceTuple 记录，返回空 master/slaves").format(cluster_obj.id))
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
        if tp.ejector_id != canonical_ejector_id or tp.receiver_id in seen_receiver_ids:
            continue
        seen_receiver_ids.add(tp.receiver_id)
        slaves.append(tp.receiver)

    return {
        "master": _build_storage_item(
            master_inst,
            addr_to_variables,
            addr_to_datadir_meta,
            storage_filter=storage_filter,
            extract_datadir=extract_datadir,
        ),
        "slaves": [
            _build_storage_item(
                slave,
                addr_to_variables,
                addr_to_datadir_meta,
                storage_filter=storage_filter,
                extract_datadir=extract_datadir,
            )
            for slave in slaves
        ],
    }


def _tendbcluster_variables(
    cluster_obj: Cluster,
    addr_to_variables: Dict[str, Dict[str, str]],
    addr_to_datadir_meta: Dict[str, Dict[str, str]],
    *,
    storage_filter: Optional[Callable[[Dict[str, str]], Dict[str, str]]] = None,
    spider_filter: Optional[Callable[[Dict[str, str]], Dict[str, str]]] = None,
    extract_datadir: bool = False,
) -> Dict:
    spiders = [
        _build_spider_item(
            proxy,
            addr_to_variables,
            addr_to_datadir_meta,
            spider_filter=spider_filter,
            extract_datadir=extract_datadir,
        )
        for proxy in iter_tendbcluster_spider_proxies(cluster_obj)
    ]

    shards: Dict[str, Dict] = {}
    for shard in cluster_obj.tendbclusterstorageset_set.select_related(
        "storage_instance_tuple__ejector__machine",
        "storage_instance_tuple__receiver__machine",
    ).order_by("shard_id"):
        tp = shard.storage_instance_tuple
        shards[str(shard.shard_id)] = {
            "master": _build_storage_item(
                tp.ejector,
                addr_to_variables,
                addr_to_datadir_meta,
                storage_filter=storage_filter,
                extract_datadir=extract_datadir,
            ),
            "slave": _build_storage_item(
                tp.receiver,
                addr_to_variables,
                addr_to_datadir_meta,
                storage_filter=storage_filter,
                extract_datadir=extract_datadir,
            ),
        }

    return {"spiders": spiders, "shards": shards}


def collect_cluster_runtime_variables(
    cluster_obj: Cluster,
    *,
    db_alias: Optional[str] = None,
    variable_names: Optional[Sequence[str]] = None,
    fail_fast: bool = True,
    variable_filter: Optional[Callable[[List[Dict]], Dict[str, str]]] = None,
    storage_filter: Optional[Callable[[Dict[str, str]], Dict[str, str]]] = None,
    spider_filter: Optional[Callable[[Dict[str, str]], Dict[str, str]]] = None,
    extract_datadir: bool = False,
    only_standby_slaves: bool = False,
    rpc_func: Optional[Callable[[Dict], List[Dict]]] = None,
) -> Dict:
    """采集集群各角色实例的运行时变量并按拓扑结构组装返回。

    fail_fast=False 时，返回体中额外包含 errors: Dict[address, error_msg]，且失联节点 variables 为 None。
    """
    addr_to_variables, addr_to_datadir_meta, addr_errors = query_variables_for_addresses(
        bk_cloud_id=cluster_obj.bk_cloud_id,
        addresses=_collect_query_addresses(cluster_obj, only_standby_slaves=only_standby_slaves),
        variable_names=variable_names,
        fail_fast=fail_fast,
        variable_filter=variable_filter,
        extract_datadir=extract_datadir,
        rpc_func=rpc_func,
    )

    if cluster_obj.cluster_type == ClusterType.TenDBSingle:
        result = _tendbsingle_variables(
            cluster_obj,
            addr_to_variables,
            addr_to_datadir_meta,
            storage_filter=storage_filter,
            extract_datadir=extract_datadir,
        )
    elif cluster_obj.cluster_type == ClusterType.TenDBHA:
        result = _tendbha_variables(
            cluster_obj,
            addr_to_variables,
            addr_to_datadir_meta,
            db_alias=db_alias,
            storage_filter=storage_filter,
            extract_datadir=extract_datadir,
        )
    else:
        result = _tendbcluster_variables(
            cluster_obj,
            addr_to_variables,
            addr_to_datadir_meta,
            storage_filter=storage_filter,
            spider_filter=spider_filter,
            extract_datadir=extract_datadir,
        )

    if not fail_fast:
        result["errors"] = addr_errors
    return result
