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
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.db_meta.models import StorageInstance, StorageInstanceTuple
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("root")


class MySQLDBHAAFChangeMasterService(BaseService):
    @transaction.atomic
    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")

        bk_cloud_id = kwargs["bk_cloud_id"]
        ro_slave_address = kwargs["ro_slave_address"]
        old_master_address = kwargs["old_master_address"]
        new_master_address = kwargs["new_master_address"]
        new_master_log_file = kwargs["new_master_log_file"]
        new_master_log_pos = kwargs["new_master_log_pos"]

        self.log_info(
            f"read only slave {ro_slave_address}\n"
            + f"old master {old_master_address}\n"
            + f"new master {new_master_address}"
        )

        # ToDo 这里是不是得检查下
        # 1. slave 现在的同步配置
        # 2. slave 现在的同步状态

        change_master_sql = (
            f"change master to "
            f"master_host='{new_master_address.split(':')[0]}',"
            f"master_port={new_master_address.split(':')[1]},"
            f"master_log_file='{new_master_log_file}',"
            f"master_log_pos={new_master_log_pos}"
        )
        self.log_info(change_master_sql)

        # ToDo 这里先不使用幂等同步
        # 如果后续失败率太高, 可以考虑在条件分支添加幂等同步, 然后发个告警
        res = DRSApi.rpc(
            {
                "addresses": [ro_slave_address],
                "cmds": ["stop slave", change_master_sql, "start slave"],
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )

        if res[0]["error_msg"]:
            return False

        for cmdr in res[0]["cmd_results"]:
            if cmdr["error_msg"]:
                return False

        old_master_instance = StorageInstance.objects.get(
            machine__ip=old_master_address.split(":")[0], port=old_master_address.split[":"][1]
        )
        new_master_instance = StorageInstance.objects.get(
            machine__ip=new_master_address.split(":")[0], port=new_master_address.split[":"][1]
        )
        ro_slave_instance = StorageInstance.objects.get(
            machine__ip=ro_slave_address.split(":")[0], port=ro_slave_address.split(":")[1]
        )

        stp = StorageInstanceTuple.objects.get(ejector=old_master_instance, receiver=ro_slave_instance)
        stp.ejector = new_master_instance
        stp.save(update_fields=["ejector"])

        self.log_info(_("同步关系更新完成"))
        return True


class MySQLDBHAAFChangeMasterComponent(Component):
    name = __name__
    code = "mysql_dbha_af_change_master"
    bound_service = MySQLDBHAAFChangeMasterService
