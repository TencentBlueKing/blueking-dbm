"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import re
from collections.abc import Hashable

from django.db import transaction
from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.constants import IP_RE_PATTERN
from backend.exceptions import ValidationError
from backend.ticket.models import Flow, FlowSummary


class BaseFlowOutputSerializer(serializers.Serializer):
    """流程输出序列化器，也是对一份流程输出表的基础定义"""

    table_name: str = ""  # 表名(表唯一标识)
    table_display_name: str = ""  # 表显示名(前端摘要显示名)，为空则取table_name
    table_primary_key: str = ""  # 表主键(保证表数据唯一性)，为空则表示无需主键。这里的主键必须是可hash的(建议用int, str类)
    hidden: bool = False  # 是否隐藏(隐藏则不在前端显示)
    dynamic_key: str = ""  # 动态字段的key(动态表格需要定义动态字段的key)

    # 基础字段的定义，可根据需要拓展
    class IpField(serializers.IPAddressField):
        """ip字段的定义"""

        pass

    class InstanceField(serializers.CharField):
        """实例字段的定义"""

        ip_pattern = re.compile(IP_RE_PATTERN)

        def run_validators(self, value):
            # 实例字段的格式必须为 IP:Port
            if ":" not in value:
                raise serializers.ValidationError("Invalid instance format")
            ip, port = value.split(":")
            if not (self.ip_pattern.match(ip) and port.isdigit()):
                raise serializers.ValidationError("Invalid instance format")
            super().run_validators(value)

    class DynamicField(serializers.ListField):
        """动态字段的定义"""

        child = serializers.JSONField()


class FlowOutputHandler:
    """流程输出处理器"""

    slz: BaseFlowOutputSerializer = None

    def __init__(self, slz):
        self.slz = slz

    @transaction.atomic
    def insert_data(self, root_id, data, ignore_conflict=True):
        """
        插入数据
        @param root_id: 流程节点ID
        @param data: 待插入的数据(可以为一个列表表示插入多条数据)
        @param ignore_conflict: 是否忽略冲突(在定义表主键之后，摘要数据需要唯一，如果忽略冲突则是覆盖更新)
        """
        # 序列化
        data = [data] if isinstance(data, dict) else data
        serializer = self.slz(data=data, many=True)
        serializer.is_valid(raise_exception=True)

        flow_id = Flow.objects.get(flow_obj_id=root_id).id
        flow_summary, __ = FlowSummary.objects.select_for_update().get_or_create(flow_id=flow_id)
        output_data = flow_summary.summary or []
        validated_data = serializer.validated_data

        # 动态表格特殊处理表头
        if self.slz.dynamic_key and validated_data and self.slz.dynamic_key in data[0]:
            validated_data = validated_data[0][self.slz.dynamic_key]
            item_list = validated_data[0].items()
        elif not self.slz.dynamic_key:
            item_list = serializer.child.fields.items()
        else:
            raise ValidationError(f"flow output insert failed, slz is {self.slz}, data is {data}")

        # 考虑顺序，获取table_name与对应的index
        table_name__index = {d["table_name"]: i for i, d in enumerate(output_data)}
        if self.slz.table_name not in table_name__index:
            titles = [
                {"id": name, "display_name": (name if self.slz.dynamic_key else field.help_text)}
                for name, field in item_list
            ]
            table_data = {
                "table_name": self.slz.table_name,
                "table_display_name": self.slz.table_display_name or self.slz.table_name,
                "table_primary_key": self.slz.table_primary_key,
                "titles": titles,
                "values": [],
                "hidden": self.slz.hidden,
            }
            output_data.append(table_data)
            table_data = output_data[-1]
        else:
            table_data = output_data[table_name__index[self.slz.table_name]]

        # 如果没有主键则直接插入，有主键则判断冲突/合并覆盖
        primary_key = table_data.get("table_primary_key")
        if not primary_key or not isinstance(primary_key, Hashable):
            table_data["values"].extend(validated_data)
        else:
            primary_map = {d[primary_key]: d for d in table_data["values"]}
            data_map = {d[primary_key]: d for d in validated_data}
            if not ignore_conflict and set(primary_map.keys()) & set(data_map.keys()):
                raise ValidationError(_("存在冲突主键的数据"))
            # 合并数据
            table_data["values"] = list({**primary_map, **data_map}.values())

        flow_summary.summary = output_data
        flow_summary.save(update_fields=["summary"])
