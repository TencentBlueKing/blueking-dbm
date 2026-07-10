# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

MySQL DTS OpenAPI 客户端，经 DRS 代理转发到 DTS Master。
使用方式与异常处理见同目录 README.md。
"""
from typing import Any

from django.utils.translation import gettext_lazy as _

from ..base import BaseApi
from ..domains import DRS_APIGW_DOMAIN
from .types import (
    ClusterInfoResponse,
    ClusterTopology,
    ConvertTaskRequest,
    ConvertTaskResponse,
    CreateSourceRequest,
    CreateTaskRequest,
    CreateTaskResponse,
    DisableRelayRequest,
    EnableRelayRequest,
    GetSourceResponse,
    ImportTemplatesRequest,
    ImportTemplatesResponse,
    ListMastersResponse,
    ListSourcesResponse,
    ListTasksResponse,
    ListWorkersResponse,
    MigrateTargetListResponse,
    OperateTaskSchemaRequest,
    PurgeRelayRequest,
    SourceStatusListResponse,
    StartTaskRequest,
    StopTaskRequest,
    TableStructureResponse,
    Task,
    TaskStatusListResponse,
    TransferSourceRequest,
    UpdateSourceRequest,
    UpdateTaskRequest,
    UpdateTaskResponse,
)


class _MySQLDTSApi(BaseApi):
    """MySQL DTS API 客户端。

    :raises ApiRequestError: DTS 业务失败、Master 不可达、DRS 转发/网络错误（最常见）
    :raises ApiResultError: DRS 网关返回 result=false（较少见）
    :raises pydantic.ValidationError: 响应结构与 types 定义不符（应修 bug，非业务异常）

    详细说明见 ``backend/components/mysqldtsapi/README.md``。
    """

    MODULE = _("DTS 数据迁移服务")
    BASE = DRS_APIGW_DOMAIN

    def __init__(self):
        self._proxy_rpc = self.generate_data_api(
            method="POST",
            url="v2/mysql-dts/rpc",
            description=_("DTS 代理 RPC"),
        )

    def _call(self, dts_master_addr: str, method: str, url: str, params: dict | None = None) -> Any:
        """通过 DRS 代理转发请求到真实的 DTS Master"""
        body = {
            "method": method,
            "url": url,
            "params": params or {},
            "dts_master_addr": dts_master_addr,
        }
        return self._proxy_rpc(body)

    @staticmethod
    def _dump_task(task: Task) -> dict:
        """序列化 Task；DTS OpenAPI 不接受 shard_mode 空字符串。"""
        params = task.model_dump(exclude_none=True, by_alias=True)
        if not params.get("shard_mode"):
            params.pop("shard_mode", None)
        return params

    # ============================================================
    # 1. Source 管理
    # ============================================================

    def create_source(self, dts_master_addr: str, request: CreateSourceRequest) -> GetSourceResponse:
        """1.1 POST /api/v1/sources — 创建数据源

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param request: 数据源配置
        """
        params = request.model_dump(exclude_none=True, by_alias=True)
        data = self._call(dts_master_addr, "POST", "/api/v1/sources", params)
        return GetSourceResponse(**data)

    def list_sources(
        self, dts_master_addr: str, with_status: bool = False, enable_relay: bool = False
    ) -> ListSourcesResponse:
        """1.2 GET /api/v1/sources — 获取数据源列表

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param with_status: 附带 source 状态信息
        :param enable_relay: 仅返回已启用 relay 的 source
        """
        params: dict = {}
        if with_status:
            params["with_status"] = True
        if enable_relay:
            params["enable_relay"] = True
        data = self._call(dts_master_addr, "GET", "/api/v1/sources", params)
        return ListSourcesResponse(**data)

    def get_source(self, dts_master_addr: str, source_name: str, with_status: bool = False) -> GetSourceResponse:
        """1.3 GET /api/v1/sources/{source-name} — 获取单个数据源

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param source_name: 数据源名称
        :param with_status: 附带 source 状态信息
        """
        params = {}
        if with_status:
            params["with_status"] = True
        data = self._call(dts_master_addr, "GET", f"/api/v1/sources/{source_name}", params)
        return GetSourceResponse(**data)

    def delete_source(self, dts_master_addr: str, source_name: str, force: bool = False) -> None:
        """1.4 DELETE /api/v1/sources/{source-name} — 删除数据源

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param source_name: 数据源名称
        :param force: 强制删除，同时停止关联的 task
        """
        params = {}
        if force:
            params["force"] = True
        self._call(dts_master_addr, "DELETE", f"/api/v1/sources/{source_name}", params)

    def update_source(self, dts_master_addr: str, source_name: str, request: UpdateSourceRequest) -> GetSourceResponse:
        """1.5 PUT /api/v1/sources/{source-name} — 更新数据源

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param source_name: 数据源名称
        :param request: 完整的数据源配置
        """
        params = request.model_dump(exclude_none=True, by_alias=True)
        data = self._call(dts_master_addr, "PUT", f"/api/v1/sources/{source_name}", params)
        return GetSourceResponse(**data)

    def get_source_status(self, dts_master_addr: str, source_name: str) -> SourceStatusListResponse:
        """1.6 GET /api/v1/sources/{source-name}/status — 获取数据源状态

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param source_name: 数据源名称
        """
        data = self._call(dts_master_addr, "GET", f"/api/v1/sources/{source_name}/status")
        return SourceStatusListResponse(**data)

    def enable_source(self, dts_master_addr: str, source_name: str) -> None:
        """1.7 POST /api/v1/sources/{source-name}/enable — 启用数据源

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param source_name: 数据源名称
        """
        self._call(dts_master_addr, "POST", f"/api/v1/sources/{source_name}/enable")

    def disable_source(self, dts_master_addr: str, source_name: str) -> None:
        """1.8 POST /api/v1/sources/{source-name}/disable — 禁用数据源

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param source_name: 数据源名称
        """
        self._call(dts_master_addr, "POST", f"/api/v1/sources/{source_name}/disable")

    def transfer_source(self, dts_master_addr: str, source_name: str, request: TransferSourceRequest) -> None:
        """1.9 POST /api/v1/sources/{source-name}/transfer — 迁移数据源到指定 worker

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param source_name: 数据源名称
        :param request: 目标 worker 名称
        """
        params = request.model_dump(exclude_none=True, by_alias=True)
        self._call(dts_master_addr, "POST", f"/api/v1/sources/{source_name}/transfer", params)

    def enable_relay(self, dts_master_addr: str, source_name: str, request: EnableRelayRequest | None = None) -> None:
        """1.10 POST /api/v1/sources/{source-name}/relay/enable — 启用 relay log

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param source_name: 数据源名称
        :param request: relay 启停配置
        """
        params = request.model_dump(exclude_none=True, by_alias=True) if request else {}
        self._call(dts_master_addr, "POST", f"/api/v1/sources/{source_name}/relay/enable", params)

    def disable_relay(
        self, dts_master_addr: str, source_name: str, request: DisableRelayRequest | None = None
    ) -> None:
        """1.11 POST /api/v1/sources/{source-name}/relay/disable — 禁用 relay log

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param source_name: 数据源名称
        :param request: 指定 worker 列表
        """
        params = request.model_dump(exclude_none=True, by_alias=True) if request else {}
        self._call(dts_master_addr, "POST", f"/api/v1/sources/{source_name}/relay/disable", params)

    def purge_relay(self, dts_master_addr: str, source_name: str, request: PurgeRelayRequest) -> None:
        """1.12 POST /api/v1/sources/{source-name}/relay/purge — 手动清理 relay log

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param source_name: 数据源名称
        :param request: 清理参数
        """
        params = request.model_dump(exclude_none=True, by_alias=True)
        self._call(dts_master_addr, "POST", f"/api/v1/sources/{source_name}/relay/purge", params)

    def get_source_schemas(self, dts_master_addr: str, source_name: str) -> list[str]:
        """1.13 GET /api/v1/sources/{source-name}/schemas — 获取上游库列表

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param source_name: 数据源名称
        """
        return self._call(dts_master_addr, "GET", f"/api/v1/sources/{source_name}/schemas")

    def get_source_schema_tables(self, dts_master_addr: str, source_name: str, schema_name: str) -> list[str]:
        """1.14 GET /api/v1/sources/{source-name}/schemas/{schema-name} — 获取上游表列表

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param source_name: 数据源名称
        :param schema_name: 库名
        """
        return self._call(dts_master_addr, "GET", f"/api/v1/sources/{source_name}/schemas/{schema_name}")

    # ============================================================
    # 2. Task 管理
    # ============================================================

    def create_task(self, dts_master_addr: str, request: CreateTaskRequest) -> CreateTaskResponse:
        """2.1 POST /api/v1/tasks — 创建任务

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param request: 任务配置
        """
        params = {"task": self._dump_task(request.task)}
        data = self._call(dts_master_addr, "POST", "/api/v1/tasks", params)
        return CreateTaskResponse(**data)

    def list_tasks(
        self,
        dts_master_addr: str,
        with_status: bool = False,
        stage: str | None = None,
        source_name_list: list[str] | None = None,
    ) -> ListTasksResponse:
        """2.2 GET /api/v1/tasks — 获取任务列表

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param with_status: 附带 subtask 状态
        :param stage: 按 stage 过滤: Stopped / Running / Finished
        :param source_name_list: 按 source 过滤
        """
        params: dict = {}
        if with_status:
            params["with_status"] = True
        if stage:
            params["stage"] = stage
        if source_name_list:
            params["source_name_list"] = source_name_list
        data = self._call(dts_master_addr, "GET", "/api/v1/tasks", params)
        return ListTasksResponse(**data)

    def get_task(self, dts_master_addr: str, task_name: str, with_status: bool = False) -> Task:
        """2.3 GET /api/v1/tasks/{task-name} — 获取单个任务（完整 Task，可供 recreate）

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param task_name: 任务名称
        :param with_status: 附带 subtask 状态列表（解析前会剥离，不进入 Task）
        """
        params = {}
        if with_status:
            params["with_status"] = True
        data = self._call(dts_master_addr, "GET", f"/api/v1/tasks/{task_name}", params)
        if isinstance(data, dict):
            data = dict(data)
            data.pop("status_list", None)
        return Task.model_validate(data)

    def delete_task(
        self, dts_master_addr: str, task_name: str, force: bool = False, source_name_list: list[str] | None = None
    ) -> None:
        """2.4 DELETE /api/v1/tasks/{task-name} — 删除任务

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param task_name: 任务名称
        :param force: 强制停止运行中的 subtask 后删除
        :param source_name_list: 仅删除指定 source 的 subtask
        """
        params: dict = {}
        if force:
            params["force"] = True
        body = {}
        if source_name_list:
            body["source_name_list"] = source_name_list
        merged = {**params, **body}
        self._call(dts_master_addr, "DELETE", f"/api/v1/tasks/{task_name}", merged if merged else None)

    def update_task(self, dts_master_addr: str, task_name: str, request: UpdateTaskRequest) -> UpdateTaskResponse:
        """2.5 PUT /api/v1/tasks/{task-name} — 更新任务

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param task_name: 任务名称
        :param request: 完整任务配置
        """
        params = {"task": self._dump_task(request.task)}
        data = self._call(dts_master_addr, "PUT", f"/api/v1/tasks/{task_name}", params)
        return UpdateTaskResponse(**data)

    def get_task_status(
        self, dts_master_addr: str, task_name: str, source_name_list: list[str] | None = None
    ) -> TaskStatusListResponse:
        """2.6 GET /api/v1/tasks/{task-name}/status — 获取任务状态

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param task_name: 任务名称
        :param source_name_list: 仅返回指定 source 的 subtask 状态
        """
        params: dict = {}
        if source_name_list:
            params["source_name_list"] = source_name_list
        data = self._call(dts_master_addr, "GET", f"/api/v1/tasks/{task_name}/status", params)
        return TaskStatusListResponse(**data)

    def start_task(self, dts_master_addr: str, task_name: str, request: StartTaskRequest | None = None) -> None:
        """2.7 POST /api/v1/tasks/{task-name}/start — 启动任务

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param task_name: 任务名称
        :param request: 启动参数
        """
        params = request.model_dump(exclude_none=True, by_alias=True) if request else {}
        self._call(dts_master_addr, "POST", f"/api/v1/tasks/{task_name}/start", params)

    def stop_task(self, dts_master_addr: str, task_name: str, request: StopTaskRequest | None = None) -> None:
        """2.8 POST /api/v1/tasks/{task-name}/stop — 停止任务

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param task_name: 任务名称
        :param request: 停止参数
        """
        params = request.model_dump(exclude_none=True, by_alias=True) if request else {}
        self._call(dts_master_addr, "POST", f"/api/v1/tasks/{task_name}/stop", params)

    def get_task_migrate_targets(
        self,
        dts_master_addr: str,
        task_name: str,
        source_name: str,
        schema_pattern: str | None = None,
        table_pattern: str | None = None,
    ) -> MigrateTargetListResponse:
        """2.9 GET /api/v1/tasks/{task-name}/sources/{source-name}/migrate_targets — 查看迁移表映射

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param task_name: 任务名称
        :param source_name: 数据源名称
        :param schema_pattern: 按库名过滤
        :param table_pattern: 按表名过滤
        """
        params: dict = {}
        if schema_pattern:
            params["schema_pattern"] = schema_pattern
        if table_pattern:
            params["table_pattern"] = table_pattern
        data = self._call(
            dts_master_addr, "GET", f"/api/v1/tasks/{task_name}/sources/{source_name}/migrate_targets", params
        )
        if data.get("data") is None:
            data["data"] = []
        return MigrateTargetListResponse(**data)

    def get_task_schemas(self, dts_master_addr: str, task_name: str, source_name: str) -> list[str]:
        """2.10 GET /api/v1/tasks/{task-name}/sources/{source-name}/schemas — 获取任务内库列表

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param task_name: 任务名称
        :param source_name: 数据源名称
        """
        return self._call(dts_master_addr, "GET", f"/api/v1/tasks/{task_name}/sources/{source_name}/schemas")

    def get_task_schema_tables(self, dts_master_addr: str, task_name: str, source_name: str, schema: str) -> list[str]:
        """2.11 GET /api/v1/tasks/{task-name}/sources/{source-name}/schemas/{schema} — 获取任务内表列表

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param task_name: 任务名称
        :param source_name: 数据源名称
        :param schema: 库名
        """
        return self._call(dts_master_addr, "GET", f"/api/v1/tasks/{task_name}/sources/{source_name}/schemas/{schema}")

    def get_task_table_structure(
        self, dts_master_addr: str, task_name: str, source_name: str, schema: str, table: str
    ) -> TableStructureResponse:
        """2.12 GET /api/v1/tasks/{task-name}/sources/{source-name}/schemas/{schema}/{table} — 查看表结构

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param task_name: 任务名称
        :param source_name: 数据源名称
        :param schema: 库名
        :param table: 表名
        """
        data = self._call(
            dts_master_addr, "GET", f"/api/v1/tasks/{task_name}/sources/{source_name}/schemas/{schema}/{table}"
        )
        return TableStructureResponse(**data)

    def operate_task_schema(
        self,
        dts_master_addr: str,
        task_name: str,
        source_name: str,
        schema: str,
        table: str,
        request: OperateTaskSchemaRequest,
    ) -> None:
        """2.13 PUT /api/v1/tasks/{task-name}/sources/{source-name}/schemas/{schema}/{table} — 操作表结构

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param task_name: 任务名称
        :param source_name: 数据源名称
        :param schema: 库名
        :param table: 表名
        :param request: sql_content / flush / sync
        """
        params = request.model_dump(exclude_none=True, by_alias=True)
        self._call(
            dts_master_addr, "PUT", f"/api/v1/tasks/{task_name}/sources/{source_name}/schemas/{schema}/{table}", params
        )

    def delete_task_schema(
        self, dts_master_addr: str, task_name: str, source_name: str, schema: str, table: str
    ) -> None:
        """2.14 DELETE /api/v1/tasks/{task-name}/sources/{source-name}/schemas/{schema}/{table} — 删除表结构(还原 checkpoint)

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param task_name: 任务名称
        :param source_name: 数据源名称
        :param schema: 库名
        :param table: 表名
        """
        self._call(
            dts_master_addr, "DELETE", f"/api/v1/tasks/{task_name}/sources/{source_name}/schemas/{schema}/{table}"
        )

    # ============================================================
    # 3. Task Template
    # ============================================================

    def create_template(self, dts_master_addr: str, task: Task) -> dict:
        """3.1 POST /api/v1/tasks/templates — 保存模板

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param task: 模板配置 (裸 Task 对象)
        """
        params = self._dump_task(task)
        data = self._call(dts_master_addr, "POST", "/api/v1/tasks/templates", params)
        return data

    def list_templates(self, dts_master_addr: str) -> ListTasksResponse:
        """3.2 GET /api/v1/tasks/templates — 获取模板列表

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        """
        data = self._call(dts_master_addr, "GET", "/api/v1/tasks/templates")
        return ListTasksResponse(**data)

    def get_template(self, dts_master_addr: str, task_name: str) -> dict:
        """3.3 GET /api/v1/tasks/templates/{task-name} — 获取单个模板

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param task_name: 模板名称
        """
        data = self._call(dts_master_addr, "GET", f"/api/v1/tasks/templates/{task_name}")
        return data

    def update_template(self, dts_master_addr: str, task_name: str, task: Task) -> dict:
        """3.4 PUT /api/v1/tasks/templates/{task-name} — 更新模板

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param task_name: 模板名称
        :param task: 完整模板配置 (裸 Task 对象)
        """
        params = self._dump_task(task)
        data = self._call(dts_master_addr, "PUT", f"/api/v1/tasks/templates/{task_name}", params)
        return data

    def delete_template(self, dts_master_addr: str, task_name: str) -> None:
        """3.5 DELETE /api/v1/tasks/templates/{task-name} — 删除模板

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param task_name: 模板名称
        """
        self._call(dts_master_addr, "DELETE", f"/api/v1/tasks/templates/{task_name}")

    def import_templates(
        self, dts_master_addr: str, request: ImportTemplatesRequest | None = None
    ) -> ImportTemplatesResponse:
        """3.6 POST /api/v1/tasks/templates/import — 批量导入

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param request: overwrite 参数
        """
        params = request.model_dump(exclude_none=True, by_alias=True) if request else {}
        data = self._call(dts_master_addr, "POST", "/api/v1/tasks/templates/import", params)
        return ImportTemplatesResponse(**data)

    # ============================================================
    # 4. 任务格式转换
    # ============================================================

    def convert_task(self, dts_master_addr: str, request: ConvertTaskRequest) -> ConvertTaskResponse:
        """4.1 POST /api/v1/tasks/converters — YAML ↔ OpenAPI 互转

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param request: task 和 task_config_file 二选一
        """
        params = request.model_dump(exclude_none=True, by_alias=True)
        data = self._call(dts_master_addr, "POST", "/api/v1/tasks/converters", params)
        return ConvertTaskResponse(**data)

    # ============================================================
    # 5. 集群管理
    # ============================================================

    def get_cluster_info(self, dts_master_addr: str) -> ClusterInfoResponse:
        """5.1 GET /api/v1/cluster/info — 获取集群信息

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        """
        data = self._call(dts_master_addr, "GET", "/api/v1/cluster/info")
        return ClusterInfoResponse(**data)

    def update_cluster_info(self, dts_master_addr: str, topology: ClusterTopology) -> ClusterInfoResponse:
        """5.2 PUT /api/v1/cluster/info — 更新集群拓扑信息

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param topology: 集群拓扑信息
        """
        params = topology.model_dump(exclude_none=True, by_alias=True)
        data = self._call(dts_master_addr, "PUT", "/api/v1/cluster/info", params)
        return ClusterInfoResponse(**data)

    def list_masters(self, dts_master_addr: str) -> ListMastersResponse:
        """5.3 GET /api/v1/cluster/masters — master 节点列表

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        """
        data = self._call(dts_master_addr, "GET", "/api/v1/cluster/masters")
        return ListMastersResponse(**data)

    def offline_master(self, dts_master_addr: str, master_name: str) -> None:
        """5.4 DELETE /api/v1/cluster/masters/{master-name} — 下线 master 节点

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param master_name: master 节点名称
        """
        self._call(dts_master_addr, "DELETE", f"/api/v1/cluster/masters/{master_name}")

    def list_workers(self, dts_master_addr: str) -> ListWorkersResponse:
        """5.5 GET /api/v1/cluster/workers — worker 节点列表

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        """
        data = self._call(dts_master_addr, "GET", "/api/v1/cluster/workers")
        return ListWorkersResponse(**data)

    def offline_worker(self, dts_master_addr: str, worker_name: str) -> None:
        """5.6 DELETE /api/v1/cluster/workers/{worker-name} — 下线 worker 节点

        :param dts_master_addr: DTS Master 地址，如 1.1.1.1:1083
        :param worker_name: worker 节点名称
        """
        self._call(dts_master_addr, "DELETE", f"/api/v1/cluster/workers/{worker_name}")


MySQLDTSApi = _MySQLDTSApi()
