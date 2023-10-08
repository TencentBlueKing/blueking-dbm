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
import logging
from urllib.parse import urljoin

from django.utils.translation import ugettext_lazy as _

from ..base import DataAPI
from ..domains import BKMONITORV3_APIGW_DOMAIN

logger = logging.getLogger("root")


class _BKMonitorV3Api(object):
    MODULE = _("监控")

    def __init__(self):
        self.metadata_get_data_id = DataAPI(
            method="GET",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="metadata_get_data_id/",
            module=self.MODULE,
            description=_("获取 data id"),
        )
        self.save_notice_group = DataAPI(
            method="POST",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="save_notice_group/",
            module=self.MODULE,
            description=_("保存通知组"),
        )
        self.query_custom_event_group = DataAPI(
            method="GET",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="query_custom_event_group/",
            module=self.MODULE,
            description=_("获取业务下自定义事件列表"),
        )
        self.custom_time_series = DataAPI(
            method="GET",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="custom_time_series/",
            module=self.MODULE,
            description=_("获取自定义指标列表"),
        )
        self.get_custom_event_group = DataAPI(
            method="GET",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="get_custom_event_group/",
            module=self.MODULE,
            description=_("获取自定义指标详情"),
        )
        self.custom_time_series_detail = DataAPI(
            method="GET",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="custom_time_series_detail/",
            module=self.MODULE,
            description=_("获取业自定义事件详情"),
        )
        self.create_custom_time_series = DataAPI(
            method="POST",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="create_custom_time_series/",
            module=self.MODULE,
            description=_("创建自定义指标"),
        )
        self.create_custom_event_group = DataAPI(
            method="POST",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="create_custom_event_group/",
            module=self.MODULE,
            description=_("创建自定义事件"),
        )
        self.save_alarm_strategy_v3 = DataAPI(
            method="POST",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="save_alarm_strategy_v3/",
            module=self.MODULE,
            description=_("保存告警策略"),
        )
        self.switch_alarm_strategy = DataAPI(
            method="POST",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="switch_alarm_strategy/",
            module=self.MODULE,
            description=_("启停告警策略"),
        )
        self.update_partial_strategy_v3 = DataAPI(
            method="POST",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="update_partial_strategy_v3/",
            module=self.MODULE,
            description=_("批量更新策略局部配置"),
        )
        self.delete_alarm_strategy_v3 = DataAPI(
            method="POST",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="delete_alarm_strategy_v3/",
            module=self.MODULE,
            description=_("删除告警策略"),
        )
        self.search_alarm_strategy_v3 = DataAPI(
            method="POST",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="search_alarm_strategy_v3/",
            module=self.MODULE,
            description=_("查询告警策略"),
        )
        self.save_collect_config = DataAPI(
            method="POST",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="save_collect_config/",
            module=self.MODULE,
            description=_("保存采集策略"),
        )
        self.query_collect_config = DataAPI(
            method="POST",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="query_collect_config/",
            module=self.MODULE,
            description=_("查询采集策略"),
        )
        self.get_collect_config_list = DataAPI(
            method="POST",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="get_collect_config_list/",
            module=self.MODULE,
            description=_("查询采集配置列表"),
        )
        self.query_collect_config_detail = DataAPI(
            method="GET",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="query_collect_config_detail/",
            module=self.MODULE,
            description=_("查询采集策略详情"),
        )
        self.search_user_groups = DataAPI(
            method="POST",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="search_user_groups/",
            module=self.MODULE,
            description=_("查询用户组列表"),
        )
        self.search_user_group_detail = DataAPI(
            method="POST",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="search_user_group_detail/",
            module=self.MODULE,
            description=_("查询用户组详情"),
        )
        self.delete_user_groups = DataAPI(
            method="POST",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="delete_user_groups/",
            module=self.MODULE,
            description=_("删除用户组"),
        )
        self.save_user_group = DataAPI(
            method="POST",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="save_user_group/",
            module=self.MODULE,
            description=_("保存用户组"),
        )
        self.save_rule_group = DataAPI(
            method="POST",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="assign/save_rule_group/",
            module=self.MODULE,
            description=_("保存分派组"),
        )

        self.search_rule_groups = DataAPI(
            method="POST",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="assign/search_rule_groups/",
            module=self.MODULE,
            description=_("查询分派组"),
        )

        self.delete_rule_group = DataAPI(
            method="POST",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="assign/delete_rule_group/",
            module=self.MODULE,
            description=_("删除分派组"),
        )

        self.search_event = DataAPI(
            method="POST",
            base=BKMONITORV3_APIGW_DOMAIN,
            url="search_event/",
            module=self.MODULE,
            description=_("查询事件"),
        )


BKMonitorV3Api = _BKMonitorV3Api()
