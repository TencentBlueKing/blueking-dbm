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

from backend.components import DBConfigApi


def sync_dbconfig():
    """Sync dbconfig
    {
        "namespace": "tendbha",
        "conf_type": "dbconf",
        "conf_file": "MySQL-5.6",
        "conf_names": [
            {
                "op_type": "upsert"
                "conf_name": "x",
                "conf_name_lc": "x",
                "value_default": "y",
                "value_type": "STRING",
                "value_type_sub": "",
                "value_allowed": "",
                "need_restart": 1,
                "flag_locked": 0,
                "flag_visible": 1,
                "description":"xxxxx"
            }
        ]
    }
    """
    # Traverse all files under the current migrations directory.
    # Directory structure: migrations/{namespace}/{conf_type}/{conf_file}.json
    # Then batch call (batch_size=100) DBConfigApi.change_plat_config(upsert) to write data to dbconfig.
    # API body format see above json

    # Get the path of migrations directory
    current_dir = Path(__file__).parent
    migrations_dir = current_dir / "migrations"

    if not migrations_dir.exists():
        print(f"Migrations directory does not exist: {migrations_dir}")
        return

    batch_size = 100

    # Traverse all namespace directories under migrations directory
    for namespace_dir in migrations_dir.iterdir():
        if not namespace_dir.is_dir() or namespace_dir.name.startswith("_"):
            continue

        namespace = namespace_dir.name

        # Traverse all conf_type directories under namespace
        for conf_type_dir in namespace_dir.iterdir():
            if not conf_type_dir.is_dir() or conf_type_dir.name.startswith("_"):
                continue

            conf_type = conf_type_dir.name

            # Traverse all JSON configuration files under conf_type
            for conf_file_path in conf_type_dir.glob("*.json"):
                conf_file = conf_file_path.stem  # Remove .json suffix

                try:
                    # Read JSON file content
                    with open(conf_file_path, "r", encoding="utf-8") as f:
                        conf_items = json.load(f)

                    # Skip if not a list
                    if not isinstance(conf_items, list):
                        print(f"Skip non-list format file: {conf_file_path}")
                        continue

                    # Add op_type field to each configuration item
                    for item in conf_items:
                        if "op_type" not in item:
                            item["op_type"] = "upsert"

                    # Process configuration items in batches
                    for i in range(0, len(conf_items), batch_size):
                        batch_conf_names = conf_items[i : i + batch_size]

                        # Construct request parameters
                        params = {
                            "namespace": namespace,
                            "conf_type": conf_type,
                            "conf_file": conf_file,
                            "conf_names": batch_conf_names,
                        }

                        # Call API
                        try:
                            result = DBConfigApi.change_plat_config(params=params)

                            # Check return result
                            if result.get("code") != 0:
                                error_msg = (
                                    f"Sync failed: {namespace}/{conf_type}/{conf_file} "
                                    f"(batch {i // batch_size + 1}): "
                                    f"code={result.get('code')}, message={result.get('message')}"
                                )
                                print(error_msg)
                                raise Exception(error_msg)

                            print(
                                f"Sync success: {namespace}/{conf_type}/{conf_file} "
                                f"(batch {i // batch_size + 1}, total {len(batch_conf_names)} items)"
                            )
                        except Exception as e:
                            print(
                                f"Sync failed: {namespace}/{conf_type}/{conf_file} "
                                f"(batch {i // batch_size + 1}): {str(e)}"
                            )
                            raise

                except json.JSONDecodeError as e:
                    print(f"JSON parse failed: {conf_file_path}: {str(e)}")
                except Exception as e:
                    print(f"Process file failed: {conf_file_path}: {str(e)}")
