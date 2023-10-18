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


from django.db import transaction
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.db_meta.enums import ClusterPhase, InstancePhase
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.flow.plugins.components.collections.common.base_service import BaseService


class MySQLHAModifyClusterPhaseService(BaseService):
    @transaction.atomic
    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")

        cluster_ids = trans_data.cluster_ids

        Cluster.objects.filter(id__in=cluster_ids).update(phase=ClusterPhase.ONLINE.value)
        ProxyInstance.objects.filter(cluster__in=cluster_ids).update(phase=InstancePhase.ONLINE.value)
        StorageInstance.objects.filter(cluster__in=cluster_ids).update(phase=InstancePhase.ONLINE.value)

        self.log_info(_("[{}] 修改集群状态完成".format(kwargs["node_name"])))
        return True


class MySQLHAModifyClusterPhaseComponent(Component):
    name = __name__
    code = "mysql_ha_modify_cluster_phase"
    bound_service = MySQLHAModifyClusterPhaseService
