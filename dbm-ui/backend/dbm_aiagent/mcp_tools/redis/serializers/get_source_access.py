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


class GetRedisSourceAccessInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名，格式为xx.xx.xx.db"))


class GetRedisSourceAccessOutputSerializer(serializers.Serializer):
    report = serializers.ListField(help_text=_("处理后的用户来源列表，需要渲染成表格"))
    failed_hosts = serializers.ListField(help_text=_("统计失败的主机列表。如果为空，不展示给用户。如果不为空，需要提示用户"))


class GetRedisSourceAccessByKeyInputSerializer(GetRedisSourceAccessInputSerializer):
    keyword_list = serializers.ListField(help_text=_("关键字列表，多个关键字之间是&的关系"))
    timeout = serializers.IntegerField(help_text=_("执行时长，不能超过300秒"), default=30)
    ins = serializers.CharField(help_text=_("指定实例, 格式为ip:port, 不传入代表抓所有接入层机器"), default="", allow_blank=True)


class GetRedisSourceAccessByKeyOutputSerializer(GetRedisSourceAccessInputSerializer):
    result_msg = serializers.CharField(help_text=_("抓包结果"))
