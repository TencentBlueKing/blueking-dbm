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

from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_services.mysql.permission.authorize import mock_data
from backend.db_services.mysql.permission.constants import AUTHORIZE_EXCEL_HEADER
from backend.utils.excel import ExcelHandler


class PreCheckAuthorizeRulesSerializer(serializers.Serializer):
    class SourceIpSerializer(serializers.Serializer):
        ip = serializers.CharField(help_text=_("ip地址"))
        bk_host_id = serializers.IntegerField(help_text=_("资源池主机ID"), required=False)

    user = serializers.CharField(help_text=_("账号名称"))
    source_ips = serializers.ListField(help_text=_("源ip列表"), child=SourceIpSerializer())
    target_instances = serializers.ListField(help_text=_("目标集群"), child=serializers.CharField(help_text=_("集群名")))
    access_dbs = serializers.ListField(help_text=_("访问DB列表"), child=serializers.CharField(help_text=_("访问DB")))
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
    cluster_ids = serializers.ListField(
        help_text=_("集群id列表"), child=serializers.IntegerField(), allow_empty=True, required=False
    )

    class Meta:
        swagger_schema_fields = {"example": mock_data.PRE_CHECK_AUTHORIZE_RULES_DATA}


class PreChecExcelAuthorizeRulesResponseSerializer(serializers.Serializer):
    pre_check = serializers.BooleanField(help_text=_("前置检查结果"))
    message = serializers.CharField(help_text=_("检查结果信息"))
    authorize_uid = serializers.CharField(help_text=_("授权数据缓存uid"))
    authorize_data = serializers.DictField(help_text=_("授权数据信息"), child=PreCheckAuthorizeRulesSerializer())

    class Meta:
        swagger_schema_fields = {"example": mock_data.PRE_CHECK_AUTHORIZE_RULES_RESPONSE_DATA}


class PreCheckExcelAuthorizeRulesSerializer(serializers.Serializer):
    authorize_file = serializers.FileField(help_text=_("授权excel文件"))
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())

    class Meta:
        swagger_schema_fields = {"example": mock_data.PRE_CHECK_EXCEL_AUTHORIZE_RULES_DATA}

    def validate(self, attrs):
        excel = attrs["authorize_file"].file
        try:
            authorize_excel_data__list = ExcelHandler.paser(excel, header_row=1)
        except Exception as e:  # pylint: disable=broad-except
            raise serializers.ValidationError(_("excel内容解析失败, 错误信息:{}。提示: 请按照模板填写授权数据").format(e))

        # 校验excel内容是否为空
        if not authorize_excel_data__list:
            raise serializers.ValidationError(_("excel表格为空!"))

        # 校验表头是否正确
        if not set(AUTHORIZE_EXCEL_HEADER).issubset(set(authorize_excel_data__list[0].keys())):
            raise serializers.ValidationError(_("excel表头校验不正确! 提示: 请按照模板填写授权数据"))

        # 检验单元格是否存在None的情况
        for data in authorize_excel_data__list:
            if None in data.values():
                raise serializers.ValidationError(_("excel包含空的单元格！请检查数据的完整性和合法性"))

        attrs["authorize_excel_data"] = authorize_excel_data__list
        return attrs


class PreCheckExcelAuthorizeRulesResponseSerializer(serializers.Serializer):
    pre_check = serializers.BooleanField(help_text=_("前置检查结果"))
    authorize_uid = serializers.CharField(help_text=_("授权数据缓存uid"))
    excel_url = serializers.URLField(help_text=_("授权信息excel文件下载url"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.PRE_CHECK_EXCEL_AUTHORIZE_RULES_RESPONSE_DATA}


class GetExcelAuthorizeRulesInfoSerializer(serializers.Serializer):
    authorize_uid = serializers.CharField(help_text=_("授权数据缓存uid"), required=False)
    ticket_id = serializers.IntegerField(help_text=_("单据ID"), required=False)


class ExcelAuthorizeRulesErrorSerializer(serializers.Serializer):
    authorize_file = serializers.FileField(help_text=_("授权执行错误excel"))


class OnlineMySQLRulesSerializer(serializers.Serializer):
    user = serializers.CharField(help_text=_("账号名称"))
    source_ip = serializers.CharField(help_text=_("访问源ip"))
    target_cluster = serializers.CharField(help_text=_("访问集群名称"))
    access_db = serializers.CharField(help_text=_("访问db名称"))
    authorize_rule = serializers.CharField(help_text=_("规则列表"))


class GetOnlineMySQLRulesSerializer(serializers.Serializer):
    online_rules = serializers.ListSerializer(
        help_text=_("现网授权列表"), allow_empty=True, child=OnlineMySQLRulesSerializer(help_text=_("授权信息"))
    )

    class Meta:
        swagger_schema_fields = {"example": mock_data.ONLINE_MYSQL_RULES_DATA}


class GetHostInAuthorizeSerializer(serializers.Serializer):
    ticket_id = serializers.IntegerField(help_text=_("单据id"))
    keyword = serializers.CharField(help_text=_("过滤搜索关键字"), required=False)

    class Meta:
        swagger_schema_fields = {"example": {"ticket_id": 1}}
