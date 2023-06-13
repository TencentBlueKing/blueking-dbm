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
from dataclasses import asdict, dataclass

from backend import env
from backend.constants import CommonInstanceLabels
from backend.db_meta.api.common import add_service_instance
from backend.db_meta.api.db_module import get_or_create
from backend.db_meta.enums import InstanceRole, MachineType
from backend.db_meta.models import AppCache, Cluster, ClusterMonitorTopo, Machine, StorageInstance
from backend.flow.consts import InstanceFuncAliasEnum
from backend.flow.utils.cc_manage import CcManage
from backend.flow.utils.hdfs.consts import (
    DATANODE_DEFAULT_HTTP_PORT,
    DATANODE_DEFAULT_PORT,
    DATANODE_DEFAULT_RPC_PORT,
    NAME_NODE_DEFAULT_PORT,
)


@dataclass()
# 定义注册HDFS服务监控实例需要的labels标签结构
class HdfsInstanceLabels(CommonInstanceLabels):
    rpc_port: str
    service_rpc_port: str
    jmx_http_port: str
    instance_name: str


def create_bk_module_for_cluster_id(cluster_id: int):
    """
    # 根据cluster_id,创建对应的域名名称模块
    """
    cluster = Cluster.objects.get(id=cluster_id)

    get_or_create(
        bk_biz_id=cluster.bk_biz_id,
        cluster_id=cluster.id,
        cluster_type=cluster.cluster_type,
        cluster_domain=cluster.immute_domain,
        creator=cluster.creator,
    )


def transfer_host_in_cluster_module(cluster_id: int, ip_list: list, machine_type: str, kwargs: dict, bk_cloud_id: int):
    """
    根据机器的ip和machine_type的信息，选择对应的bk_set_id, 并将主机转移到对应cluster模块下
    @param cluster_id: cluster id
    @param ip_list: 待转移的ip 列表
    @param machine_type: 机器的类型
    @param kwargs: 集群创建信息，包含集群自定义端口号
    @param bk_cloud_id: 机器列表所在的云区域，兼容后续跨云管理
    """
    transfer_bk_module_ids = []
    transfer_bk_host_ids = []
    cluster = Cluster.objects.get(id=cluster_id)
    for ip in ip_list:
        machine = Machine.objects.get(ip=ip, bk_cloud_id=bk_cloud_id)
        transfer_bk_host_ids.append(machine.bk_host_id)

    bk_module_obj = ClusterMonitorTopo.objects.get(
        bk_biz_id=cluster.bk_biz_id,
        cluster_id=cluster.id,
        machine_type=machine_type,
    )
    transfer_bk_module_ids.append(bk_module_obj.bk_module_id)

    # 主机转移到对应的模块下，机器可能对应多个集群，所有主机转移到多个模块下是合理的
    # CCApi.transfer_host_module(
    #     {
    #         "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
    #         "bk_host_id": transfer_bk_host_ids,
    #         "bk_module_id": transfer_bk_module_ids,
    #         "is_increment": False,
    #     },
    #     use_admin=True,
    # )

    CcManage.transfer_host_module(transfer_bk_host_ids, transfer_bk_module_ids)

    if machine_type == MachineType.HDFS_MASTER.value:
        # HDFS master机器筛选NameNode实例主机 添加服务实例
        for ins in StorageInstance.objects.filter(
            cluster=cluster, machine__ip__in=ip_list, instance_role=InstanceRole.HDFS_NAME_NODE.value
        ):
            init_hdfs_instance_service(
                cluster=cluster,
                ins=ins,
                bk_module_id=bk_module_obj.bk_module_id,
                instance_role=ins.instance_role,
                func_name=InstanceFuncAliasEnum.HDFS_NAME_NODE_FUNC_ALIAS.value,
                kwargs=kwargs,
            )
    elif machine_type == MachineType.HDFS_DATANODE.value:
        for ins in StorageInstance.objects.filter(
            cluster=cluster, machine__ip__in=ip_list, instance_role=InstanceRole.HDFS_DATA_NODE.value
        ):
            init_hdfs_instance_service(
                cluster=cluster,
                ins=ins,
                bk_module_id=bk_module_obj.bk_module_id,
                instance_role=ins.instance_role,
                func_name=InstanceFuncAliasEnum.HDFS_DATA_NODE_FUNC_ALIAS.value,
                kwargs=kwargs,
            )


def init_hdfs_instance_service(cluster, ins, bk_module_id, instance_role, func_name, kwargs: dict):
    """
    添加服务实例
    """
    rpc_port = DATANODE_DEFAULT_RPC_PORT
    jmx_http_port = DATANODE_DEFAULT_HTTP_PORT
    service_rpc_port = DATANODE_DEFAULT_PORT

    if instance_role == InstanceRole.HDFS_NAME_NODE.value:
        rpc_port = kwargs["rpc_port"]
        jmx_http_port = kwargs["http_port"]
        service_rpc_port = NAME_NODE_DEFAULT_PORT

    instance_labels = asdict(
        HdfsInstanceLabels(
            app=AppCache.get_app_attr(cluster.bk_biz_id, default=cluster.bk_biz_id),
            app_id=str(cluster.bk_biz_id),
            app_name=AppCache.get_app_attr(cluster.bk_biz_id, "db_app_abbr", cluster.bk_biz_id),
            bk_biz_id=str(cluster.bk_biz_id),
            bk_cloud_id=str(cluster.bk_cloud_id),
            cluster_domain=cluster.immute_domain,
            cluster_name=cluster.name,
            cluster_type=cluster.cluster_type,
            instance_role=instance_role,
            instance_host=ins.machine.ip,
            instance=f"{ins.machine.ip}-{ins.port}",
            instance_name=ins.name,
            rpc_port=str(rpc_port),
            jmx_http_port=str(jmx_http_port),
            service_rpc_port=str(service_rpc_port),
        )
    )

    bk_instance_id = add_service_instance(
        bk_module_id=bk_module_id,
        bk_host_id=ins.machine.bk_host_id,
        listen_ip=ins.machine.ip,
        listen_port=ins.port,
        func_name=func_name,
        labels_dict=instance_labels,
    )
    # 保存到数据库
    ins.bk_instance_id = bk_instance_id
    ins.save(update_fields=["bk_instance_id"])
