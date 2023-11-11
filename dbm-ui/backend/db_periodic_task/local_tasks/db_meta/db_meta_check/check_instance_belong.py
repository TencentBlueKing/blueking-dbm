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

from django.db.models import Count, Q, QuerySet
from django.utils.translation import ugettext_lazy as _

from backend.db_meta.models import ProxyInstance, StorageInstance
from backend.db_report.enums import MetaCheckSubType
from backend.db_report.models import MetaCheckReport


def check_instance_belong():
    """
    所有实例都应该属于唯一一个集群
    """
    _instance_belong(StorageInstance.objects.all())
    _instance_belong(ProxyInstance.objects.all())


def _instance_belong(qs: QuerySet):
    for ins in qs.annotate(cluster_count=Count("cluster")).filter(~Q(cluster_count=1)):
        if ins.cluster.exists():  # 大于 1 个集群
            msg = _("{} 属于 {} 个集群".format(ins.ip_port(), ins.cluster.count()))  # ToDo 详情
        else:  # 不属于任何集群
            msg = _("{} 不属于任何集群".format(ins.ip_port()))

        MetaCheckReport.objects.create(
            bk_biz_id=ins.bk_biz_id,
            bk_cloud_id=ins.machine.bk_cloud_id,
            ip=ins.machine.ip,
            port=ins.port,
            cluster_type=ins.cluster_type,
            machine_type=ins.machine.machine_type,
            status=False,
            msg=msg,
            subtype=MetaCheckSubType.InstanceBelong.value,
        )
