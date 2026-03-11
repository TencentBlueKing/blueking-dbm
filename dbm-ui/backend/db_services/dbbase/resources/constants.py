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

from blue_krill.data_types.enum import EnumField, StrStructuredEnum

RESOURCE_TAG = "db_services/resources"


class ResourceNodeType(StrStructuredEnum):
    BIZ = EnumField("biz", _("业务"))
    CLUSTER = EnumField("cluster", _("集群"))
    MODULE = EnumField("module", _("模块"))


DEFAULT_CLUSTER_DATA = {
    "id": 0,
    "db_type": "",
    "phase": "",
    "phase_name": "",
    "status": "",
    "operations": [],
    "dns_to_clb": False,
    "cluster_time_zone": "",
    "cluster_name": "",
    "cluster_alias": "",
    "cluster_access_port": 0,
    "cluster_stats": {},
    "cluster_type": "",
    "cluster_type_name": "",
    "cluster_subzones": [],
    "cluster_subzone_ids": [],
    "disaster_tolerance_level": "",
    "master_domain": "",
    "slave_domain": "",
    "cluster_entry": [],
    "bk_biz_id": 0,
    "bk_biz_name": "",
    "bk_cloud_id": 0,
    "bk_cloud_name": "",
    "major_version": "",
    "region": "",
    "city": "",
    "db_module_name": "",
    "db_module_id": 0,
    "creator": "",
    "updater": "",
    "create_at": "",
    "update_at": "",
    "cluster_spec": {},
    "tags": [],
    "zone_list": [],
}
