# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community
Edition) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import logging
import os
import shutil
import time

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from drf_spectacular.settings import spectacular_settings

from backend import env
from backend.dbm_aiagent.mcp_tools import decorators
from backend.dbm_aiagent.mcp_tools.constants import DBMMcpTools
from backend.dbm_init.management.commands.mcp_checker import SimpleMCPDependencyGraph

logger = logging.getLogger("root")


class Command(BaseCommand):
    def add_arguments(self, parser):
        """添加命令行参数"""
        parser.add_argument(
            "--apigw",
            action="store_true",
            help="执行 APIGW 同步逻辑",
        )
        parser.add_argument(
            "--mcp",
            action="store_true",
            help="执行 MCP 同步逻辑",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="同时执行 APIGW 和 MCP 逻辑",
        )
        parser.add_argument("--only_mcp_resource", action="store_true", help="生成 mcp 资源描述")
        parser.add_argument("--mcp_check", type=str, nargs="*", help="mcp 依赖检查", required=False, default=None)
        # default=list(DBMMcpTools.get_values()))
        parser.add_argument(
            "--mcp_servers",
            type=str,
            default=None,
            help="仅导出指定 MCP Server 的 tools，多个用逗号分隔，例如：--mcp_servers=mysql-query,redis-bill。"
            "默认为空，表示导出全部。可选值参考 DBMMcpTools。",
        )

    @staticmethod
    def __preprocess_exclude_mcp_views(endpoints, **kwargs):
        """
        预处理 hook：排除不兼容 drf-spectacular 的视图
        只保留 MCP tools 相关的视图（路径包含 /apis/ai/mcp_tools/）
        """
        filtered = [endpoint for endpoint in endpoints if "/apis/ai/mcp_tools/" in endpoint[0]]
        return filtered

    @staticmethod
    def __build_preprocess_filter_by_mcp_servers(mcp_servers: list[str]):
        """
        根据指定的 mcp_servers 列表，构造一个预处理 hook，
        只保留属于这些 server 的 operation_id 对应视图。
        """
        # 汇总所有指定 server 下的 operation_id 集合
        allowed_operation_ids: set[str] = set()
        for server_name in mcp_servers:
            allowed_operation_ids.update(decorators.MCP_TOOLS_REGISTRY.get(server_name, []))

        logger.info(
            "mcp_servers filter: servers=%s, allowed_operation_ids=%s", mcp_servers, allowed_operation_ids
        )

        def _filter_hook(endpoints, **kwargs):
            filtered = []
            for endpoint in endpoints:
                # endpoint 结构：(path, path_regex, method, callback)
                callback = endpoint[3] if len(endpoint) > 3 else None
                op_id = None
                if callback is not None:
                    # ViewSetMixin actions 挂在 initkwargs 或 cls 上；
                    # drf-spectacular 会用 callback.initkwargs.get('kwargs') 等，
                    # 这里直接从 callback 的 cls + action 重建 operation_id
                    cls = getattr(callback, "cls", None)
                    action_name = getattr(callback, "actions", {}).get(endpoint[2].lower())
                    if cls and action_name:
                        view_func = getattr(cls, action_name, None)
                        if view_func:
                            op_id = getattr(view_func, "kwargs", {}).get("operation_id") or getattr(
                                view_func, "_spectacular_annotation", {}
                            ).get("operation_id")
                    # 兜底：直接从 callback 的 initkwargs 取
                    if op_id is None:
                        initkwargs = getattr(callback, "initkwargs", {})
                        op_id = initkwargs.get("operation_id")

                if op_id and op_id in allowed_operation_ids:
                    filtered.append(endpoint)
                elif op_id is None and "/apis/ai/mcp_tools/" in endpoint[0]:
                    # 无法解析 operation_id 时，保守保留（让 drf-spectacular 正常扫描后再筛选）
                    filtered.append(endpoint)

            return filtered

        return _filter_hook

    @staticmethod
    def __move_generated_resources_file(source_filename, target_file_path):
        """
        将生成的文件移动到目标位置
        TODO: 等 generate_resources_yaml 命令支持指定输出路径后，可以删除此方法
        """
        source_file = os.path.join(settings.BASE_DIR, source_filename)
        target_file = os.path.join(settings.BASE_DIR, target_file_path)

        if os.path.exists(source_file):
            # 确保目标目录存在
            target_dir = os.path.dirname(target_file)
            os.makedirs(target_dir, exist_ok=True)

            # 移动文件到目标位置
            shutil.move(source_file, target_file)
            logger.info(f"Resources file moved from {source_file} to {target_file}")
        else:
            logger.warning(f"Generated resources file not found at {source_file}")

    @staticmethod
    def sync_apigw(gateway_name, definition_file_path, resources_file_path):
        """执行 APIGW 同步逻辑"""

        # 同步网关基本信息
        logger.info("call sync_apigw_config with definition: %s" % definition_file_path)
        call_command("sync_apigw_config", f"--gateway-name={gateway_name}", f"--file={definition_file_path}")

        # 同步网关环境信息
        logger.info("call sync_apigw_stage with definition: %s" % definition_file_path)
        call_command("sync_apigw_stage", f"--gateway-name={gateway_name}", f"--file={definition_file_path}")

        # 为应用主动授权
        logger.info("call grant_apigw_permissions with definition: %s" % definition_file_path)
        call_command("grant_apigw_permissions", f"--gateway-name={gateway_name}", f"--file={definition_file_path}")

        # 同步网关资源
        logger.info("call sync_apigw_resources with resources: %s" % resources_file_path)
        call_command("sync_apigw_resources", f"--gateway-name={gateway_name}", f"--file={resources_file_path}")

        # 同步资源文档
        if env.BK_APIGW_RESOURCE_DOCS_BASE_DIR:
            logger.info("call sync_resource_docs_by_archive with definition: %s" % definition_file_path)
            call_command(
                "sync_resource_docs_by_archive",
                f"--gateway-name={gateway_name}",
                f"--file={definition_file_path}",
                "--safe-mode",
            )

        # 同步MCP资源
        if getattr(settings, "BK_APIGW_STAGE_ENABLE_MCP_SERVERS", None) and gateway_name == settings.BK_APIGW_MCP_NAME:
            logger.info(f"call sync_apigw_stage_mcp_servers with definition: {definition_file_path}")
            call_command(
                "create_version_and_release_apigw",
                f"--gateway-name={gateway_name}",
                f"--file={definition_file_path}",
                f"--stage={settings.BK_APIGW_STAGE_NAME}",
            )

            # 发布需要等待，这里暂停30s'
            logger.info("Sleep for 30s and wait for apigw-release to complete.")
            time.sleep(30)

            call_command(
                "sync_apigw_stage_mcp_servers",
                f"--gateway-name={gateway_name}",
                f"--file={definition_file_path}",
            )

        # 获取网关公钥
        logger.info("call fetch_apigw_public_key")
        call_command("fetch_apigw_public_key", f"--gateway-name={gateway_name}")

    def sync_dbm_apigw(self):
        """执行 DBM APIGW 同步逻辑"""
        if not env.BK_APIGW_STAGE_ENABLE_SERVERS:
            return

        definition_file_path = "backend/dbm_init/apigw/definition.yaml"
        resources_file_path = "backend/dbm_init/apigw/resources.yaml"
        self.sync_apigw(settings.BK_APIGW_NAME, definition_file_path, resources_file_path)

    def sync_mcp_apigw(self, only_mcp_resource: bool = False, mcp_servers: list[str] = None):
        """执行 MCP 同步逻辑

        Args:
            only_mcp_resource: 仅生成 mcp_resources.yaml，不同步网关
            mcp_servers: 若指定，则只导出这些 server 下的 tools；为 None 时导出全部
        """
        if not getattr(settings, "BK_APIGW_STAGE_ENABLE_MCP_SERVERS", None):
            return

        # 修改settings的BK_APIGW_STAGE_MCP_SERVERS，是的包含tools
        for server in settings.BK_APIGW_STAGE_MCP_SERVERS:
            server["tools"] = decorators.MCP_TOOLS_REGISTRY.get(server["name"], [])

        definition_file_path = "backend/dbm_init/apigw/mcp_definition.yaml"
        resources_file_path = "backend/dbm_init/apigw/mcp_resources.yaml"

        # 构造 mcp_servers 过滤 hook（仅在指定了 mcp_servers 时启用）
        mcp_servers_filter_hook = None
        if mcp_servers:
            logger.info("sync_mcp_apigw: filtering by mcp_servers=%s", mcp_servers)
            mcp_servers_filter_hook = Command.__build_preprocess_filter_by_mcp_servers(mcp_servers)

        # 生成mcp资源文件
        try:
            # 添加预处理 hook，只扫描 MCP tools 相关的视图
            spectacular_settings.PREPROCESSING_HOOKS.append(Command.__preprocess_exclude_mcp_views)
            if mcp_servers_filter_hook:
                spectacular_settings.PREPROCESSING_HOOKS.append(mcp_servers_filter_hook)
            call_command("generate_resources_yaml")
            Command.__move_generated_resources_file("resources.yaml", resources_file_path)
        finally:
            # 清理预处理 hook，避免影响其他命令
            if Command.__preprocess_exclude_mcp_views in spectacular_settings.PREPROCESSING_HOOKS:
                spectacular_settings.PREPROCESSING_HOOKS.remove(Command.__preprocess_exclude_mcp_views)
            if mcp_servers_filter_hook and mcp_servers_filter_hook in spectacular_settings.PREPROCESSING_HOOKS:
                spectacular_settings.PREPROCESSING_HOOKS.remove(mcp_servers_filter_hook)

        # 同步网关基本信息
        if not only_mcp_resource:
            self.sync_apigw(settings.BK_APIGW_MCP_NAME, definition_file_path, resources_file_path)

    def handle(self, *args, **options):
        apigw = options.get("apigw", False)
        mcp = options.get("mcp", False)
        all_mode = options.get("all", False)
        only_mcp_resource = options.get("only_mcp_resource", False)
        mcp_check = options.get("mcp_check")
        mcp_servers_raw = options.get("mcp_servers")

        # 解析 --mcp_servers=a,b,c → ['a', 'b', 'c']，去空格，过滤空串
        mcp_servers: list[str] | None = None
        if mcp_servers_raw:
            mcp_servers = [s.strip() for s in mcp_servers_raw.split(",") if s.strip()]
            if not mcp_servers:
                mcp_servers = None

        if mcp_check is not None:
            only_mcp_resource = True
            if len(mcp_check) == 0:
                mcp_check = DBMMcpTools.get_values()

        # 如果没有指定任何参数，默认执行 apigw 逻辑（保持向后兼容）
        if apigw or all_mode:
            self.sync_dbm_apigw()

        if mcp or all_mode or only_mcp_resource:
            self.sync_mcp_apigw(only_mcp_resource, mcp_servers=mcp_servers)

        if mcp_check:
            analyzer = SimpleMCPDependencyGraph()
            analyzer.load_from_file(
                os.path.join(settings.BASE_DIR, "backend/dbm_init/apigw/mcp_resources.yaml"), mcp_servers=mcp_check
            )
            analyzer.export_for_llm(os.path.join(settings.BASE_DIR, "mcp-knowledge.md"))
