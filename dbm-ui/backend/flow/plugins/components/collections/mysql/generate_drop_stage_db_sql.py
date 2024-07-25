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

from django.db.transaction import atomic
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.db_services.mysql.sql_import.constants import BKREPO_SQLFILE_PATH, SQLCharset, SQLExecuteTicketMode
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.builders.common.base import fetch_cluster_ids
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


class GenerateDropStageDBSqlService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        """
        bk_cloud_id 统一由私有变量kwargs传入
        """
        global_data = data.get_one_of_inputs("global_data")
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")

        getattr(self, kwargs.get("trans_func"))(global_data, trans_data, kwargs)
        return True

    def write_drop_sql(self, global_data, trans_data, kwargs):
        """往单据detail写入drop sql语句。TODO： 因为目前没有全局的共享上下文，只能写入DB了"""

        # old_new_map = trans_data.old_new_map
        # drop_stage_db_cmds = []
        # for old_db in old_new_map:
        #     stage_db = old_new_map[old_db]
        #     drop_stage_db_cmds.append("drop database if exists `{}`".format(stage_db))

        drop_stage_db_cmds = trans_data.drop_sqls
        self.log_info("[{}] drop stage db cmds: {}".format(kwargs["node_name"], drop_stage_db_cmds))
        # 原子更新：将drop sql语句插入ticket信息中，用后后续ticket flow上下文获取
        with atomic():
            ticket = Ticket.objects.select_for_update().get(id=global_data["uid"])
            drop_cmds = ticket.details.get("drop_stage_db_cmds", [])
            drop_cmds.extend(drop_stage_db_cmds)
            ticket.update_details(drop_stage_db_cmds=drop_cmds)

    @staticmethod
    def generate_dropsql_ticket(global_data, trans_data, kwargs):
        """生成drop语句的变更SQL单据数据"""
        ticket = Ticket.objects.get(id=global_data["uid"])
        bk_biz_id, cluster_ids = global_data["bk_biz_id"], fetch_cluster_ids(global_data["infos"])

        drop_sql_content = ";".join(ticket.details["drop_stage_db_cmds"])
        details = {
            "bk_biz_id": bk_biz_id,
            "cluster_ids": cluster_ids,
            "backup": [],
            "path": BKREPO_SQLFILE_PATH.format(biz=bk_biz_id),
            "charset": SQLCharset.DEFAULT.value,
            "ticket_mode": {"mode": SQLExecuteTicketMode.MANUAL.value},
            "execute_objects": [{"dbnames": ["test"], "ignore_dbnames": [], "sql_content": drop_sql_content}],
        }

        if ticket.ticket_type == TicketType.TENDBCLUSTER_TRUNCATE_DATABASE:
            ticket_type = TicketType.TENDBCLUSTER_FORCE_IMPORT_SQLFILE.value
        else:
            ticket_type = TicketType.MYSQL_FORCE_IMPORT_SQLFILE.value

        Ticket.create_ticket(
            ticket_type=ticket_type,
            creator=global_data["created_by"],
            bk_biz_id=bk_biz_id,
            remark=_("清档自动发起的变更SQL单据\n关联单据：{}").format(ticket.url),
            details=details,
        )


class GenerateDropStageDBSqlComponent(Component):
    name = __name__
    code = "generate_drop_stage_db_sql"
    bound_service = GenerateDropStageDBSqlService
