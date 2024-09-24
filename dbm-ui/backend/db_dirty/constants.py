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

from django.utils.translation import ugettext_lazy as _

from blue_krill.data_types.enum import EnumField, StructuredEnum

SWAGGER_TAG = _("主机池")


class PoolType(str, StructuredEnum):
    # 池管理：污点池，故障池，待回收池
    Dirty = EnumField("dirty", _("污点池"))
    Fault = EnumField("fault", _("故障池"))
    Recycle = EnumField("recycle", _("待回收池"))
    # 资源池不由saas维护，单独由资源池服务维护
    Resource = EnumField("resource", _("资源池"))
    # 回收池表示已经挪到cc待回收，不在dbm流转
    Recycled = EnumField("recycled", _("已回收"))


class MachineEventType(str, StructuredEnum):
    ImportResource = EnumField("import_resource", _("导入资源池"))
    ApplyResource = EnumField("apply_resource", _("申请资源"))
    ReturnResource = EnumField("return_resource", _("退回资源"))
    ToDirty = EnumField("to_dirty", _("转入污点池"))
    ToRecycle = EnumField("to_recycle", _("转入待回收池"))
    ToFault = EnumField("to_fault", _("转入故障池"))
    UndoImport = EnumField("undo_import", _("撤销导入"))
    Recycled = EnumField("recycled", _("回收"))


MACHINE_EVENT__POOL_MAP = {
    MachineEventType.ToDirty: PoolType.Dirty,
    MachineEventType.ToRecycle: PoolType.Recycle,
    MachineEventType.ToFault: PoolType.Fault,
    MachineEventType.ImportResource: PoolType.Resource,
    MachineEventType.ReturnResource: PoolType.Resource,
    MachineEventType.Recycled: PoolType.Recycled,
    MachineEventType.UndoImport: PoolType.Recycled,
}
