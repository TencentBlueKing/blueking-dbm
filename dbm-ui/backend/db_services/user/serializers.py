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


class ListUsersSerializer(serializers.Serializer):
    fuzzy_lookups = serializers.CharField(help_text=_("模糊搜索"), required=False, default="")
    # TODO 待前端vue3 组件改造后下线不分页功能
    no_page = serializers.CharField(help_text=_("不分页，即将下架，请不要使用，并尽快迁移"), required=False, default=False)
