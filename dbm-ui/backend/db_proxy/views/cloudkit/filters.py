# -*- coding:utf-8 -*-
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
from django_filters import rest_framework as filters

from backend.db_proxy.models import DBCloudKit


class DBCloudKitListFilter(filters.FilterSet):
    bk_cloud_id = filters.NumberFilter(field_name="bk_cloud_id", lookup_expr="exact", label=_("云区域ID"))
    bk_biz_id = filters.NumberFilter(field_name="bk_biz_id", lookup_expr="exact", label=_("业务ID"))
    name = filters.CharFilter(field_name="name", lookup_expr="icontains", label=_("套件ID名称"))
    alias = filters.CharFilter(field_name="alias", lookup_expr="icontains", label=_("套件别名"))

    class Meta:
        model = DBCloudKit
        fields = ["bk_cloud_id", "bk_biz_id", "name", "alias"]
