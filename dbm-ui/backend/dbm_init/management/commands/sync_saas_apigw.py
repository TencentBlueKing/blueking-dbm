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

from django.core.management import call_command
from django.core.management.base import BaseCommand

from backend import env

logger = logging.getLogger("root")


class Command(BaseCommand):
    def handle(self, *args, **kwargs):

        definition_file_path = "backend/dbm_init/apigw/definition.yaml"
        resources_file_path = "backend/dbm_init/apigw/resources.yaml"

        # 同步网关基本信息
        logger.info("call sync_apigw_config with definition: %s" % definition_file_path)
        call_command("sync_apigw_config", file=definition_file_path)

        # 同步网关环境信息
        logger.info("call sync_apigw_stage with definition: %s" % definition_file_path)
        call_command("sync_apigw_stage", file=definition_file_path)

        # 为应用主动授权
        logger.info("call grant_apigw_permissions with definition: %s" % definition_file_path)
        call_command("grant_apigw_permissions", file=definition_file_path)

        # 同步网关资源
        logger.info("call sync_apigw_resources with resources: %s" % resources_file_path)
        call_command("sync_apigw_resources", file=resources_file_path)

        # 同步资源文档
        if env.BK_APIGW_RESOURCE_DOCS_BASE_DIR:
            logger.info("call sync_resource_docs_by_archive with definition: %s" % definition_file_path)
            call_command("sync_resource_docs_by_archive", file=definition_file_path)

        # 获取网关公钥
        logger.info("call fetch_apigw_public_key")
        call_command("fetch_apigw_public_key")
