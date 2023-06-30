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

from django.db import models
from django.forms import model_to_dict
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.models import AuditedModel

from ..enums import ClusterType, MachineType


class Spec(AuditedModel):
    """
    资源规格
    """

    spec_id = models.AutoField(primary_key=True)
    spec_name = models.CharField(max_length=128, help_text=_("虚拟规格名称"))
    spec_cluster_type = models.CharField(
        max_length=64, choices=ClusterType.get_choices(), help_text=_("集群类型:MySQL、Proxy、Spider")
    )
    spec_machine_type = models.CharField(max_length=64, choices=MachineType.get_choices(), help_text=_("机器规格类型"))
    cpu = models.JSONField(null=True, help_text=_("cpu规格描述:{'min':1,'max':10}"))
    mem = models.JSONField(null=True, help_text=_("mem规格描述:{'min':100,'max':1000}"))
    device_class = models.JSONField(null=True, help_text=_("实际机器机型: ['class1','class2'] "))
    storage_spec = models.JSONField(null=True, help_text=_("存储磁盘需求配置:{'mount_point':'/data','size':500,'type':'ssd'}"))
    desc = models.TextField(help_text=_("资源规格描述"), default="")
    # es专属
    instance_num = models.IntegerField(default=1, help_text=_("实例数(es专属)"))

    class Meta:
        index_together = [("spec_cluster_type", "spec_machine_type", "spec_name")]

    def get_apply_params_detail(self, group_mark, count, bk_cloud_id, affinity=None, location_spec=None):
        # 获取资源申请的detail过程，暂时忽略亲和性和位置参数过滤
        return {
            "group_mark": group_mark,
            "bk_cloud_id": bk_cloud_id,
            # "device_class": self.device_class,
            "spec": {"cpu": self.cpu, "ram": self.mem},
            # "storage_spec": self.storage_spec,
            "count": count,
            "affinity": affinity
            # TODO: 暂时忽略location_spec(位置信息)
        }

    def get_spec_info(self):
        # 获取规格的基本信息
        return {
            "id": self.spec_id,
            "name": self.spec_name,
            "cpu": self.cpu,
            "mem": self.mem,
            "device_class": self.device_class,
            "storage_spec": self.storage_spec,
        }


class ClusterDeployPlan(AuditedModel):
    """
    Spider、TendisCache、TendisPlus、TendisSSD 部署方案
    """

    name = models.CharField(max_length=128, default="")
    shard_cnt = models.PositiveIntegerField(default=0, help_text=_("集群分片总数"))
    capacity = models.CharField(max_length=128, default="", help_text=_("集群存储预估总容量/G"))
    machine_pair_cnt = models.PositiveIntegerField(default=0, help_text=_("机器组数: (每组两台)"))
    spec = models.ForeignKey(Spec, on_delete=models.PROTECT)
    cluster_type = models.CharField(help_text=_("集群类型"), choices=ClusterType.get_choices(), max_length=128)
    desc = models.TextField(default="", help_text=_("方案描述"), blank=True, null=True)

    def get_apply_params_details(self, bk_cloud_id, affinity=None, location_spec=None):
        # 获取资源申请的参数，暂时忽略亲和性和位置参数过滤
        backend_group_params = [
            self.spec.get_apply_params_detail(
                group_mark=f"backend_group_{group}",
                count=2,
                bk_cloud_id=bk_cloud_id,
                affinity=affinity,
                location_spec=location_spec,
            )
            for group in range(self.machine_pair_cnt)
        ]
        return backend_group_params

    @property
    def simple_desc(self):
        return model_to_dict(self, ["id", "name", "shard_cnt", "capacity", "machine_pair_cnt", "cluster_type"])


class SnapshotSpec(AuditedModel):
    """
    资源规格快照
    """

    # machine 表在做一个外键关联到快照表
    snapshot_id = models.AutoField(primary_key=True)
    spec_id = models.PositiveIntegerField(null=False)
    spec_name = models.CharField(max_length=128)
    spec_type = models.CharField(max_length=64, default="MySQL")
    cpu = models.JSONField(null=True, help_text=_("cpu规格描述:{'min':1,'max':10}"))
    mem = models.JSONField(null=True, help_text=_("mem规格描述:{'min':100,'max':1000}"))
    device_class = models.JSONField(null=True, help_text=_("实际机器机型: ['class1','class2'] "))
    storage_spec = models.JSONField(null=True)
    desc = models.TextField(default="", help_text=_("资源规格描述"))
