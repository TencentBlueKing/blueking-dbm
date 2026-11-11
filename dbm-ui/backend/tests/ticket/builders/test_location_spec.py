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
from backend.configuration.constants import AffinityEnum
from backend.db_services.dbbase.constants import IpSource
from backend.ticket.builders.common.base import get_location_zones, get_ticket_zone_list


def _ticket_data(location_spec, affinity=AffinityEnum.CROS_SUBZONE):
    return {
        "ip_source": IpSource.RESOURCE_POOL,
        "disaster_tolerance_level": affinity,
        "resource_spec": {"backend_group": {"location_spec": location_spec}},
    }


def test_location_zones_prefers_new_protocol_field():
    """部署单据前端传的是 bk_cloud_zone_list"""
    assert get_location_zones({"bk_cloud_zone_list": ["ap-guangzhou-3"]}) == ["ap-guangzhou-3"]


def test_location_zones_falls_back_to_sub_zone_ids():
    """存量单据 / 集群后续单据还是 sub_zone_ids"""
    assert get_location_zones({"sub_zone_ids": ["ap-guangzhou-4"]}) == ["ap-guangzhou-4"]


def test_location_zones_handles_missing():
    assert get_location_zones({}) == []
    assert get_location_zones(None) == []


def test_ticket_zone_list_reads_new_protocol_field():
    """部署时按可用区部署，集群元数据要记住这几个可用区，不能因为 key 变了丢成空列表"""
    data = _ticket_data(
        {"bk_cloud_region": "ap-guangzhou", "bk_cloud_zone_list": ["ap-guangzhou-3", "ap-guangzhou-4"]}
    )
    assert get_ticket_zone_list(data) == ["ap-guangzhou-3", "ap-guangzhou-4"]


def test_ticket_zone_list_reads_legacy_field():
    data = _ticket_data({"city": "广州", "sub_zone_ids": ["ap-guangzhou-3"]})
    assert get_ticket_zone_list(data) == ["ap-guangzhou-3"]


def test_ticket_zone_list_ignores_location_for_cross_rack():
    """跨机架/无 这类级别不限定可用区，取空"""
    data = _ticket_data({"bk_cloud_zone_list": ["ap-guangzhou-3"]}, affinity=AffinityEnum.CROSS_RACK)
    assert get_ticket_zone_list(data) == []
