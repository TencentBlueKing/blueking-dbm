"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from pipeline.component_framework.component import Component

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.cc_manage import CcManage


class DelCCServiceInstService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        """
        根据cluster_id、ip:port删除对应服务实例
        """
        kwargs = data.get_one_of_inputs("kwargs")
        cluster_id = kwargs["cluster_id"]
        del_instance_list = kwargs["del_instance_list"]

        cluster = Cluster.objects.get(id=cluster_id)
        db_type = ClusterType.cluster_type_to_db_type(cluster.cluster_type)
        for instance in del_instance_list:
            if cluster.proxyinstance_set.filter(machine__ip=instance["ip"], port=instance["port"]).exists():
                # 一个集群有却只有一个proxy类型实例
                proxy = cluster.proxyinstance_set.get(machine__ip=instance["ip"], port=instance["port"])
                CcManage(proxy.bk_biz_id, db_type).delete_service_instance(bk_instance_ids=[proxy.bk_instance_id])

            if cluster.storageinstance_set.filter(machine__ip=instance["ip"], port=instance["port"]).exists():
                # 一个集群有却只有一个storage类型实例
                storage = cluster.storageinstance_set.get(machine__ip=instance["ip"], port=instance["port"])
                CcManage(storage.bk_biz_id, db_type).delete_service_instance(bk_instance_ids=[storage.bk_instance_id])

        return True


class DelCCServiceInstComponent(Component):
    name = __name__
    code = "delete_cc_service_instance"
    bound_service = DelCCServiceInstService
