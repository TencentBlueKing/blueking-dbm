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

from django.db import transaction
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.db_meta.models import Cluster
from backend.db_monitor.models import MySQLAutofixTodo
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("celery")


class MySQLAutofixTodoRegisterService(BaseService):
    @transaction.atomic
    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")

        for row in kwargs["infos"]:
            self.log_info("[{}] mysql autofix info row: {}".format(kwargs["node_name"], row))
            cluster_obj = Cluster.objects.get(
                bk_cloud_id=row["bk_cloud_id"], bk_biz_id=row["bk_biz_id"], immute_domain=row["immute_domain"]
            )

            new_record = {
                "bk_cloud_id": row["bk_cloud_id"],
                "bk_biz_id": row["bk_biz_id"],
                "check_id": row["check_id"],
                "cluster_id": cluster_obj.pk,
                "immute_domain": row["immute_domain"],
                "cluster_type": cluster_obj.cluster_type,
                "machine_type": row["machine_type"],
                "ip": row["ip"],
                "port": row["port"],
                "event_create_time": row["event_create_time"],
            }

            # 按表唯一键做 replace 操作, 防止实例重复上报
            MySQLAutofixTodo.objects.update_or_create(
                defaults=new_record,
                check_id=new_record["check_id"],
                ip=new_record["ip"],
                port=new_record["port"],
            )

        self.log_info(_("[{}] 自愈信息写入完成".format(kwargs["node_name"])))
        return True


class MySQLAutofixTodoRegisterComponent(Component):
    name = __name__
    code = "mysql_autofix_todo_register"
    bound_service = MySQLAutofixTodoRegisterService
