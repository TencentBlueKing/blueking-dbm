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

from dataclasses import dataclass

from django.utils.translation import gettext as _

from backend.components.db_remote_service.client import DRSApi
from backend.flow.consts import SYSTEM_DBS
from backend.flow.utils.mysql.mysql_version_parse import get_online_mysql_version


@dataclass
class Endpoint:
    ip: str
    port: int
    bk_cloud_id: int
    cluster_id: int

    @property
    def address(self) -> str:
        return f"{self.ip}:{self.port}"


class PrecheckCollectError(Exception):
    """DTS 预检查采集失败。"""


def _query(endpoint: Endpoint, sql: str) -> list[dict]:
    try:
        response = DRSApi.short_rpc(
            {
                "addresses": [endpoint.address],
                "cmds": [sql],
                "force": False,
                "bk_cloud_id": endpoint.bk_cloud_id,
            }
        )
        if not response:
            raise ValueError("DRS returned an empty response")
        instance_result = response[0]
        if instance_result.get("error_msg"):
            raise ValueError(instance_result["error_msg"])
        command_results = instance_result.get("cmd_results") or []
        if not command_results:
            raise ValueError("DRS returned no command result")
        command_result = command_results[0]
        if command_result.get("error_msg"):
            raise ValueError(command_result["error_msg"])
        return command_result.get("table_data") or []
    except PrecheckCollectError:
        raise
    except Exception as exc:
        raise PrecheckCollectError(
            _("集群 {} 实例 {} 查询失败: {}").format(endpoint.cluster_id, endpoint.address, exc)
        ) from exc


class InstanceCollector:
    def __init__(self, endpoint: Endpoint) -> None:
        self.endpoint = endpoint

    def query(self, sql: str) -> list[dict]:
        return _query(self.endpoint, sql)

    def mysql_version(self) -> str:
        try:
            version = get_online_mysql_version(
                self.endpoint.ip,
                self.endpoint.port,
                self.endpoint.bk_cloud_id,
            )
        except Exception as exc:
            raise PrecheckCollectError(
                _("集群 {} 实例 {} 版本采集失败: {}").format(self.endpoint.cluster_id, self.endpoint.address, exc)
            ) from exc
        if not version:
            raise PrecheckCollectError(_("集群 {} 实例 {} 版本为空").format(self.endpoint.cluster_id, self.endpoint.address))
        return version

    def user_schemas(self) -> list[str]:
        rows = _query(self.endpoint, "SHOW DATABASES")
        schemas = []
        for row in rows:
            schema = row.get("Database") or row.get("database")
            if schema and schema not in SYSTEM_DBS:
                schemas.append(schema)
        return schemas

    def global_variables(self, names: list[str]) -> dict[str, str]:
        if not names:
            return {}
        unique = []
        seen = set()
        for name in names:
            key = str(name).strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(key)
        sql = "SHOW GLOBAL VARIABLES WHERE Variable_name IN ({})".format(", ".join(f"'{name}'" for name in unique))
        rows = _query(self.endpoint, sql)
        result = {}
        for row in rows:
            name = row.get("Variable_name") or row.get("variable_name")
            value = row.get("Value")
            if value is None:
                value = row.get("value")
            if name is None:
                continue
            result[str(name).lower()] = "" if value is None else str(value)
        return result
