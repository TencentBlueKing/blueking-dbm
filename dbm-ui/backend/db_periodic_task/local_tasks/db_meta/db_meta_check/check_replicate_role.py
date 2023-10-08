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
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext_lazy as _

from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.models import StorageInstanceTuple
from backend.db_report.enums import MetaCheckSubType
from backend.db_report.models import MetaCheckReport


def check_replicate_role():
    """
    ejector 只能是 master, repeater; 即不能是 slave
    receiver 只能是 slave, repeater; 即不能是 master
    """
    for bad_ejector_tuple in StorageInstanceTuple.objects.filter(
        ejector__instance_inner_role=InstanceInnerRole.SLAVE.value
    ):
        ejector = bad_ejector_tuple.ejector
        try:
            MetaCheckReport.objects.create(
                bk_biz_id=ejector.bk_biz_id,
                bk_cloud_id=ejector.machine.bk_cloud_id,
                ip=ejector.machine.ip,
                port=ejector.port,
                cluster=ejector.cluster.get().immute_domain,
                cluster_type=ejector.cluster_type,
                machine_type=ejector.machine.machine_type,
                status=False,
                msg=_("{} {} 不能作为同步 ejector".format(ejector.ip_port(), ejector.instance_inner_role)),
                subtype=MetaCheckSubType.ReplicateRole.value,
            )
        except ObjectDoesNotExist:  # 忽略实例没有集群关系的异常, instance-belong 会发现这个错误
            pass

    for bad_receiver_tuple in StorageInstanceTuple.objects.filter(
        receiver__instance_inner_role=InstanceInnerRole.MASTER.value
    ):
        receiver = bad_receiver_tuple.ejector
        try:
            MetaCheckReport.objects.create(
                bk_biz_id=receiver.bk_biz_id,
                bk_cloud_id=receiver.machine.bk_cloud_id,
                ip=receiver.machine.ip,
                port=receiver.port,
                cluster=receiver.cluster.get().immute_domain,
                cluster_type=receiver.cluster_type,
                machine_type=receiver.machine.machine_type,
                status=False,
                msg=_("{} {} 不能作为同步 receiver".format(receiver.ip_port(), receiver.instance_inner_role)),
                subtype=MetaCheckSubType.ReplicateRole.value,
            )
        except ObjectDoesNotExist:  # 忽略实例没有集群关系的异常, instance-belong 会发现这个错误
            pass
