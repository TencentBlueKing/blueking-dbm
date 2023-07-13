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
from typing import Dict

from django.db import models
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.models import AuditedModel

from ...constants import INT_MAX
from ...db_services.ipchooser.constants import DEVICE_CLASS
from ...ticket.constants import AffinityEnum
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
    desc = models.TextField(help_text=_("资源规格描述"), null=True, blank=True)
    # es专属
    instance_num = models.IntegerField(default=0, help_text=_("实例数(es专属)"))
    # spider，redis集群专属
    qps = models.JSONField(default=dict, help_text=_("qps规格描述:{'min': 1, 'max': 100}"))

    class Meta:
        index_together = [("spec_cluster_type", "spec_machine_type", "spec_name")]

    @property
    def capacity(self):
        """
        根据不同集群类型，计算该规格的容量
        TendbCluster: 如果只有/data数据盘，则容量/2; 如果有/data和/data1数据盘，则按照/data1为准
        TendisPlus: 一定有两块盘，以/data1为准
        TendisCache: 以内存为准，内存不是范围，是一个准确的值
        默认：磁盘总容量
        """
        mount_point__size: Dict[str, int] = {disk["mount_point"]: disk["size"] for disk in self.storage_spec}
        if self.spec_cluster_type == ClusterType.TenDBCluster:
            return mount_point__size.get("data1") or mount_point__size["/data"] / 2
        elif self.spec_cluster_type in [
            ClusterType.TwemproxyTendisSSDInstance,
            ClusterType.TendisPredixyTendisplusCluster,
        ]:
            return mount_point__size["/data1"]
        elif self.spec_cluster_type == ClusterType.TendisTwemproxyRedisInstance:
            # 取min, max都一样
            return self.mem["min"]
        else:
            return sum(mount_point__size.values())

    def get_apply_params_detail(self, group_mark, count, bk_cloud_id, affinity=AffinityEnum.NONE, location_spec=None):
        # 获取资源申请的detail过程，暂时忽略亲和性和位置参数过滤
        return {
            "group_mark": group_mark,
            "bk_cloud_id": bk_cloud_id,
            "device_class": self.device_class,
            "spec": {
                "cpu": self.cpu,
                # 内存GB-->MB
                "ram": {"min": self.mem["min"] * 1024, "max": self.mem["max"] * 1024},
            },
            "storage_spec": [
                {
                    "mount_point": storage_spec["mount_point"],
                    # 如果是all，则需要传空
                    "disk_type": "" if storage_spec["type"] == "ALL" else storage_spec["type"],
                    "min": storage_spec["size"],
                    "max": INT_MAX,
                }
                for storage_spec in self.storage_spec
            ],
            "count": count,
            "affinity": affinity
            # TODO: 暂时忽略location_spec(位置信息)
        }

    def get_backend_group_apply_params_detail(self, bk_cloud_id, backend_group):
        # 专属于后端：如果一组master/slave有特殊要求，则采用backend_group申请
        backend_group_params = [
            self.get_apply_params_detail(
                group_mark=f"backend_group_{group}",
                count=2,
                bk_cloud_id=bk_cloud_id,
                affinity=backend_group.get("affinity", AffinityEnum.NONE),
                location_spec=backend_group.get("location_spec", None),
            )
            for group in range(backend_group["count"])
        ]
        return backend_group_params

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
