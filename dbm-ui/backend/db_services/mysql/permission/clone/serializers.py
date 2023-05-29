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

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.request_validator import validate_instance_in_biz
from backend.db_services.mysql.permission.clone import mock_data
from backend.db_services.mysql.permission.constants import CLONE_EXCEL_HEADER_MAP, CloneType
from backend.utils.excel import ExcelHandler


class CloneElementSerializer(serializers.Serializer):
    source = serializers.CharField(help_text=_("旧实例/旧客户端IP"))
    target = serializers.CharField(help_text=_("新实例/新客户端IP"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    module = serializers.CharField(help_text=_("模块名"), required=False)
    cluster_domain = serializers.CharField(help_text=_("集群域名"), required=False)

    class Meta:
        swagger_schema_fields = {"example": mock_data.CLONE_INSTANCE_DATA}


class PreCheckCloneSerializer(serializers.Serializer):
    clone_type = serializers.ChoiceField(help_text=_("权限克隆类型"), choices=CloneType.get_choices())
    clone_list = serializers.ListField(
        help_text=_("克隆元素列表"), child=CloneElementSerializer(help_text=_("克隆元素信息")), min_length=1
    )

    class Meta:
        swagger_schema_fields = {"example": mock_data.CLONE_INSTANCE_LIST_DATA}

    def validate(self, attrs):

        # 校验源和目标是否不一致
        ip_list = []
        clone_obj_list = []
        for clone_obj in attrs["clone_list"]:
            if clone_obj["source"] == clone_obj["target"]:
                raise serializers.ValidationError(
                    _("源克隆对象{}与目的克隆对象{}相同").format(clone_obj["source"], clone_obj["target"])
                )

            for instance_type in ["source", "target"]:
                obj = clone_obj[instance_type]
                ip_list.append(obj if attrs["clone_type"] == CloneType.CLIENT.value else obj.split(":")[0])
                clone_obj_list.append(obj)

        # TODO：校验ip是否都属于同一个云区域

        # 校验新实例是否都在本业务中
        if attrs["clone_type"] == CloneType.CLIENT.value:
            return attrs

        instances_not_in_biz = validate_instance_in_biz(self.context["bk_biz_id"], clone_obj_list)
        if instances_not_in_biz:
            raise serializers.ValidationError(
                _("实例{}不属于本业务{}，请保证所有实例均在本业务下").format(instances_not_in_biz, self.context["bk_biz_id"])
            )

        return attrs


class PreCheckCloneResponseSerializer(serializers.Serializer):
    pre_check = serializers.BooleanField(help_text=_("权限克隆前置检查结果"))
    message = serializers.CharField(help_text=_("权限克隆前置检查信息"))
    clone_uid = serializers.CharField(help_text=_("权限克隆数据uid"))
    clone_data_list = serializers.ListField(help_text=_("权限克隆数据列表"), child=serializers.DictField())

    class Meta:
        swagger_schema_fields = {"example": mock_data.CLONE_INSTANCE_LIST_RESPONSE_DATA}


class PreCheckExcelCloneSerializere(serializers.Serializer):
    clone_file = serializers.FileField(help_text=_("克隆实例/客户端excel文件"))
    clone_type = serializers.ChoiceField(help_text=_("权限克隆类型"), choices=CloneType.get_choices())

    def validate(self, attrs):
        clone_excel_file = attrs["clone_file"].file
        try:
            clone_data_list = ExcelHandler.paser(clone_excel_file)
        except Exception as e:  # pylint: disable=broad-except
            raise serializers.ValidationError(_("excel内容解析失败, 错误信息:{}。").format(e))

        # 校验表头是否正确
        if not set(CLONE_EXCEL_HEADER_MAP[attrs["clone_type"]]).issubset(set(clone_data_list[0].keys())):
            raise serializers.ValidationError(_("excel表头校验不正确!"))

        # 校验excel内容是否为空
        if not clone_data_list:
            raise serializers.ValidationError(_("excel内容为空!"))

        # 检验单元格是否存在None的情况
        for data in clone_data_list:
            if None in data.values():
                raise serializers.ValidationError(_("excel包含空的单元格！请检查数据的完整性和合法性"))

        clone_keys = ["source", "target"]
        for index, clone_data in enumerate(clone_data_list):
            clone_data_list[index] = dict(zip(clone_keys, clone_data.values()))

        attrs["clone_list"] = clone_data_list
        return attrs


class PreCheckExcelCloneResponseSerializer(serializers.Serializer):
    pre_check = serializers.BooleanField(help_text=_("权限克隆前置检查结果"))
    excel_url = serializers.CharField(help_text=_("权限克隆前置检查信息"))
    clone_uid = serializers.CharField(help_text=_("权限克隆数据uid"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.CLONE_EXCEL_INSTANCE_LIST_RESPONSE_DATA}


class GetExcelCloneInfoSerializer(serializers.Serializer):
    clone_type = serializers.ChoiceField(help_text=_("权限克隆类型"), choices=CloneType.get_choices())
    clone_uid = serializers.CharField(help_text=_("权限克隆数据缓存uid"), required=False)
    ticket_id = serializers.IntegerField(help_text=_("单据ID"), required=False)
