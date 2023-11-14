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
from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import gettext_lazy as _


class InstancePhase(str, StructuredEnum):
    # instance实际可能存在的phase状态
    ONLINE = EnumField("online", _("正常"))
    OFFLINE = EnumField("offline", _("下架"))

    # 仅用作单据校验，不实际写入，销毁集群时，请直接删除Instance
    DESTROY = EnumField("destroy", _("销毁"))

    TRANS_STAGE = EnumField("trans_stage", _(" scr/gcs迁移中"))

    @classmethod
    def instance_status_transfer_valid(cls, source_phase, target_phase) -> bool:
        """
        判断集群的phase状态转移是否合法
        合法的状态转移:
        启用--->禁用，禁用--->销毁，禁用--->启用
        """

        if source_phase == cls.ONLINE.value and target_phase == cls.OFFLINE.value:
            return True
        elif source_phase == cls.OFFLINE.value and target_phase in [cls.ONLINE.value, cls.DESTROY.value]:
            return True
        else:
            return False
