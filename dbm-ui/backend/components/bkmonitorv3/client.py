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

from django.utils.translation import ugettext_lazy as _

from ..base import BaseApi
from ..domains import BKMONITORV3_APIGW_DOMAIN


class _BKMonitorV3Api(BaseApi):
    MODULE = _("监控")
    BASE = BKMONITORV3_APIGW_DOMAIN

    def __init__(self):
        self.metadata_get_data_id = self.generate_data_api(
            method="GET",
            url="metadata_get_data_id/",
            description=_("获取 data id"),
        )
        self.save_notice_group = self.generate_data_api(
            method="POST",
            url="save_notice_group/",
            description=_("保存通知组"),
        )
        self.query_custom_event_group = self.generate_data_api(
            method="GET",
            url="query_custom_event_group/",
            description=_("获取业务下自定义事件列表"),
        )
        self.custom_time_series = self.generate_data_api(
            method="GET",
            url="custom_time_series/",
            description=_("获取自定义指标列表"),
        )
        self.get_custom_event_group = self.generate_data_api(
            method="GET",
            url="get_custom_event_group/",
            description=_("获取自定义指标详情"),
        )
        self.custom_time_series_detail = self.generate_data_api(
            method="GET",
            url="custom_time_series_detail/",
            description=_("获取业自定义事件详情"),
        )
        self.create_custom_time_series = self.generate_data_api(
            method="POST",
            url="create_custom_time_series/",
            description=_("创建自定义指标"),
        )
        self.create_custom_event_group = self.generate_data_api(
            method="POST",
            url="create_custom_event_group/",
            description=_("创建自定义事件"),
        )
        self.save_alarm_strategy_v3 = self.generate_data_api(
            method="POST",
            url="save_alarm_strategy_v3/",
            description=_("保存告警策略"),
        )
        self.switch_alarm_strategy = self.generate_data_api(
            method="POST",
            url="switch_alarm_strategy/",
            description=_("启停告警策略"),
        )
        self.update_partial_strategy_v3 = self.generate_data_api(
            method="POST",
            url="update_partial_strategy_v3/",
            description=_("批量更新策略局部配置"),
        )
        self.delete_alarm_strategy_v3 = self.generate_data_api(
            method="POST",
            url="delete_alarm_strategy_v3/",
            description=_("删除告警策略"),
        )
        self.search_alarm_strategy_v3 = self.generate_data_api(
            method="POST",
            url="search_alarm_strategy_v3/",
            description=_("查询告警策略"),
        )
        self.save_collect_config = self.generate_data_api(
            method="POST",
            url="save_collect_config/",
            description=_("保存采集策略"),
        )
        self.query_collect_config = self.generate_data_api(
            method="POST",
            url="query_collect_config/",
            description=_("查询采集策略"),
        )
        self.get_collect_config_list = self.generate_data_api(
            method="POST",
            url="get_collect_config_list/",
            description=_("查询采集配置列表"),
        )
        self.query_collect_config_detail = self.generate_data_api(
            method="GET",
            url="query_collect_config_detail/",
            description=_("查询采集策略详情"),
        )
        self.search_user_groups = self.generate_data_api(
            method="POST",
            url="search_user_groups/",
            description=_("查询用户组列表"),
        )
        self.search_user_group_detail = self.generate_data_api(
            method="POST",
            url="search_user_group_detail/",
            description=_("查询用户组详情"),
        )
        self.delete_user_groups = self.generate_data_api(
            method="POST",
            url="delete_user_groups/",
            description=_("删除用户组"),
        )
        self.save_user_group = self.generate_data_api(
            method="POST",
            url="save_user_group/",
            description=_("保存用户组"),
        )
        self.save_duty_rule = self.generate_data_api(
            method="POST",
            url="save_duty_rule/",
            description=_("保存轮值规则"),
        )
        self.delete_duty_rules = self.generate_data_api(
            method="POST",
            url="delete_duty_rules/",
            description=_("删除轮值规则"),
        )
        self.save_rule_group = self.generate_data_api(
            method="POST",
            url="assign/save_rule_group/",
            description=_("保存分派组"),
        )
        self.search_rule_groups = self.generate_data_api(
            method="POST",
            url="assign/search_rule_groups/",
            description=_("查询分派组"),
        )
        self.delete_rule_group = self.generate_data_api(
            method="POST",
            url="assign/delete_rule_group/",
            description=_("删除分派组"),
        )
        self.search_event = self.generate_data_api(
            method="POST",
            url="search_event/",
            description=_("查询事件"),
        )
        self.unify_query = self.generate_data_api(
            method="POST",
            url="time_series_unify_query/",
            description=_("统一查询时序数据"),
        )


BKMonitorV3Api = _BKMonitorV3Api()
