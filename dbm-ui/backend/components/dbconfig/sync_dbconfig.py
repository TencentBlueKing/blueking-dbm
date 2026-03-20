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
from pathlib import Path
from typing import List, Optional

from backend.components import DBConfigApi


def _register_config_file_definition(namespace: str, conf_file_def: dict) -> None:
    """注册单个配置文件定义

    Args:
        namespace: 命名空间
        conf_file_def: 配置文件定义字典

    Raises:
        Exception: 注册失败时抛出异常
    """
    # 添加 namespace 和 op_type 字段
    conf_file_def["namespace"] = namespace
    if "op_type" not in conf_file_def:
        conf_file_def["op_type"] = "upsert"

    # 调用 API 注册配置文件定义
    result = DBConfigApi.change_config_file_def(params=conf_file_def, raw=True)

    # 检查返回结果
    if result.get("code") != 0:
        error_msg = (
            f"Register config file definition failed: "
            f"{namespace}/{conf_file_def.get('conf_type')}/{conf_file_def.get('conf_file')}: "
            f"code={result.get('code')}, message={result.get('message')}"
        )
        print(error_msg)
        raise Exception(error_msg)

    print(
        f"Register config file definition success: "
        f"{namespace}/{conf_file_def.get('conf_type')}/{conf_file_def.get('conf_file')}"
    )


def _process_namespace_config_file(namespace: str, namespace_dir: Path) -> None:
    """处理 namespace 配置文件定义（{namespace}.json）

    Args:
        namespace: 命名空间名称
        namespace_dir: namespace 目录路径
    """
    namespace_json_path = namespace_dir / f"{namespace}.json"
    if not namespace_json_path.exists():
        return

    try:
        with open(namespace_json_path, "r", encoding="utf-8") as f:
            conf_file_defs = json.load(f)

        # 确保是列表格式
        if not isinstance(conf_file_defs, list):
            print(f"Skip non-list format file: {namespace_json_path}")
            return

        # 为每个配置文件定义单独调用 API
        success_count = 0
        for conf_file_def in conf_file_defs:
            try:
                _register_config_file_definition(namespace, conf_file_def)
                success_count += 1
            except Exception as e:
                print(
                    f"Register config file definition failed: "
                    f"{namespace}/{conf_file_def.get('conf_type')}/{conf_file_def.get('conf_file')}: {str(e)}"
                )
                raise

        print(
            f"Register config file definition completed for namespace '{namespace}': "
            f"{success_count}/{len(conf_file_defs)} config files registered"
        )

    except json.JSONDecodeError as e:
        print(f"JSON parse failed: {namespace_json_path}: {str(e)}")
        raise
    except Exception as e:
        print(f"Process namespace config file failed: {namespace_json_path}: {str(e)}")
        raise


def _sync_config_items(namespace: str, conf_type: str, conf_file: str, conf_names: List[dict]) -> None:
    """同步配置项

    Args:
        namespace: 命名空间
        conf_type: 配置类型
        conf_file: 配置文件名
        conf_names: 配置项列表

    Raises:
        Exception: 同步失败时抛出异常
    """
    # 构造请求参数
    params = {
        "namespace": namespace,
        "conf_type": conf_type,
        "conf_file": conf_file,
        "op_user": "system",  # 后台会把 system 不记录操作记录
        "conf_names": conf_names,
    }

    # 调用 API
    result = DBConfigApi.change_plat_config(params=params, raw=True)

    # 检查返回结果
    if result.get("code") != 0:
        error_msg = (
            f"Sync failed: {namespace}/{conf_type}/{conf_file}: "
            f"code={result.get('code')}, message={result.get('message')}"
        )
        print(error_msg)
        raise Exception(error_msg)

    print(f"Sync success: {namespace}/{conf_type}/{conf_file} " f"(total {len(conf_names)} items)")


def _process_config_file(
    namespace: str, conf_type: str, conf_file_path: Path, target_conf_file: Optional[str] = None
) -> None:
    """处理单个配置文件

    Args:
        namespace: 命名空间
        conf_type: 配置类型
        conf_file_path: 配置文件路径
        target_conf_file: 指定要同步的配置文件名，为空则处理所有
    """
    current_conf_file = conf_file_path.stem  # 移除 .json 后缀

    # 如果指定了 conf_file，则只处理匹配的 conf_file
    if target_conf_file and current_conf_file != target_conf_file:
        return

    try:
        # 读取 JSON 文件内容
        with open(conf_file_path, "r", encoding="utf-8") as f:
            conf_items = json.load(f)

        # 跳过非列表格式
        if not isinstance(conf_items, list):
            print(f"Skip non-list format file: {conf_file_path}")
            return

        # 为每个配置项添加 op_type 字段
        for item in conf_items:
            if "op_type" not in item:
                item["op_type"] = "upsert"

        # 一次性同步所有配置项
        try:
            _sync_config_items(namespace, conf_type, current_conf_file, conf_items)
        except Exception as e:
            print(f"Sync failed: {namespace}/{conf_type}/{current_conf_file}: {str(e)}")
            raise

    except json.JSONDecodeError as e:
        print(f"JSON parse failed: {conf_file_path}: {str(e)}")
        raise
    except Exception as e:
        print(f"Process file failed: {conf_file_path}: {str(e)}")
        raise


def _process_conf_type_dir(
    namespace: str, conf_type_dir: Path, target_conf_type: Optional[str] = None, target_conf_file: Optional[str] = None
) -> None:
    """处理 conf_type 目录

    Args:
        namespace: 命名空间
        conf_type_dir: conf_type 目录路径
        target_conf_type: 指定要同步的配置类型，为空则处理所有
        target_conf_file: 指定要同步的配置文件名，为空则处理所有
    """
    if not conf_type_dir.is_dir() or conf_type_dir.name.startswith("_"):
        return

    current_conf_type = conf_type_dir.name

    # 如果指定了 conf_type，则只处理匹配的 conf_type
    if target_conf_type and current_conf_type != target_conf_type:
        return

    # 遍历 conf_type 下的所有 JSON 配置文件
    for conf_file_path in conf_type_dir.glob("*.json"):
        _process_config_file(namespace, current_conf_type, conf_file_path, target_conf_file)


def _process_namespace_dir(
    namespace_dir: Path,
    target_namespace: Optional[str] = None,
    target_conf_type: Optional[str] = None,
    target_conf_file: Optional[str] = None,
) -> None:
    """处理 namespace 目录

    Args:
        namespace_dir: namespace 目录路径
        target_namespace: 指定要同步的命名空间，为空则处理所有
        target_conf_type: 指定要同步的配置类型，为空则处理所有
        target_conf_file: 指定要同步的配置文件名，为空则处理所有
    """
    if not namespace_dir.is_dir() or namespace_dir.name.startswith("_"):
        return

    current_namespace = namespace_dir.name

    # 如果指定了 namespace，则只处理匹配的 namespace
    if target_namespace and current_namespace != target_namespace:
        return

    # 首先处理 {namespace}.json 文件，注册配置文件定义
    _process_namespace_config_file(current_namespace, namespace_dir)

    # 遍历 namespace 下的所有 conf_type 目录
    for conf_type_dir in namespace_dir.iterdir():
        _process_conf_type_dir(current_namespace, conf_type_dir, target_conf_type, target_conf_file)


def sync_dbconfig(
    namespace: Optional[str] = None, conf_type: Optional[str] = None, conf_file: Optional[str] = None
) -> None:
    """同步 DBConfig 配置

    遍历 migrations 目录下的所有配置文件，批量调用 DBConfigApi 写入到 dbconfig。
    目录结构: migrations/{namespace}/{conf_type}/{conf_file}.json

    Args:
        namespace: 指定要同步的 namespace，为空则同步所有 namespace
        conf_type: 指定要同步的 conf_type，为空则同步所有 conf_type
        conf_file: 指定要同步的 conf_file，为空则同步所有 conf_file

    API 请求格式示例:
    {
        "namespace": "tendbha",
        "conf_type": "dbconf",
        "conf_file": "MySQL-5.6",
        "conf_names": [
            {
                "op_type": "upsert",
                "conf_name": "x",
                "conf_name_lc": "x",
                "value_default": "y",
                "value_type": "STRING",
                "value_type_sub": "",
                "value_allowed": "",
                "need_restart": 1,
                "flag_locked": 0,
                "flag_visible": 1,
                "description": "xxxxx"
            }
        ]
    }
    """
    # 获取 migrations 目录路径
    current_dir = Path(__file__).parent
    migrations_dir = current_dir / "migrations"

    if not migrations_dir.exists():
        print(f"Migrations directory does not exist: {migrations_dir}")
        return

    # 遍历所有 namespace 目录
    for namespace_dir in migrations_dir.iterdir():
        _process_namespace_dir(namespace_dir, namespace, conf_type, conf_file)
