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

import yaml
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
        parser.add_argument("--mcp_servers", type=str, required=False, default=None, help="指定mcp导出tools, 逗号分隔")
        # default=list(DBMMcpTools.get_values()))

    @staticmethod
    def __preprocess_exclude_mcp_views(endpoints, **kwargs):
        """
        预处理 hook：排除不兼容 drf-spectacular 的视图
        只保留 MCP tools 相关的视图（路径包含 /apis/ai/mcp_tools/）
        """
        filtered = [endpoint for endpoint in endpoints if "/apis/ai/mcp_tools/" in endpoint[0]]
        return filtered

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
    def __get_tools_by_server_names(server_names):
        """根据 server 名称获取对应 operation_id 列表。"""
        if not server_names:
            return set()

        selected_tools = set()
        for server_name in server_names:
            operation_ids = decorators.MCP_TOOLS_REGISTRY.get(server_name, [])
            selected_tools.update(operation_ids)
        return selected_tools

    @staticmethod
    def __filter_mcp_resources_by_servers(resources_file_path, server_names):
        """根据指定 server 过滤 mcp_resources.yaml 中的 paths。"""
        tools = Command.__get_tools_by_server_names(server_names)
        if not tools:
            logger.warning(
                "No MCP tools matched for mcp_servers=%s, all MCP paths will be removed.", ",".join(server_names)
            )

        resource_file = os.path.join(settings.BASE_DIR, resources_file_path)
        with open(resource_file, "r", encoding="utf-8") as f:
            spec = yaml.safe_load(f) or {}

        filtered_paths = {}
        for path, path_item in (spec.get("paths", {}) or {}).items():
            keep_path = False
            for operation in (path_item or {}).values():
                if isinstance(operation, dict) and operation.get("operationId") in tools:
                    keep_path = True
                    break
            if keep_path:
                filtered_paths[path] = path_item

        spec["paths"] = filtered_paths
        with open(resource_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(spec, f, allow_unicode=True, sort_keys=False)

        logger.info(
            "Filtered MCP resources by mcp_servers=%s, kept paths=%s",
            ",".join(server_names),
            len(filtered_paths),
        )

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

    def sync_mcp_apigw(self, only_mcp_resource: bool = False, mcp_servers=None):
        """执行 MCP 同步逻辑"""
        if not getattr(settings, "BK_APIGW_STAGE_ENABLE_MCP_SERVERS", None):
            return

        selected_servers = set(mcp_servers) if mcp_servers is not None else None

        # 修改settings的BK_APIGW_STAGE_MCP_SERVERS，是的包含tools
        for server in settings.BK_APIGW_STAGE_MCP_SERVERS:
            if selected_servers is None or server["name"] in selected_servers:
                server["tools"] = decorators.MCP_TOOLS_REGISTRY.get(server["name"], [])
            else:
                server["tools"] = []

        definition_file_path = "backend/dbm_init/apigw/mcp_definition.yaml"
        resources_file_path = "backend/dbm_init/apigw/mcp_resources.yaml"

        # 生成mcp资源文件
        try:
            # 添加预处理 hook，只扫描 MCP tools 相关的视图
            spectacular_settings.PREPROCESSING_HOOKS.append(Command.__preprocess_exclude_mcp_views)
            call_command("generate_resources_yaml")
            Command.__move_generated_resources_file("resources.yaml", resources_file_path)
            # 过滤mcp资源文件
            if selected_servers is not None:
                Command.__filter_mcp_resources_by_servers(resources_file_path, selected_servers)
        finally:
            # 清理预处理 hook，避免影响其他命令
            if Command.__preprocess_exclude_mcp_views in spectacular_settings.PREPROCESSING_HOOKS:
                spectacular_settings.PREPROCESSING_HOOKS.remove(Command.__preprocess_exclude_mcp_views)

        # 同步网关基本信息
        if not only_mcp_resource:
            self.sync_apigw(settings.BK_APIGW_MCP_NAME, definition_file_path, resources_file_path)

    def handle(self, *args, **options):
        apigw = options.get("apigw", False)
        mcp = options.get("mcp", False)
        all_mode = options.get("all", False)
        only_mcp_resource = options.get("only_mcp_resource", False)
        mcp_check = options.get("mcp_check")
        mcp_servers_option = options.get("mcp_servers")
        mcp_servers = mcp_servers_option.split(",") if mcp_servers_option else None

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
