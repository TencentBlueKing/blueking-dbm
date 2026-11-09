"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.db_meta.enums import ClusterType
from backend.db_report.report_basemodel import BaseReportABS


class EsDatanodeAttrReport(BaseReportABS):
    domain = models.CharField(max_length=255, default="")
    app = models.CharField(max_length=100, verbose_name=_("业务名"))
    dba = models.JSONField(verbose_name=_("业务所属dba"))
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="", help_text=_("集群类型"))
    ip = models.CharField(max_length=64, default="", verbose_name=_("节点IP"))
    node_name = models.CharField(max_length=255, default="", verbose_name=_("节点名称"))
    node_role = models.CharField(max_length=32, default="", verbose_name=_("节点角色"))
    es_idc_id = models.CharField(max_length=64, default="", verbose_name=_("ES配置机房ID"))
    meta_idc_id = models.IntegerField(default=0, verbose_name=_("元数据机房ID"))
    es_rack_id = models.CharField(max_length=64, default="", verbose_name=_("ES配置机架ID"))
    meta_rack_id = models.IntegerField(default=0, verbose_name=_("元数据机架ID"))
    es_sub_zone_id = models.CharField(max_length=64, default="", verbose_name=_("ES配置园区ID"))
    meta_sub_zone_id = models.IntegerField(default=0, verbose_name=_("元数据园区ID"))
