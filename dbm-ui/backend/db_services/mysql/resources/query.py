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
from backend.db_meta.models import StorageInstance
from backend.db_services.dbbase.resources import query
from backend.db_services.dbbase.resources.register import register_resource_decorator


@register_resource_decorator()
class MysqlListRetrieveResource(query.ListRetrieveResource):
    """查看 mysql 架构的资源"""

    @staticmethod
    def slave_associate_mater_role(instances):
        """
        查询slave/repeater角色关联的主库
        """
        pair_instance_map = {}
        instance_ids = [instance["id"] for instance in instances]
        insts = (
            StorageInstance.objects.filter(id__in=instance_ids)
            .select_related("machine")
            .prefetch_related("as_receiver", "as_receiver__ejector__machine")
        )
        for inst in insts:
            pair_instance_map[inst.machine.ip] = inst.as_receiver.get().ejector.simple_desc

        return pair_instance_map
