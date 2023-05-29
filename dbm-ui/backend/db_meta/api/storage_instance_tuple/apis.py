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

from django.db import transaction

from backend.db_meta import request_validator
from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.models import StorageInstance, StorageInstanceTuple

logger = logging.getLogger("root")


@transaction.atomic
def create(tpls: List, creator: str = ""):
    """
    1. ejector 必须是 master 或 repeater
    2. receiver 必须是 slave 或 repeater
    3. 允许多 master, 允许环路
    4. 不禁止 meta type 不同的情况, 因为天知道以后会不会有集群类型切换
    """

    tpls = request_validator.validated_storage_tuple_list(tpls, allow_empty=False, allow_null=False)

    for tpl in tpls:
        ejector_ip = tpl["ejector"]["ip"]
        ejector_port = tpl["ejector"]["port"]
        receiver_ip = tpl["receiver"]["ip"]
        receiver_port = tpl["receiver"]["port"]

        ejector_obj = StorageInstance.objects.get(machine__ip=ejector_ip, port=ejector_port)
        receiver_obj = StorageInstance.objects.get(machine__ip=receiver_ip, port=receiver_port)
        # ToDo 当 master 作为 receiver 时, 转换成 repeater 这个动作到底该在哪里做
        if ejector_obj.instance_inner_role not in [
            InstanceInnerRole.MASTER,
            InstanceInnerRole.REPEATER,
        ]:
            raise Exception("""{} can't be ejector""".format(ejector_obj.instance_inner_role))

        if receiver_obj.instance_inner_role not in [
            InstanceInnerRole.SLAVE,
            InstanceInnerRole.REPEATER,
        ]:
            raise Exception("""{} can't be receiver""".format(receiver_obj.instance_inner_role))

        if ejector_obj == receiver_obj:
            raise Exception("""ejector and receiver can't be same instance""")
        StorageInstanceTuple.objects.create(ejector=ejector_obj, receiver=receiver_obj, creator=creator)
