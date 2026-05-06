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
import logging

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend import env
from backend.db_meta.models import Cluster
from backend.db_services.mysql.sql_import.constants import BKREPO_SQLFILE_PATH
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class DisplaySemanticCheckInfoService(BaseService):
    """
    显示SQL语义检测单据信息
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        cluster_ids = kwargs.get("cluster_ids", [])
        execute_objects = kwargs.get("execute_objects", [])
        bk_biz_id = kwargs.get("bk_biz_id")
        charset = kwargs.get("charset", "")

        # 获取集群域名
        clusters = Cluster.objects.filter(id__in=cluster_ids)
        cluster_domains = [cluster.immute_domain for cluster in clusters]

        # 构建bkrepo文件路径
        file_path = BKREPO_SQLFILE_PATH.format(biz=bk_biz_id)
        bkrepo_frontend_url = env.BKREPO_FRONTEND_URL.rstrip("/")
        bkrepo_project = env.BKREPO_PROJECT
        bkrepo_bucket = env.BKREPO_BUCKET

        # 输出格式化的日志信息
        self.log_info("=" * 60)
        self.log_info(_("SQL语义检测单据信息回显"))
        self.log_info("=" * 60)
        self.log_info("")
        self.log_info(_("📋 模拟执行信息"))
        self.log_info("-" * 60)
        self.log_info("")
        self.log_info(_("🎯 目标集群："))
        for domain in cluster_domains:
            self.log_info(f"   • {domain}")
        self.log_info("")
        self.log_info(_("🔤 字符集："))
        self.log_info(f"   • {charset}")
        self.log_info("")
        self.log_info(_("📊 变更对象详情："))
        self.log_info("-" * 60)
        self.log_info("")

        # 遍历每个执行对象
        for idx, execute_obj in enumerate(execute_objects):
            line_id = execute_obj.get("line_id", idx)
            dbnames = execute_obj.get("dbnames", [])
            ignore_dbnames = execute_obj.get("ignore_dbnames", [])
            sql_files = execute_obj.get("sql_files", [])
            import_mode = execute_obj.get("import_mode", "")

            self.log_info(_("   单据行 #{}").format(line_id))
            self.log_info("   ┌─────────────────────────────────────────────────────────┐")
            self.log_info(_("   │ ✅ 变更数据库:"))
            if dbnames:
                for dbname in dbnames:
                    self.log_info(f"   │    • {dbname}")
            else:
                self.log_info(_("   │    • 无"))
            self.log_info("   │")
            self.log_info(_("   │ ⛔ 忽略数据库:"))
            if ignore_dbnames:
                for ignore_dbname in ignore_dbnames:
                    self.log_info(f"   │    • {ignore_dbname}")
            else:
                self.log_info(_("   │    • 无"))
            self.log_info("   │")
            self.log_info(_("   │ 📁 SQL文件:"))
            if sql_files:
                for sql_file in sql_files:
                    # 构建bkrepo文件链接
                    file_url = f"{bkrepo_frontend_url}/generic/{bkrepo_project}/{bkrepo_bucket}/{file_path}/{sql_file}"
                    link_html = _("<a href='{}' target='_blank'>{}</a>").format(file_url, sql_file)
                    self.log_info(f"   │    • {link_html}")
            else:
                self.log_info(_("   │    • 无"))
            self.log_info("   │")
            if import_mode:
                self.log_info(_("   │ 📝 导入模式: {}").format(import_mode))
            self.log_info("   └─────────────────────────────────────────────────────────┘")
            if idx < len(execute_objects) - 1:
                self.log_info("")

        self.log_info("")
        self.log_info("=" * 60)

        return True


class DisplaySemanticCheckInfoComponent(Component):
    name = _("显示SQL语义检测单据信息")
    code = "display_semantic_check_info"
    bound_service = DisplaySemanticCheckInfoService
