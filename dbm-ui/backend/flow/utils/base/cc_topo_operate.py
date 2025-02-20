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
from collections import defaultdict
from dataclasses import asdict
from typing import Dict, List, Union

from django.db.models import QuerySet

from backend.configuration.models import BizSettings
from backend.constants import CommonInstanceLabels
from backend.db_meta.enums import AccessLayer, ClusterType, MachineType
from backend.db_meta.models import (
    AppCache,
    Cluster,
    ClusterMonitorTopo,
    ExtraProcessInstance,
    Machine,
    ProxyInstance,
    StorageInstance,
)
from backend.db_meta.models.cluster_monitor import INSTANCE_MONITOR_PLUGINS
from backend.exceptions import ValidationError
from backend.flow.utils.cc_manage import CcManage, trigger_operate_collector

logger = logging.getLogger("flow")


class CCTopoOperator:
    db_type = None

    def __init__(self, cluster: Union[Cluster, List[Cluster]], ticket_data: dict = None):
        """
        支持单集群/多集群两种模式
        大部分情况下一台主机只属于一个集群
        单机多实例的场景，允许一台机器有多个集群，如 MySQL 的场景
        这里统一当做多集群处理
        """
        if self.db_type is None:
            raise NotImplementedError("db_type can not be None")

        if isinstance(cluster, Cluster):
            self.clusters: List[Cluster] = [cluster]
        else:
            self.clusters: List[Cluster] = cluster
        self.ticket_data = ticket_data or {}

        # 仅允许同一业务的集群操作
        bk_biz_ids = list(set([cluster.bk_biz_id for cluster in self.clusters]))
        if len(bk_biz_ids) != 1:
            raise ValidationError("different cluster biz is not supporting")

        self.bk_biz_id = bk_biz_ids[0]
        # 仅允许同一类型的集群操作
        if isinstance(cluster, Cluster):
            self.hosting_biz_id = BizSettings.get_exact_hosting_biz(self.bk_biz_id, cluster.cluster_type)
        else:
            cluster_types = list(set([cls.cluster_type for cls in cluster]))
            if len(cluster_types) != 1:
                raise ValidationError("different cluster type is not supporting")
            self.hosting_biz_id = BizSettings.get_exact_hosting_biz(self.bk_biz_id, cluster_types[0])

        self.is_bk_module_created = False

    def create_bk_module(self):
        """
        # 根据cluster_id,创建对应的域名名称模块
        """
        if self.db_type is None:
            raise NotImplementedError(f"{self.__module__}db_type is not define")
        for cluster in self.clusters:
            CcManage(bk_biz_id=cluster.bk_biz_id, cluster_type=cluster.cluster_type).get_or_create_set_module(
                db_type=self.db_type,
                cluster_type=cluster.cluster_type,
                bk_module_name=cluster.immute_domain,
                cluster_id=cluster.id,
                creator=cluster.creator,
            )
        # 创建完成后进行缓存，不重复检查和创建
        self.is_bk_module_created = True

    def transfer_instances_to_cluster_module(
        self, instances: Union[List[StorageInstance], List[ProxyInstance], QuerySet], is_increment=False
    ):
        """
        @params instances 实例列表
        @params is_increment 是否为增量操作，即主机处于多模块
        转移实例到对应的集群模块下，并添加服务实例
        """
        if not self.is_bk_module_created:
            self.create_bk_module()

        cluster_ids = [cluster.id for cluster in self.clusters]
        # 获取cluster_types_list
        cluster_types = Cluster.objects.filter(id__in=cluster_ids).values_list("cluster_type", flat=True).distinct()
        cluster_types_list = list(cluster_types)
        # 根据机器类型对实例进行分组
        machine_type_instances_map: Dict[str, List[Union[StorageInstance, ProxyInstance]]] = defaultdict(list)
        for ins in instances:
            machine_type_instances_map[ins.machine_type].append(ins)

        for machine_type, ins_list in machine_type_instances_map.items():
            bk_host_ids = list(set([ins.machine.bk_host_id for ins in ins_list]))

            bk_module_ids = list(
                ClusterMonitorTopo.objects.filter(cluster_id__in=cluster_ids, machine_type=machine_type).values_list(
                    "bk_module_id", flat=True
                )
            )
            # 批量转移主机
            for cluster_type in cluster_types_list:
                CcManage(self.bk_biz_id, cluster_type).transfer_host_module(bk_host_ids, bk_module_ids, is_increment)
            # 创建 CMDB 服务实例
            bk_instance_ids = self.init_instances_service(machine_type, ins_list)
            trigger_operate_collector(self.db_type, machine_type, bk_instance_ids)

    def init_instances_service(self, machine_type, instances=None):
        """
        创建服务实例
        """
        cluster_module_id_map = {}
        func_name = INSTANCE_MONITOR_PLUGINS[self.db_type][machine_type]["func_name"]
        bk_instance_ids = []
        for ins in instances:
            cluster = ins.cluster.first()
            # 查询实例对应的模块 ID
            bk_module_id = cluster_module_id_map.get(cluster.id)
            if not bk_module_id:
                bk_module_id = ClusterMonitorTopo.objects.get(
                    bk_biz_id=self.hosting_biz_id, cluster_id=cluster.id, machine_type=machine_type
                ).bk_module_id
                cluster_module_id_map[cluster.id] = bk_module_id

            # 写入服务实例
            bk_instance_id = self.init_instance_service(
                cluster=cluster,
                ins=ins,
                bk_module_id=bk_module_id,
                instance_role=self.generate_ins_instance_role(ins),
                func_name=func_name,
            )
            bk_instance_ids.append(bk_instance_id)
        return bk_instance_ids

    def init_unique_service(self, machine_type):
        """
        适配部分场景下，某种 machine_type 只需要一个服务实例的情况
        """
        bk_instance_ids = []
        for cluster in self.clusters:
            # 若服务实例存在，忽略即可
            if (
                StorageInstance.objects.filter(cluster=cluster, machine_type=machine_type)
                .exclude(bk_instance_id=0)
                .exists()
            ):
                continue

            # 若服务实例不存在，则添加
            func_name = INSTANCE_MONITOR_PLUGINS[self.db_type][machine_type]["func_name"]
            bk_module_id = ClusterMonitorTopo.objects.get(
                bk_biz_id=self.hosting_biz_id, cluster_id=cluster.id, machine_type=machine_type
            ).bk_module_id
            instance = StorageInstance.objects.filter(cluster=cluster, machine_type=machine_type).first()

            # 写入服务实例
            bk_instance_id = self.init_instance_service(
                cluster=cluster,
                ins=instance,
                bk_module_id=bk_module_id,
                instance_role=instance.instance_role,
                func_name=func_name,
            )
            bk_instance_ids.append(bk_instance_id)
        return bk_instance_ids

    @staticmethod
    def generate_ins_instance_role(ins: Union[StorageInstance, ProxyInstance]):
        """
        生成服务实例的 instance role
        """
        return ins.instance_role if ins.access_layer == AccessLayer.STORAGE else AccessLayer.PROXY.value

    def generate_ins_labels(
        self, cluster: Cluster, ins: Union[StorageInstance, ProxyInstance], instance_role: str
    ) -> dict:
        """
        生成服务实例标签
        """
        labels = asdict(
            CommonInstanceLabels(
                app=AppCache.get_app_attr(cluster.bk_biz_id, default=cluster.bk_biz_id),
                appid=str(cluster.bk_biz_id),
                app_name=AppCache.get_app_attr(cluster.bk_biz_id, "db_app_abbr", cluster.bk_biz_id),
                bk_biz_id=str(cluster.bk_biz_id),
                bk_cloud_id=str(cluster.bk_cloud_id),
                cluster_domain=cluster.immute_domain,
                cluster_name=cluster.name,
                cluster_type=cluster.cluster_type,
                instance_role=instance_role,
                instance_host=ins.machine.ip,
                instance_port=str(ins.port),
                db_module=str(cluster.db_module_id),
                instance=f"{ins.machine.ip}-{ins.port}",
            )
        )
        labels.update(self.generate_custom_labels(ins))
        return labels

    def generate_custom_labels(self, ins: Union[StorageInstance, ProxyInstance]) -> dict:
        """
        生成自定义标签，即 CommonInstanceLabels 不满足的标签
        如 DB 组件无额外标签，则不需要定义
        """
        return {}

    def init_instance_service(
        self,
        cluster: Cluster,
        ins: Union[StorageInstance, ProxyInstance],
        bk_module_id: int,
        instance_role: str,
        func_name: str,
    ):
        """
        添加服务实例
        """
        inst_labels = self.generate_ins_labels(cluster, ins, instance_role)

        bk_instance_id = CcManage(self.bk_biz_id, cluster.cluster_type).add_service_instance(
            bk_module_id=bk_module_id,
            bk_host_id=ins.machine.bk_host_id,
            listen_ip=ins.machine.ip,
            listen_port=ins.port,
            func_name=func_name,
            bk_process_name=f"{self.db_type}-{ins.machine_type}",
            labels_dict=inst_labels,
        )
        # 保存到数据库
        ins.bk_instance_id = bk_instance_id
        ins.save(update_fields=["bk_instance_id"])
        return bk_instance_id

    def create_tbinlogdumper_instances(self, instances: List[ExtraProcessInstance]):
        """
        tbinlogdumper专属，注册服务实例，自动下发exporter采集性能数据
        @param instances: 待添加的tbinlogdumper实例
        """
        # 按照集群信息生成对应的模块
        for cluster in self.clusters:
            CcManage(bk_biz_id=cluster.bk_biz_id, cluster_type=cluster.cluster_type).get_or_create_set_module(
                db_type=self.db_type,
                cluster_type=ClusterType.TBinlogDumper.value,
                bk_module_name=cluster.immute_domain,
                cluster_id=cluster.id,
                creator=cluster.creator,
            )

        inst_id_to_host_id_map = {}
        inst_id_to_module_id_map = {}
        for inst in instances:
            inst_id_to_host_id_map[inst.id] = Machine.objects.get(ip=inst.ip, bk_cloud_id=inst.bk_cloud_id).bk_host_id
            inst_id_to_module_id_map[inst.id] = ClusterMonitorTopo.objects.get(
                cluster_id=inst.cluster_id, machine_type=MachineType.TBinlogDumper.value
            ).bk_module_id

        # 合并导入机器到对应模块下
        cc_manage = CcManage(self.bk_biz_id, ClusterType.TenDBHA.value)
        cc_manage.transfer_host_module(
            bk_host_ids=list(filter(None, list(set(inst_id_to_host_id_map.values())))),
            target_module_ids=list(filter(None, list(set(inst_id_to_module_id_map.values())))),
            is_increment=True,
        )

        # 创建 CMDB 服务实例
        for inst in instances:
            # 写入服务实
            bk_instance_id = cc_manage.add_service_instance(
                bk_module_id=inst_id_to_module_id_map[inst.id],
                bk_host_id=inst_id_to_host_id_map[inst.id],
                listen_ip=inst.ip,
                listen_port=inst.listen_port,
                func_name=INSTANCE_MONITOR_PLUGINS[self.db_type]["tbinlogdumper"]["func_name"],
                bk_process_name=f"{self.db_type}-{'tbinlogdumper'}",
                labels_dict={
                    "exporter_conf_path": f"exporter_{inst.listen_port}.cnf",
                    "appid": str(inst.bk_biz_id),
                },
            )
            inst.bk_instance_id = bk_instance_id
            inst.save(update_fields=["bk_instance_id"])
