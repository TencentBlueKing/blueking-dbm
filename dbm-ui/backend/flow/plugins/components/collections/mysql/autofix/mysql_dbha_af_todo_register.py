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
from datetime import datetime, timezone

from django.db import transaction
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.configuration.constants import DisableDBHAAutofixLevel, SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.enums import MachineType
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.db_monitor.models import MySQLDBHAEvent
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("celery")


def is_autofix_disabled(row: dict, cluster_obj) -> bool:
    """
    判断该事件是否命中自愈禁用规则。

    rules 来自 SystemSettings DISABLE_DBHA_AUTOFIX_APPS, 结构为 list[dict]:
    [
        {
            "bk_biz_id": int,             # (必填) 业务ID
            "cluster_type": str,          # (必填) 集群类型, 如 "tendbha", "tendbcluster"
            "disable_level": str,         # (必填) 禁用级别: "cluster_type" | "cluster" | "machine_type"
            "disable_value": str/int,     # disable_level 为 "cluster_type" 时无意义;
                                          #   为 "cluster" 时填 cluster_id;
                                          #   为 "machine_type" 时填 machine_type 字符串, 如 "proxy", "backend"
        }
    ]
    """
    rules: list[dict] = SystemSettings.get_setting_value(SystemSettingsEnum.DISABLE_DBHA_AUTOFIX_APPS.value) or []
    for rule in rules:
        if rule["bk_biz_id"] != row["bk_biz_id"]:
            continue
        if rule["cluster_type"] != cluster_obj.cluster_type:
            continue

        level = rule["disable_level"]
        value = rule.get("disable_value", "")

        if level == DisableDBHAAutofixLevel.CLUSTER_TYPE:
            return True
        elif level == DisableDBHAAutofixLevel.CLUSTER and value == cluster_obj.pk:
            return True
        elif level == DisableDBHAAutofixLevel.MACHINE_TYPE and value == row["machine_type"]:
            return True

    return False


class MySQLDBHAAFTodoRegisterService(BaseService):
    @transaction.atomic
    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")

        for row in kwargs["infos"]:
            self.log_info("[{}] mysql autofix info row: {}".format(kwargs["node_name"], row))

            cluster_obj = Cluster.objects.get(
                bk_cloud_id=row["bk_cloud_id"], bk_biz_id=row["bk_biz_id"], immute_domain=row["immute_domain"]
            )

            if is_autofix_disabled(row, cluster_obj):
                self.log_info(
                    "[{}] mysql autofix info row: {} skipped by disable rule".format(kwargs["node_name"], row)
                )
                continue

            if row["machine_type"] in [MachineType.PROXY, MachineType.SPIDER]:
                ProxyInstance.objects.get(cluster=cluster_obj, machine__ip=row["ip"], port=row["port"])
            elif row["machine_type"] in [MachineType.BACKEND, MachineType.REMOTE]:
                StorageInstance.objects.get(cluster=cluster_obj, machine__ip=row["ip"], port=row["port"])
            else:
                self.log_error("unsupported machine_type: {}".format(row["machine_type"]))
                continue

            # 蓝鲸监控默认使用 utc 时区, 但是时间又没有时区信息
            event_create_time_str = row["event_create_time"]
            event_create_time_dt = datetime.strptime(event_create_time_str, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc
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
                "event_create_time": event_create_time_dt,  # row["event_create_time"],
                "instance_role": row["instance_role"],
                "new_master_host": row["new_master_host"],
                "new_master_port": row["new_master_port"],
                "new_master_log_file": row["new_master_log_file"],
                "new_master_log_pos": row["new_master_log_pos"],
            }

            # 按表唯一键做 replace 操作, 防止实例重复上报
            MySQLDBHAEvent.objects.update_or_create(
                defaults=new_record,
                check_id=new_record["check_id"],
                ip=new_record["ip"],
                port=new_record["port"],
            )

        self.log_info(_("[{}] 自愈信息写入完成".format(kwargs["node_name"])))
        return True


class MySQLDBHAAFTodoRegisterComponent(Component):
    name = __name__
    code = "mysql_dbha_af_todo_register"
    bound_service = MySQLDBHAAFTodoRegisterService
