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

from django.db import transaction
from rest_framework import serializers

from backend.constants import IP_RE_PATTERN
from backend.ticket.models import Flow


class BaseFlowOutputSerializer(serializers.Serializer):
    """流程输出序列化器，也是对一份流程输出表的基础定义"""

    table_name: str = ""
    hidden: bool = False

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


class FlowOutputHandler:
    """流程输出处理器"""

    slz: BaseFlowOutputSerializer = None

    def __init__(self, slz):
        self.slz = slz

    @transaction.atomic
    def insert_data(self, root_id, data):
        """
        插入数据
        @param root_id: 流程节点ID
        @param data: 待插入的数据(可以为一个列表表示插入多条数据)
        """
        # 序列化
        data = [data] if isinstance(data, dict) else data
        serializer = self.slz(data=data, many=True)
        serializer.is_valid(raise_exception=True)

        flow = Flow.objects.select_for_update().get(flow_obj_id=root_id)
        output_data = flow.context.get("__flow_output_v2", [])

        # 考虑顺序，获取table_name与对应的index
        table_name__index = {d["table_name"]: i for i, d in enumerate(output_data)}
        if self.slz.table_name not in table_name__index:
            titles = [{"id": name, "display_name": field.help_text} for name, field in serializer.child.fields.items()]
            table_data = {"table_name": self.slz.table_name, "titles": titles, "values": [], "hidden": self.slz.hidden}
            output_data.append(table_data)
            table_data = output_data[-1]
        else:
            table_data = output_data[table_name__index[self.slz.table_name]]

        table_data["values"].extend(serializer.validated_data)
        flow.context["__flow_output_v2"] = output_data
        flow.save(update_fields=["context"])
