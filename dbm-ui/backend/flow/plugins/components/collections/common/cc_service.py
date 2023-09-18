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
from typing import List

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.db_meta import api
from backend.db_meta.models import BKModule, Cluster, DBModule
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.cc_manage import CcManage

logger = logging.getLogger("flow")


class TransferHostCreateClusterService(BaseService):
    """
    集群创建时，挪动机器模块
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        bk_biz_id = global_data["bk_biz_id"]

        # 注意: 原子入参要求提供cluster_id
        cluster_id = global_data["cluster_id"]
        cluster = Cluster.objects.get(id=cluster_id)

        # 更新DBMeta和创建cc目录，这里如果已经存在，则会报错
        machine_topo = api.db_module.get_or_create(
            bk_biz_id=bk_biz_id,
            cluster_id=cluster_id,
            cluster_type=cluster.cluster_type,
            cluster_name=cluster.name,
            cluster_domain=cluster.immute_domain,
        )

        ip_modules = []
        for info in kwargs["cluster"]["machine_list"]:
            ips = getattr(trans_data, info["ips_var_name"])
            #  将哪批机器转移到哪个模块
            ip_modules.append({"ips": ips, "bk_module_id": machine_topo[info["machine_type"]]})

        CcManage.transfer_machines(bk_biz_id, cluster.bk_cloud_id, ip_modules)

        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
            Service.InputItem(name="trans_data", key="trans_data", type="dict", required=True),
        ]


class TransferHostCreateClusterComponent(Component):
    name = __name__
    code = "transfer_host"
    bound_service = TransferHostCreateClusterService


class TransferHostDestroyClusterService(BaseService):
    """
    集群销毁时，挪动机器模块
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        ips = kwargs["cluster"]["ips"]
        CcManage.transfer_machines_idle(ips)
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
            Service.InputItem(name="trans_data", key="trans_data", type="dict", required=True),
        ]


class TransferHostDestroyClusterComponent(Component):
    name = __name__
    code = "transfer_host_destroy"
    bound_service = TransferHostDestroyClusterService


class TransferHostScaleService(BaseService):
    """
    集群扩缩容，移动模块
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        bk_biz_id = global_data["bk_biz_id"]
        cluster_type = kwargs["cluster"]["cluster_type"]
        module_name = kwargs["cluster"]["cluster_name"]

        db_module_id = DBModule.objects.get(
            bk_biz_id=bk_biz_id, cluster_type=cluster_type, db_module_name=module_name
        ).db_module_id

        machine_list = kwargs["cluster"]["machine_list"]
        ip_modules = []
        for info in machine_list:
            machine_type = info["machine_type"]
            ips = info["ips"]
            bk_module_id = BKModule.objects.get(db_module_id=db_module_id, machine_type=machine_type).bk_module_id
            #  将哪批机器转移到哪个模块
            ip_modules.append({"ips": ips, "bk_module_id": bk_module_id})

        CcManage.transfer_machines(bk_biz_id, kwargs["bk_cloud_id"], ip_modules)
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
            Service.InputItem(name="trans_data", key="trans_data", type="dict", required=True),
        ]


class TransferHostScaleComponent(Component):
    name = __name__
    code = "transfer_host_scale"
    bound_service = TransferHostScaleService
