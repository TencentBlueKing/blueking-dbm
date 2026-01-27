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
import ast
import json
from typing import Any, Union

from django.utils.translation import gettext_lazy as _


class SchemaExtractionError(Exception):
    """Schema 数据抽取异常"""

    def __init__(self, message: str, path: str = "", details: dict = None):
        self.message = message
        self.path = path  # 发生错误的数据路径
        self.details = details or {}
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        msg = self.message
        if self.path:
            msg = f"[{self.path}] {msg}"
        if self.details:
            msg = f"{msg} | Details: {self.details}"
        return msg


def _try_parse_json_string(value: str) -> Any:
    """
    尝试将字符串解析为 JSON 对象

    Args:
        value: 可能是 JSON 字符串的值

    Returns:
        解析后的对象，如果解析失败则返回原值
    """
    if not isinstance(value, str):
        return value

    # 检查是否看起来像 JSON 对象或数组
    stripped = value.strip()
    if not (stripped.startswith("{") or stripped.startswith("[")):
        return value

    # 方法1: 先尝试标准 JSON 解析
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        pass

    # 方法2: 尝试用 ast.literal_eval 解析 Python 风格的字面量（如 True/False, 单引号等）
    try:
        return ast.literal_eval(stripped)
    except (ValueError, SyntaxError):
        pass

    # 方法3: 简单替换单引号后再尝试
    try:
        fixed = stripped.replace("'", '"')
        return json.loads(fixed)
    except (json.JSONDecodeError, ValueError):
        return value


def _is_spec_object(obj: dict) -> bool:
    """
    判断一个对象是否是 spec 规格详情对象
    spec 对象通常包含: id, cpu, mem, name, device_class, storage_spec 等字段

    Args:
        obj: 待判断的对象

    Returns:
        是否是 spec 对象
    """
    if not isinstance(obj, dict):
        return False

    # spec 对象的特征字段
    spec_indicators = {"cpu", "mem", "storage_spec", "device_class", "qps"}
    # 必须有 name 或 spec_name 字段，且至少包含 2 个特征字段
    has_name = "name" in obj or "spec_name" in obj
    if not has_name:
        return False

    indicator_count = sum(1 for field in spec_indicators if field in obj)
    return indicator_count >= 2


def _is_backupinfo_object(obj: dict) -> bool:
    """
    判断一个对象是否是 backupinfo 备份详情对象
    backupinfo 对象通常包含: backup_id, backup_time, backup_host, backup_port, file_list 等字段

    Args:
        obj: 待判断的对象

    Returns:
        是否是 backupinfo 对象
    """
    if not isinstance(obj, dict):
        return False

    # backupinfo 对象的必要字段
    if "backup_id" not in obj:
        return False

    # backupinfo 对象的特征字段（至少包含 2 个特征字段）
    backupinfo_indicators = {
        "backup_time",
        "backup_host",
        "backup_port",
        "file_list",
        "backup_type",
        "backup_tool",
        "cluster_id",
    }
    indicator_count = sum(1 for field in backupinfo_indicators if field in obj)
    return indicator_count >= 2


def _get_cluster_domain(cluster_id: Any, cluster_map: dict) -> str:
    """
    从 cluster_map 中获取指定 cluster_id 的域名

    Args:
        cluster_id: 集群ID
        cluster_map: 集群信息映射

    Returns:
        集群域名，未找到则返回 None
    """
    # cluster_map 的 key 可能是字符串或整数
    cluster_info = cluster_map.get(str(cluster_id)) or cluster_map.get(cluster_id)
    if cluster_info and isinstance(cluster_info, dict):
        return cluster_info.get("immute_domain")
    return None


def _enrich_cluster_domain(data: Any, cluster_map: dict) -> Any:
    """
    递归遍历提取结果，为包含 cluster_id/cluster_ids/target_cluster_id 的对象追加对应的域名字段

    Args:
        data: 提取后的结果数据
        cluster_map: 原始数据中的 clusters 映射 {cluster_id: {immute_domain: ...}}

    Returns:
        增强后的结果数据
    """
    # 先尝试解析字符串化的 JSON
    if isinstance(data, str):
        parsed = _try_parse_json_string(data)
        if parsed != data:  # 解析成功
            return _enrich_cluster_domain(parsed, cluster_map)
        return data

    if isinstance(data, dict):
        # 情况1: 检查是否包含 cluster_id（单个ID）
        if "cluster_id" in data:
            cluster_id = data["cluster_id"]
            domain = _get_cluster_domain(cluster_id, cluster_map)
            if domain:
                data["cluster_domain"] = domain

        # 情况2: 检查是否包含 cluster_ids（ID列表）
        if "cluster_ids" in data:
            cluster_ids = data["cluster_ids"]
            if isinstance(cluster_ids, list):
                # 保持与 cluster_ids 顺序对应，找不到的用 None 占位
                domains = []
                for cid in cluster_ids:
                    domain = _get_cluster_domain(cid, cluster_map)
                    domains.append(domain)  # 即使是 None 也追加，保持索引对应
                # 只有当至少有一个有效域名时才添加 cluster_domains
                if any(d is not None for d in domains):
                    data["cluster_domains"] = domains

        # 情况3: 检查是否包含 target_cluster_id（目标集群ID，常用于回档等场景）
        if "target_cluster_id" in data:
            target_cluster_id = data["target_cluster_id"]
            domain = _get_cluster_domain(target_cluster_id, cluster_map)
            if domain:
                data["target_cluster_domain"] = domain

        # 递归处理所有值（排除刚添加的域名字段，避免无效递归）
        for key, value in list(data.items()):
            if key not in ("cluster_domain", "cluster_domains", "target_cluster_domain"):
                data[key] = _enrich_cluster_domain(value, cluster_map)

    elif isinstance(data, list):
        # 递归处理数组中的每个元素
        for idx, item in enumerate(data):
            data[idx] = _enrich_cluster_domain(item, cluster_map)

    return data


def _simplify_spec_objects(data: Any) -> Any:
    """
    递归遍历数据，将 spec 规格详情对象简化为只保留 name

    场景1: nodes.hot[].spec -> 从完整对象简化为 spec.name
    场景2: resource_spec.hot -> 保留 spec_name, count 等关键字段，删除 cpu, mem 等详情
    场景3: 字符串化的 JSON 也会被解析和简化

    Args:
        data: 待处理的数据

    Returns:
        简化后的数据
    """
    # 先尝试解析字符串化的 JSON
    if isinstance(data, str):
        parsed = _try_parse_json_string(data)
        if parsed != data:  # 解析成功
            return _simplify_spec_objects(parsed)
        return data

    if isinstance(data, dict):
        # 检查当前对象是否是完整的 spec 详情对象
        if _is_spec_object(data):
            # 只保留 name 或 spec_name
            return data.get("name") or data.get("spec_name", "")

        # 检查是否是 resource_spec 类型的对象（包含 spec_id, spec_name, count 等）
        # 这类对象需要保留 spec_name, count, label_names，删除 cpu, mem, qps 等
        if "spec_name" in data or "spec_id" in data:
            # 需要删除的详情字段
            fields_to_remove = {
                "cpu",
                "mem",
                "qps",
                "storage_spec",
                "capacity",
                "device_class",
                "affinity",
                "location_spec",
            }
            for field in fields_to_remove:
                data.pop(field, None)

        # 递归处理所有值
        for key, value in list(data.items()):
            data[key] = _simplify_spec_objects(value)

    elif isinstance(data, list):
        # 递归处理数组中的每个元素
        for idx, item in enumerate(data):
            data[idx] = _simplify_spec_objects(item)

    return data


def _simplify_specs_dict(data: Any) -> Any:
    """
    递归遍历数据，将 specs 字典（key 为 spec_id，value 为规格详情）简化

    原始格式:
    "specs": {
        "385": {"id": 385, "cpu": {...}, "mem": {...}, "name": "8核_32G_100G", ...},
        "398": {"id": 398, "cpu": {...}, "mem": {...}, "name": "32核_128G_7T_带云盘", ...}
    }

    简化为:
    "specs": {
        "385": "8核_32G_100G",
        "398": "32核_128G_7T_带云盘"
    }

    Args:
        data: 待处理的数据

    Returns:
        简化后的数据
    """
    # 先尝试解析字符串化的 JSON
    if isinstance(data, str):
        parsed = _try_parse_json_string(data)
        if parsed != data:  # 解析成功
            return _simplify_specs_dict(parsed)
        return data

    if isinstance(data, dict):
        # 检查是否是 specs 字典（所有 value 都是 spec 对象）
        if data and all(isinstance(v, dict) and _is_spec_object(v) for v in data.values()):
            # 简化为 {spec_id: spec_name}
            return {k: v.get("name") or v.get("spec_name", "") for k, v in data.items()}

        # 递归处理所有值
        for key, value in list(data.items()):
            # 特殊处理：如果 key 是 "specs"，检查是否需要简化
            if key == "specs":
                parsed_value = _try_parse_json_string(value) if isinstance(value, str) else value
                if isinstance(parsed_value, dict):
                    if parsed_value and all(isinstance(v, dict) and _is_spec_object(v) for v in parsed_value.values()):
                        data[key] = {k: v.get("name") or v.get("spec_name", "") for k, v in parsed_value.items()}
                        continue
            data[key] = _simplify_specs_dict(value)

    elif isinstance(data, list):
        # 递归处理数组中的每个元素
        for idx, item in enumerate(data):
            data[idx] = _simplify_specs_dict(item)

    return data


def _simplify_backupinfo(data: Any) -> Any:
    """
    递归遍历数据，将 backupinfo 备份详情对象简化为只保留 backup_id 和 backup_time

    原始 backupinfo 包含大量字段如：backup_host, backup_port, file_list, binlog_info 等
    简化后只保留 backup_id 和 backup_time 两个关键字段

    Args:
        data: 待处理的数据

    Returns:
        简化后的数据
    """
    # 先尝试解析字符串化的 JSON
    if isinstance(data, str):
        parsed = _try_parse_json_string(data)
        if parsed != data:  # 解析成功
            return _simplify_backupinfo(parsed)
        return data

    if isinstance(data, dict):
        # 递归处理所有值
        for key, value in list(data.items()):
            # 特殊处理：如果 key 是 "backupinfo"，检查是否需要简化
            if key == "backupinfo":
                parsed_value = _try_parse_json_string(value) if isinstance(value, str) else value
                if isinstance(parsed_value, dict) and _is_backupinfo_object(parsed_value):
                    # 只保留 backup_id 和 backup_time
                    data[key] = {
                        "backup_id": parsed_value.get("backup_id"),
                        "backup_time": parsed_value.get("backup_time"),
                    }
                    continue
            data[key] = _simplify_backupinfo(value)

    elif isinstance(data, list):
        # 递归处理数组中的每个元素
        for idx, item in enumerate(data):
            data[idx] = _simplify_backupinfo(item)

    return data


def _summarize_long_lists(data: Any, max_length: int = 10) -> Any:
    """
    递归遍历数据，将长度大于 max_length 的列表转换为摘要形式

    摘要形式：保留前2个和后1个元素，中间用省略信息替代
    例如：[item1, item2, "...(省略 N 项)...", itemN]

    Args:
        data: 待处理的数据
        max_length: 列表长度阈值，超过此长度的列表会被摘要

    Returns:
        处理后的数据
    """
    if isinstance(data, dict):
        # 递归处理所有值
        for key, value in list(data.items()):
            data[key] = _summarize_long_lists(value, max_length)

    elif isinstance(data, list):
        # 先递归处理数组中的每个元素
        for idx, item in enumerate(data):
            data[idx] = _summarize_long_lists(item, max_length)

        # 然后检查是否需要摘要
        if len(data) > max_length:
            # 保留前2个和后1个元素
            first_items = data[:2]
            last_item = data[-1]
            omitted_count = len(data) - 3

            # 构建摘要列表
            data = first_items + [_(f"...(省略 {omitted_count} 项)...")] + [last_item]

    return data


def _handle_none_value(prop_schema: dict, current_path: str) -> Any:
    """
    处理值为 None 的情况

    Args:
        prop_schema: 属性的 schema 定义
        current_path: 当前数据路径（用于错误提示）

    Returns:
        默认值或 None

    Raises:
        SchemaExtractionError: 当必需字段值为空时抛出
    """
    default_value = prop_schema.get("default")
    if default_value is not None:
        return default_value
    # 检查是否是必需字段
    if prop_schema.get("required", False):
        prop_type = prop_schema.get("type")
        raise SchemaExtractionError(_("必需字段值为空"), path=current_path, details={"expected_type": prop_type})
    return None


def _extract_object_value(prop_schema: dict, value: Any, full_data: dict, current_path: str) -> Any:
    """
    提取 object 类型的值

    Args:
        prop_schema: 属性的 schema 定义
        value: 属性值
        full_data: 完整的原始数据
        current_path: 当前数据路径（用于错误提示）

    Returns:
        提取后的对象
    """
    if not isinstance(value, dict):
        raise SchemaExtractionError(
            _(f"类型不匹配，期望 object，实际为 {type(value).__name__}"),
            path=current_path,
            details={"expected_type": "object", "actual_type": type(value).__name__},
        )
    obj_properties = prop_schema.get("properties", {})
    if obj_properties:
        return _extract_object(obj_properties, value, full_data, current_path)
    # 无 properties 定义时，根据 extractKeys 提取或返回原值
    extract_keys = prop_schema.get("extractKeys")
    if extract_keys:
        return {k: v for k, v in value.items() if k in extract_keys}
    return value


def _extract_array_value(prop_schema: dict, value: Any, full_data: dict, current_path: str) -> list:
    """
    提取 array 类型的值

    Args:
        prop_schema: 属性的 schema 定义
        value: 属性值
        full_data: 完整的原始数据
        current_path: 当前数据路径（用于错误提示）

    Returns:
        提取后的数组
    """
    if not isinstance(value, list):
        raise SchemaExtractionError(
            _(f"类型不匹配，期望 array，实际为 {type(value).__name__}"),
            path=current_path,
            details={"expected_type": "array", "actual_type": type(value).__name__},
        )
    items_schema = prop_schema.get("items", {})
    extracted_items = []
    for idx, item in enumerate(value):
        item_path = f"{current_path}[{idx}]"
        try:
            extracted_items.append(_extract_value(items_schema, item, full_data, item_path))
        except SchemaExtractionError:
            raise
        except Exception as item_err:
            raise SchemaExtractionError(_(f"数组元素提取失败: {str(item_err)}"), path=item_path)
    return extracted_items


def _extract_string_value(value: Any, current_path: str) -> str:
    """
    提取 string 类型的值

    Args:
        value: 属性值
        current_path: 当前数据路径（用于错误提示）

    Returns:
        字符串值
    """
    if isinstance(value, str):
        return value
    # 尝试转换为字符串
    try:
        return str(value)
    except Exception:
        raise SchemaExtractionError(
            _("无法转换为 string 类型"), path=current_path, details={"actual_type": type(value).__name__}
        )


def _extract_integer_value(value: Any, current_path: str) -> int:
    """
    提取 integer 类型的值

    Args:
        value: 属性值
        current_path: 当前数据路径（用于错误提示）

    Returns:
        整数值
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise SchemaExtractionError(
            _(f"类型不匹配，期望 integer，实际为 {type(value).__name__}"),
            path=current_path,
            details={"expected_type": "integer", "actual_type": type(value).__name__},
        )
    return value


def _extract_number_value(value: Any, current_path: str) -> Union[int, float]:
    """
    提取 number 类型的值

    Args:
        value: 属性值
        current_path: 当前数据路径（用于错误提示）

    Returns:
        数值
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise SchemaExtractionError(
            _(f"类型不匹配，期望 number，实际为 {type(value).__name__}"),
            path=current_path,
            details={"expected_type": "number", "actual_type": type(value).__name__},
        )
    return value


def _extract_boolean_value(value: Any, current_path: str) -> bool:
    """
    提取 boolean 类型的值

    Args:
        value: 属性值
        current_path: 当前数据路径（用于错误提示）

    Returns:
        布尔值
    """
    if not isinstance(value, bool):
        raise SchemaExtractionError(
            _(f"类型不匹配，期望 boolean，实际为 {type(value).__name__}"),
            path=current_path,
            details={"expected_type": "boolean", "actual_type": type(value).__name__},
        )
    return value


# 类型处理函数映射表
_TYPE_EXTRACTORS = {
    "object": _extract_object_value,
    "array": _extract_array_value,
    "string": lambda prop_schema, value, full_data, current_path: _extract_string_value(value, current_path),
    "integer": lambda prop_schema, value, full_data, current_path: _extract_integer_value(value, current_path),
    "number": lambda prop_schema, value, full_data, current_path: _extract_number_value(value, current_path),
    "boolean": lambda prop_schema, value, full_data, current_path: _extract_boolean_value(value, current_path),
}


def _extract_value(prop_schema: dict, value: Any, full_data: dict, current_path: str) -> Any:
    """
    递归提取单个属性值

    Args:
        prop_schema: 属性的 schema 定义
        value: 属性值
        full_data: 完整的原始数据
        current_path: 当前数据路径（用于错误提示）

    Returns:
        提取后的值
    """
    # 处理 None 值
    if value is None:
        return _handle_none_value(prop_schema, current_path)

    prop_type = prop_schema.get("type")

    # 使用映射表获取对应的提取函数
    extractor = _TYPE_EXTRACTORS.get(prop_type)
    if extractor:
        return extractor(prop_schema, value, full_data, current_path)

    # 未知类型直接返回原值
    return value


def _extract_object(obj_properties: dict, data: dict, full_data: dict, parent_path: str = "") -> dict:
    """
    提取对象类型数据

    Args:
        obj_properties: 对象的 properties schema 定义
        data: 当前层级的数据
        full_data: 完整的原始数据
        parent_path: 父级路径（用于错误提示）

    Returns:
        提取后的对象
    """
    extracted = {}
    for key, prop_schema in obj_properties.items():
        current_path = f"{parent_path}.{key}" if parent_path else key
        # 支持从其他路径取值 (通过 sourceKey)
        source_key = prop_schema.get("sourceKey", key)
        value = data.get(source_key)

        try:
            extracted[key] = _extract_value(prop_schema, value, full_data, current_path)
        except SchemaExtractionError:
            raise
        except Exception as field_err:
            raise SchemaExtractionError(
                _(f"字段提取失败: {str(field_err)}"), path=current_path, details={"source_key": source_key}
            )
    return extracted


def extract_by_schema(schema: dict, raw_data: Union[str, dict]) -> dict:
    """
    根据 JSON Schema 从原始数据中抽取数据

    Args:
        schema: JSON Schema 定义
        raw_data: 原始数据，可以是 JSON 字符串或字典

    Returns:
        dict: 符合 Schema 结构的抽取结果

    Raises:
        SchemaExtractionError: 当数据抽取失败时抛出
    """

    # 校验 schema 参数
    if not isinstance(schema, dict):
        raise SchemaExtractionError(_("Schema 必须是字典类型"), path="schema", details={"actual_type": type(schema).__name__})

    if "properties" not in schema:
        raise SchemaExtractionError(_("Schema 缺少 properties 定义"), path="schema")

    # 解析 raw_data
    if isinstance(raw_data, str):
        try:
            parsed_data = json.loads(raw_data)
        except json.JSONDecodeError as json_err:
            raise SchemaExtractionError(
                _(f"JSON 解析失败: {str(json_err)}"),
                path="raw_data",
                details={"error_position": json_err.pos if hasattr(json_err, "pos") else None},
            )
    elif isinstance(raw_data, dict):
        parsed_data = raw_data
    else:
        raise SchemaExtractionError(
            _("原始数据必须是 JSON 字符串或字典类型"), path="raw_data", details={"actual_type": type(raw_data).__name__}
        )

    try:
        schema_properties = schema.get("properties", {})
        extracted_result = _extract_object(schema_properties, parsed_data, parsed_data)

        # 后处理1：简化 spec 规格详情对象，只保留名称（会解析字符串化的 JSON）
        extracted_result = _simplify_spec_objects(extracted_result)

        # 后处理2：简化 specs 字典（会解析字符串化的 JSON）
        extracted_result = _simplify_specs_dict(extracted_result)

        # 后处理3：简化 backupinfo 备份详情对象，只保留 backup_id 和 backup_time（会解析字符串化的 JSON）
        extracted_result = _simplify_backupinfo(extracted_result)

        # 后处理4：为包含 cluster_id 的对象追加 cluster_domain
        # 注意：必须在所有字符串解析后处理之后执行，这样才能正确处理解析后的 cluster_id
        clusters_map = parsed_data.get("clusters", {})
        if clusters_map:
            extracted_result = _enrich_cluster_domain(extracted_result, clusters_map)

        # 后处理5：删除辅助字段（clusters 用于查找域名的映射，specs 是规格详情映射，machine_infos 是机器信息映射，都不是真正的需求字段）
        for auxiliary_field in ("clusters", "specs", "machine_infos"):
            if auxiliary_field in extracted_result:
                del extracted_result[auxiliary_field]

        # 后处理6：将长度大于10的列表转换为摘要形式
        extracted_result = _summarize_long_lists(extracted_result)

        return extracted_result
    except SchemaExtractionError:
        raise
    except Exception as outer_err:
        raise SchemaExtractionError(
            _(f"数据抽取过程发生未知错误: {str(outer_err)}"), details={"error_type": type(outer_err).__name__}
        )
