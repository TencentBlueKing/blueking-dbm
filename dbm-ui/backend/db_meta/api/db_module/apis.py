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

from django.db import IntegrityError, transaction
from django.forms import model_to_dict

from backend import env
from backend.components import CCApi
from backend.db_meta import request_validator
from backend.db_meta.enums import ClusterTypeMachineTypeDefine
from backend.db_meta.exceptions import DbModuleExistException
from backend.db_meta.models import AppMonitorTopo, Cluster, ClusterMonitorTopo, DBModule

logger = logging.getLogger("root")


@transaction.atomic
def create(bk_biz_id: int, name: str, cluster_type: str, creator: str = ""):
    """创建DB模块
    说明：这里的模块与cc无任何关系，仅用于关联配置文件，相当于场景化配置模板，比如gamedb,logdb等
    """
    bk_biz_id = request_validator.validated_integer(bk_biz_id, min_value=0)
    name = request_validator.validated_str(name)
    cluster_type = request_validator.validated_str(cluster_type)

    try:
        db_module = DBModule.objects.create(
            bk_biz_id=bk_biz_id,
            cluster_type=cluster_type,
            db_module_name=name,
        )
    except IntegrityError:
        raise DbModuleExistException(db_module_name=name)

    return model_to_dict(db_module)


@transaction.atomic
def get_or_create(
    bk_biz_id: int,
    cluster_id: int,
    cluster_type: str,
    cluster_domain: str,
    creator: str = "",
):
    """创建监控拓扑相关模块"""
    bk_biz_id = request_validator.validated_integer(bk_biz_id, min_value=0)
    cluster_type = request_validator.validated_str(cluster_type)

    machine_topo = {}
    for machine_type in ClusterTypeMachineTypeDefine[cluster_type]:
        app_monitor_topo = AppMonitorTopo.objects.get(bk_biz_id=env.DBA_APP_BK_BIZ_ID, machine_type=machine_type)
        bk_set_id = app_monitor_topo.bk_set_id

        # CCApi.get_or_create_module
        res = CCApi.search_module(
            {
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                "bk_set_id": bk_set_id,
                "condition": {"bk_module_name": cluster_domain},
            },
            use_admin=True,
        )

        if res["count"]:
            module = res["info"][0]
        else:
            module = CCApi.create_module(
                {
                    "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                    "bk_set_id": bk_set_id,
                    "data": {"bk_parent_id": bk_set_id, "bk_module_name": cluster_domain},
                },
                use_admin=True,
            )

        # 保留一份集群监控拓扑数据
        module, created = ClusterMonitorTopo.objects.get_or_create(
            defaults={
                "bk_biz_id": bk_biz_id,
                "creator": creator,
            },
            machine_type=machine_type,
            bk_biz_id=bk_biz_id,
            cluster_id=cluster_id,
            bk_set_id=bk_set_id,
            bk_module_id=module["bk_module_id"],
        )
        machine_topo[machine_type] = module.bk_module_id

    return machine_topo


@transaction.atomic
def get_or_create_influxdb(
    bk_biz_id: int,
    cluster_type: str,
    instance_ip: str,
    instance_id: int,
    creator: str = "",
):
    """
    influxdb专用
    This function is used to create a monitoring topology related module,
    specifically for Influxdb. It requires bk_biz_id, cluster_type, instance_ip,
    instance_id, and creator as parameters. If the module already exists,
    it will retrieve it, and if not, it will create the module.
    Finally, the function will return a dictionary containing machine type and corresponding bk_module_id.
    """

    bk_biz_id = request_validator.validated_integer(bk_biz_id, min_value=0)
    cluster_type = request_validator.validated_str(cluster_type)

    machine_topo = {}
    for machine_type in ClusterTypeMachineTypeDefine[cluster_type]:
        app_monitor_topo = AppMonitorTopo.objects.get(bk_biz_id=env.DBA_APP_BK_BIZ_ID, machine_type=machine_type)
        bk_set_id = app_monitor_topo.bk_set_id

        res = CCApi.search_module(
            {
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                "bk_set_id": bk_set_id,
                "condition": {"bk_module_name": instance_ip},
            },
            use_admin=True,
        )

        if res["count"]:
            module = res["info"][0]
        else:
            module = CCApi.create_module(
                {
                    "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                    "bk_set_id": bk_set_id,
                    "data": {"bk_parent_id": bk_set_id, "bk_module_name": instance_ip},
                },
                use_admin=True,
            )

        # 保留一份集群监控拓扑数据
        module, created = ClusterMonitorTopo.objects.get_or_create(
            defaults={
                "bk_biz_id": bk_biz_id,
                "creator": creator,
            },
            machine_type=machine_type,
            bk_biz_id=bk_biz_id,
            bk_set_id=bk_set_id,
            instance_id=instance_id,
            bk_module_id=module["bk_module_id"],
        )
        machine_topo[machine_type] = module.bk_module_id

    return machine_topo


@transaction.atomic
def delete_cluster_modules(db_type, del_cluster_id: int):
    """
    封装方法：现在bkcc的模块是跟cluster_id、db_type 的结合对应
    根据这些信息删除对应模块, 使用场景是回收集群
    @param db_type: db组件类型
    @param del_cluster_id： 待删除模块所关联的cluster_id
    """
    cluster = Cluster.objects.get(id=del_cluster_id)
    for machine_type in ClusterTypeMachineTypeDefine[cluster.cluster_type]:
        bk_set_id = AppMonitorTopo.objects.get(
            bk_biz_id=env.DBA_APP_BK_BIZ_ID, db_type=db_type, machine_type=machine_type
        ).bk_set_id

        bk_module_obj = ClusterMonitorTopo.objects.get(
            machine_type=machine_type,
            bk_biz_id=cluster.bk_biz_id,
            cluster_id=del_cluster_id,
            bk_set_id=bk_set_id,
        )

        CCApi.delete_module(
            {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "bk_set_id": bk_set_id, "bk_module_id": bk_module_obj.bk_module_id},
        )
        bk_module_obj.delete(keep_parents=True)


@transaction.atomic
def delete_instance_modules(db_type, del_instance_id: int, bk_biz_id: int, cluster_type):
    """
    封装方法：现在bkcc的模块是跟cluster_id、db_type 的结合对应
    根据这些信息删除对应模块, 使用场景是回收集群
    @param db_type: db组件类型
    @param del_instance_id： 待删除模块所关联的ins_id
    @param bk_biz_id： 待删除模块所关联的bk_biz_id
    @param cluster_type： 集群类型
    """
    for machine_type in ClusterTypeMachineTypeDefine[cluster_type]:
        bk_set_id = AppMonitorTopo.objects.get(
            bk_biz_id=env.DBA_APP_BK_BIZ_ID, db_type=db_type, machine_type=machine_type
        ).bk_set_id

        bk_module_obj = ClusterMonitorTopo.objects.get(
            machine_type=machine_type,
            bk_biz_id=bk_biz_id,
            instance_id=del_instance_id,
            bk_set_id=bk_set_id,
        )

        CCApi.delete_module(
            {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "bk_set_id": bk_set_id, "bk_module_id": bk_module_obj.bk_module_id},
        )
        bk_module_obj.delete(keep_parents=True)
