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
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from backend.components import DRSApi
from backend.components.dbconfig.constants import ConfFile
from backend.db_meta.enums import ClusterType, InstanceRole, InstanceStatus
from backend.db_meta.models import Cluster
from backend.utils.batch_request import request_multi_thread

logger = logging.getLogger("root")

"""
集群运行时配置（infodba_schema.local_config）
- 由 mysql-monitor 的 config-report 采集各实例本机的工具配置文件（dbbackup/checksum/rotatebinlog...），
  按一层 key 展开为 JSON 写入每个实例自己的 infodba_schema.local_config
- 这里通过 DRS 查询集群内所有实例的 local_config，与 dbconfig 中的集群级配置做比对
"""

# 运行时配置比对标记
FLAG_DIFF_UNKNOWN = -1  # 未取得有效运行时配置
FLAG_DIFF_SAME = 0  # 运行时与配置一致
FLAG_DIFF_DIFFERENT = 1  # 运行时与配置不一致

# local_config 中脱敏后的值，无法比对
MASKED_VALUE = "******"

# dbconfig conf_file(version) -> local_config.conf_type
# dbbackup.options 没有具体的 local_config 实体，暂不处理
CONF_FILE_LOCAL_CONF_TYPE = {
    ConfFile.DBBACKUP_INI.value: "dbbackup",
    ConfFile.BINLOG_ROTATE.value: "rotatebinlog",
    ConfFile.CHECKSUM.value: "checksum",
    ConfFile.ITEMS_CONFIG.value: "mysql-monitor",
}

# 支持运行时配置的集群类型 -> 需要查询的实例角色
CLUSTER_RUNTIME_STORAGE_ROLES = {
    ClusterType.TenDBSingle: [InstanceRole.ORPHAN],
    ClusterType.TenDBHA: [InstanceRole.BACKEND_MASTER, InstanceRole.BACKEND_SLAVE],
    ClusterType.TenDBCluster: [InstanceRole.REMOTE_MASTER, InstanceRole.REMOTE_SLAVE],
}
# 需要额外查询接入层（spider）的集群类型
CLUSTER_RUNTIME_WITH_PROXY = [ClusterType.TenDBCluster]

# 查询实例本机的 local_config
# 主机级配置（如 rotatebinlog）port=0，实例级配置 port=实例端口，所以 port 匹配 (0, 实例端口)
# 这里不会出现注入，所以参数都是从元数据查出的
QUERY_LOCAL_CONFIG_SQL = (
    "SELECT host, port, conf_type, conf_file, config_value FROM infodba_schema.local_config "
    "WHERE host = '{host}' AND port IN (0, {port}) AND conf_type = '{conf_type}'"
)

# DRS 查询超时时间（秒），页面接口要求快速返回，超时即视为未取得运行时配置（flag_difference=-1）
DRS_QUERY_TIMEOUT_SECONDS = 2


class ClusterRuntimeConfigError(Exception):
    pass


def support_cluster_runtime(meta_cluster_type: str, conf_file: str) -> bool:
    return meta_cluster_type in CLUSTER_RUNTIME_STORAGE_ROLES and conf_file in CONF_FILE_LOCAL_CONF_TYPE


def _flatten(prefix: str, value: Any, result: Dict[str, Any], max_depth: int = 1):
    """
    local_config 的 config_value 在采集端（Go FlattenOneLevel）已经展开了一层 key，
    这里默认再向下展开一级（max_depth 可调），同时保留每一级的原值
    例如 {"Public.EncryptOpt": {"EncryptCmd": "x", "Nested": {"k": "v"}}} 默认会得到:
      Public.EncryptOpt            -> {"EncryptCmd": "x", "Nested": {"k": "v"}}
      Public.EncryptOpt.EncryptCmd -> "x"
      Public.EncryptOpt.Nested     -> {"k": "v"}    # 再深一层默认不展开
    这样 dbconfig 中定义的 MAP 配置名（如 pt_checksum.args）和展开后的配置名（如 pt_checksum.args.run-time）都能匹配上
    """
    result[prefix] = value
    if max_depth <= 0 or not isinstance(value, dict):
        return
    for k, v in value.items():
        _flatten(f"{prefix}.{k}", v, result, max_depth - 1)


def _parse_config_value(config_value: str) -> Dict[str, Any]:
    data = json.loads(config_value)
    if not isinstance(data, dict):
        raise ClusterRuntimeConfigError(f"invalid local_config.config_value: {config_value[:100]}")
    result: Dict[str, Any] = {}
    for k, v in data.items():
        _flatten(k, v, result)
    return result


def _cluster_instance_addresses(cluster: Cluster) -> List[Tuple[str, int]]:
    """获取集群需要查询运行时配置的实例 (ip, port) 列表，仅取 running 状态的实例"""
    roles = CLUSTER_RUNTIME_STORAGE_ROLES.get(cluster.cluster_type, [])
    instances = [
        (inst.machine.ip, inst.port)
        for inst in cluster.storageinstance_set.select_related("machine").filter(
            instance_role__in=roles, status=InstanceStatus.RUNNING
        )
    ]
    if cluster.cluster_type in CLUSTER_RUNTIME_WITH_PROXY:
        instances.extend(
            [
                (inst.machine.ip, inst.port)
                for inst in cluster.proxyinstance_set.select_related("machine").filter(status=InstanceStatus.RUNNING)
            ]
        )
    return sorted(set(instances))


def query_cluster_runtime_config(cluster: Cluster, conf_file: str) -> List[Dict[str, Any]]:
    """
    查询集群所有实例的运行时配置，SQL 按 host/port/conf_type 过滤，逐实例并发查询
    返回: [{"address": "ip:port", "config": {conf_name: raw_value}}, ...]
    任何实例查询失败都抛异常；实例上没有对应 conf_type 的记录则跳过
    """
    conf_type = CONF_FILE_LOCAL_CONF_TYPE[conf_file]
    instances = _cluster_instance_addresses(cluster)
    if not instances:
        raise ClusterRuntimeConfigError(f"cluster {cluster.immute_domain} has no instance to query")

    params_list = [
        {"bk_cloud_id": cluster.bk_cloud_id, "ip": ip, "port": port, "conf_type": conf_type} for ip, port in instances
    ]
    # 并发查询所有实例，每个实例的请求各自带 host/port（local_config 只存本机数据）
    results = request_multi_thread(func=_query_instance_runtime_config, params_list=params_list, get_data=lambda x: x)
    runtime_configs = [r for r in results if r]
    if not runtime_configs:
        raise ClusterRuntimeConfigError(f"no local_config found for conf_type: {conf_type}")
    return runtime_configs


def _query_instance_runtime_config(bk_cloud_id: int, ip: str, port: int, conf_type: str) -> Optional[Dict[str, Any]]:
    """
    查询单个实例的 local_config，实例上没有对应记录时返回 None
    """
    address = f"{ip}:{port}"
    sql = QUERY_LOCAL_CONFIG_SQL.format(host=ip, port=port, conf_type=conf_type)

    rpc_results = DRSApi.v2_short_rpc(
        {"bk_cloud_id": bk_cloud_id, "addresses": [address], "cmds": [sql], "force": False},
        timeout=DRS_QUERY_TIMEOUT_SECONDS,
    )
    if not rpc_results:
        raise ClusterRuntimeConfigError(f"{address}: empty drs result")

    res = rpc_results[0]
    address = res.get("address") or address
    if res.get("error_msg"):
        raise ClusterRuntimeConfigError(f"{address}: {res['error_msg']}")
    cmd_results = res.get("cmd_results") or []
    if not cmd_results or cmd_results[0].get("error_msg"):
        raise ClusterRuntimeConfigError(f"{address}: {cmd_results[0].get('error_msg') if cmd_results else ''}")

    rows = cmd_results[0].get("table_data") or []
    if not rows:
        return None
    # 优先取实例级配置（port != 0），主机级配置（如 rotatebinlog，port=0）兜底
    rows.sort(key=lambda r: int(r.get("port") or 0) == 0)
    return {"address": address, "config": _parse_config_value(rows[0]["config_value"])}


def _scalar_to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def runtime_value_to_str(value: Any) -> str:
    """运行时值转化为展示的字符串"""
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, list):
        if all(not isinstance(v, (dict, list)) for v in value):
            return ",".join(_scalar_to_str(v) for v in value)
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return _scalar_to_str(value)


# 布尔类文本，仅这类值比较时忽略大小写（如 True/true、ON/on）
BOOL_TEXTS = {"true", "false", "yes", "no", "on", "off", "1", "0"}


def _scalar_equal(conf_value: Any, runtime_value: Any) -> bool:
    if isinstance(runtime_value, str) and runtime_value == MASKED_VALUE:
        return True
    left, right = _scalar_to_str(conf_value).strip(), _scalar_to_str(runtime_value).strip()
    if left == right:
        return True
    # 仅布尔类值（true/false/yes/no/on/off/1/0）忽略大小写比较，其它标量保持精确比较
    if left.lower() in BOOL_TEXTS and right.lower() in BOOL_TEXTS:
        return left.lower() == right.lower()
    try:
        return float(left) == float(right)
    except (TypeError, ValueError):
        return False


def _deep_equal(conf_value: Any, runtime_value: Any) -> bool:
    if isinstance(runtime_value, dict):
        if not isinstance(conf_value, dict) or set(conf_value.keys()) != set(runtime_value.keys()):
            return False
        return all(_deep_equal(conf_value[k], runtime_value[k]) for k in runtime_value)
    if isinstance(runtime_value, list):
        if not isinstance(conf_value, list) or len(conf_value) != len(runtime_value):
            return False
        return all(_deep_equal(c, r) for c, r in zip(conf_value, runtime_value))
    if isinstance(conf_value, (dict, list)):
        return False
    return _scalar_equal(conf_value, runtime_value)


def conf_value_equal(conf_value: str, runtime_value: Any) -> bool:
    """比较 dbconfig 中的配置值（字符串）与运行时值（json 类型）是否一致"""
    conf_value = conf_value if conf_value is not None else ""
    if isinstance(runtime_value, (dict, list)):
        text = conf_value.strip()
        try:
            parsed = json.loads(text) if text else ([] if isinstance(runtime_value, list) else {})
        except ValueError:
            # LIST 类型在 dbconfig 中可能是逗号分隔的字符串
            if not isinstance(runtime_value, list):
                return False
            parsed = [v.strip() for v in text.split(",") if v.strip()]
        if isinstance(runtime_value, list) and isinstance(parsed, str):
            parsed = [v.strip() for v in parsed.split(",") if v.strip()]
        return _deep_equal(parsed, runtime_value)
    return _scalar_equal(conf_value, runtime_value)


def patch_conf_items_runtime(
    conf_items: List[Dict[str, Any]], runtime_configs: Optional[List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """
    为配置项补充运行时配置
    - conf_value_runtime: 运行时值，多实例不一致时去重后以 , 分隔
    - flag_difference: -1 未取得有效运行时配置；0 一致；1 不一致
    """
    for item in conf_items:
        item["conf_value_runtime"] = None
        item["flag_difference"] = FLAG_DIFF_UNKNOWN
    if not runtime_configs:
        return conf_items

    name__runtime_values: Dict[str, List[Any]] = defaultdict(list)
    for runtime in runtime_configs:
        for conf_name, value in runtime["config"].items():
            name__runtime_values[conf_name].append(value)

    for item in conf_items:
        conf_name = item.get("conf_name")
        # 配置名取交集，只有两边都存在的配置才补充运行时值
        if conf_name not in name__runtime_values:
            continue
        values = name__runtime_values[conf_name]
        display_values: List[str] = []
        for value in values:
            value_str = runtime_value_to_str(value)
            if value_str not in display_values:
                display_values.append(value_str)
        item["conf_value_runtime"] = ",".join(display_values)

        conf_value = item.get("conf_value")
        # 模板变量 {{xxx}} 由下发时渲染，无法比对
        if isinstance(conf_value, str) and "{{" in conf_value:
            item["flag_difference"] = FLAG_DIFF_SAME
            continue
        is_diff = any(not conf_value_equal(conf_value, value) for value in values)
        item["flag_difference"] = FLAG_DIFF_DIFFERENT if is_diff else FLAG_DIFF_SAME

    return conf_items
