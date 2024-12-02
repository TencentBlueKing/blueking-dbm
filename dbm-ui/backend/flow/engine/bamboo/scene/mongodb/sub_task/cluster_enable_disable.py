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

from copy import deepcopy
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.db_meta.enums.cluster_type import ClusterType
from backend.flow.consts import MongoDBInstanceType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mongodb.change_instance_status import (
    ChangeInstanceStatusOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.enable_disable_mongodb import (
    EnableDisableMongoDBOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs


def cluster_enable_disable(
    root_id: str, ticket_data: Optional[Dict], sub_kwargs: ActKwargs, cluster_id: int, enable: bool
) -> SubBuilder:
    """
    cluster禁用启用流程
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 设置参数
    sub_get_kwargs.payload["app"] = sub_get_kwargs.payload["bk_app_abbr"]

    # 获取集群信息
    sub_get_kwargs.get_cluster_info_deinstall(cluster_id=cluster_id)
    cluster_type = sub_get_kwargs.payload["cluster_type"]

    # 修改实例状态
    kwargs = {
        "cluster_id": cluster_id,
        "cluster_type": cluster_type,
        "enable": enable,
    }
    sub_pipeline.add_act(
        act_name=_("MongoDB--修改实例状态"), act_component_code=ChangeInstanceStatusOperationComponent.code, kwargs=kwargs
    )

    acts_list = []
    # 启用
    if enable:
        name = "enable"
        if cluster_type == ClusterType.MongoReplicaSet.value:
            for node in sub_get_kwargs.payload["nodes"]:
                kwargs = sub_get_kwargs.get_mongo_start_kwargs(
                    node_info=node,
                    instance_type=MongoDBInstanceType.MongoD.value,
                )
                acts_list.append(
                    {
                        "act_name": _("MongoDB-{}:{}-mongod开启进程".format(node["ip"], str(node["port"]))),
                        "act_component_code": ExecuteDBActuatorJobComponent.code,
                        "kwargs": kwargs,
                    }
                )
        elif cluster_type == ClusterType.MongoShardedCluster.value:
            for mongos in sub_get_kwargs.payload["mongos_nodes"]:
                kwargs = sub_get_kwargs.get_mongo_start_kwargs(
                    node_info=mongos,
                    instance_type=MongoDBInstanceType.MongoS.value,
                )
                acts_list.append(
                    {
                        "act_name": _("MongoDB-{}:{}-mongos开启进程".format(mongos["ip"], str(mongos["port"]))),
                        "act_component_code": ExecuteDBActuatorJobComponent.code,
                        "kwargs": kwargs,
                    }
                )
    # 禁用
    else:
        name = "disable"
        if cluster_type == ClusterType.MongoReplicaSet.value:
            for node in sub_get_kwargs.payload["nodes"]:
                kwargs = sub_get_kwargs.get_mongo_deinstall_kwargs(
                    node_info=node,
                    instance_type=MongoDBInstanceType.MongoD.value,
                    nodes_info=sub_get_kwargs.payload["nodes"],
                    force=True,
                    rename_dir=False,
                )
                acts_list.append(
                    {
                        "act_name": _("MongoDB-{}:{}-mongod关闭进程".format(node["ip"], node["port"])),
                        "act_component_code": ExecuteDBActuatorJobComponent.code,
                        "kwargs": kwargs,
                    }
                )
        elif cluster_type == ClusterType.MongoShardedCluster.value:
            for mongos in sub_get_kwargs.payload["mongos_nodes"]:
                kwargs = sub_get_kwargs.get_mongo_deinstall_kwargs(
                    node_info=mongos,
                    instance_type=MongoDBInstanceType.MongoS.value,
                    nodes_info=[mongos],
                    force=True,
                    rename_dir=False,
                )
                acts_list.append(
                    {
                        "act_name": _("MongoDB-{}:{}-mongos关闭进程".format(mongos["ip"], mongos["port"])),
                        "act_component_code": ExecuteDBActuatorJobComponent.code,
                        "kwargs": kwargs,
                    }
                )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # 修改cluster状态
    kwargs = {"cluster_id": cluster_id, "enable": enable}
    sub_pipeline.add_act(
        act_name=_("修改meta"),
        act_component_code=EnableDisableMongoDBOperationComponent.code,
        kwargs=kwargs,
    )

    return sub_pipeline.build_sub_process(sub_name=_("MongoDB--cluster-{}".format(name)))
