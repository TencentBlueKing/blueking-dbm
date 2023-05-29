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
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster, StorageInstance, StorageInstanceTuple
from backend.flow.plugins.components.collections.common.base_service import BaseService


class MysqlMasterSlaveRelationshipCheckService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data") or {}
        master = global_data["master"]
        slaves = global_data["slaves"]

        master_instance, ok = self._get_storage_instance(master["id"], global_data["bk_biz_id"])
        if not ok:
            self.log_error("instance not found: id {}".format(master["id"]))
            return False
        if ok and (master_instance.instance_inner_role not in [InstanceInnerRole.MASTER, InstanceInnerRole.REPEATER]):
            self.log_error(
                "instance {}{}{} role should be master or repeater, not be {}".format(
                    master["ip"],
                    IP_PORT_DIVIDER,
                    master["port"],
                    master_instance.instance_inner_role,
                )
            )

        try:
            tuples = StorageInstanceTuple.objects.filter(ejector=master["id"]).values()
        except ObjectDoesNotExist:
            self.log_error(
                "「 bk_biz_id = {}, cluster_type = {}, instance = {}{}{} 」 has no slave".format(
                    global_data["bk_biz_id"],
                    ClusterType.TenDBHA.value,
                    master["ip"],
                    IP_PORT_DIVIDER,
                    master["port"],
                )
            )
            return False

        receivers = [v_tuple["receiver_id"] for v_tuple in tuples]
        for slave in slaves:
            if slave["id"] not in receivers:
                self.log_error(
                    "「 bk_biz_id = {}, cluster_type = {}, instance = {}{}{} and instance = {}{}{} 」"
                    " have no master slave relationship".format(
                        global_data["bk_biz_id"],
                        ClusterType.TenDBHA.value,
                        master["ip"],
                        IP_PORT_DIVIDER,
                        master["port"],
                        slave["ip"],
                        IP_PORT_DIVIDER,
                        slave["port"],
                    )
                )
                return False
        self.log_info(_("主备关系校验成功"))
        return True

    def _get_storage_instance(self, ins_id, bk_biz_id):
        try:
            storage_instance = StorageInstance.objects.get(id=ins_id, bk_biz_id=bk_biz_id)
            return storage_instance, True
        except ObjectDoesNotExist:
            self.log_error("storage instance 「 bk_biz_id = {}, id = {} 」 not exists".format(bk_biz_id, ins_id))
            return None, False


class MysqlMasterSlaveRelationshipCheckServiceComponent(Component):
    name = __name__
    code = "mysql_master_slave_relationship_check"
    bound_service = MysqlMasterSlaveRelationshipCheckService
