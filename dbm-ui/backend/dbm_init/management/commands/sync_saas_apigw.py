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

    def sync_mcp_apigw(self, only_mcp_resource: bool = False):
        """执行 MCP 同步逻辑"""
        if not getattr(settings, "BK_APIGW_STAGE_ENABLE_MCP_SERVERS", None):
            return

        # 修改settings的BK_APIGW_STAGE_MCP_SERVERS，是的包含tools
        for server in settings.BK_APIGW_STAGE_MCP_SERVERS:
            server["tools"] = decorators.MCP_TOOLS_REGISTRY.get(server["name"], [])

        definition_file_path = "backend/dbm_init/apigw/mcp_definition.yaml"
        resources_file_path = "backend/dbm_init/apigw/mcp_resources.yaml"

        # 生成mcp资源文件
        try:
            # 添加预处理 hook，只扫描 MCP tools 相关的视图
            spectacular_settings.PREPROCESSING_HOOKS.append(Command.__preprocess_exclude_mcp_views)
            call_command("generate_resources_yaml")
            Command.__move_generated_resources_file("resources.yaml", resources_file_path)
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

        # 如果没有指定任何参数，默认执行 apigw 逻辑（保持向后兼容）
        if apigw or all_mode:
            self.sync_dbm_apigw()

        if mcp or all_mode or only_mcp_resource:
            self.sync_mcp_apigw(only_mcp_resource)
