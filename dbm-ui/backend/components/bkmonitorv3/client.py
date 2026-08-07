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

import time
from dataclasses import asdict
from typing import List

from django.utils.translation import gettext_lazy as _

from ...db_monitor.dataclass import MonitorEvent
from ..base import BaseApi
from ..domains import BKMONITORV3_APIGW_DOMAIN
from ..exception import DataAPIException


class _BKMonitorV3Api(BaseApi):
    MODULE = _("监控")
    BASE = BKMONITORV3_APIGW_DOMAIN

    class ErrorCode:
        MONITOR_GROUP_NAME_ALREADY_EXISTS = 3312003
        DUTY_RULE_NAME_ALREADY_EXISTS = 3312006
        STRATEGY_ALREADY_EXISTS = 3313008

    def __init__(self):
        self.query_custom_event_group = self.generate_data_api(
            method="GET",
            url="app/custom_event/query/",
            description=_("获取业务下自定义事件列表"),
        )
        self.custom_time_series = self.generate_data_api(
            method="GET",
            url="app/custom_metric/list/",
            description=_("获取自定义指标列表"),
        )
        self.get_custom_event_group = self.generate_data_api(
            method="GET",
            url="app/custom_event/get/",
            description=_("获取自定义指标详情"),
        )
        self.custom_time_series_detail = self.generate_data_api(
            method="GET",
            url="app/custom_metric/detail/",
            description=_("获取业自定义事件详情"),
        )
        self.create_custom_time_series = self.generate_data_api(
            method="POST",
            url="app/custom_metric/create/",
            description=_("创建自定义指标"),
        )
        self.create_custom_event_group = self.generate_data_api(
            method="POST",
            url="app/custom_event/create/",
            description=_("创建自定义事件"),
        )
        self.save_alarm_strategy_v3 = self.generate_data_api(
            method="POST",
            url="app/alarm_strategy/save/v3/",
            description=_("保存告警策略"),
        )
        self.switch_alarm_strategy = self.generate_data_api(
            method="POST",
            url="app/alarm_strategy/switch/",
            description=_("启停告警策略"),
        )
        self.update_partial_strategy_v3 = self.generate_data_api(
            method="POST",
            url="app/alarm_strategy/update_bulk/v3/",
            description=_("批量更新策略局部配置"),
        )
        self.delete_alarm_strategy_v3 = self.generate_data_api(
            method="POST",
            url="app/alarm_strategy/delete/v3/",
            description=_("删除告警策略"),
        )
        self.search_alarm_strategy_v3 = self.generate_data_api(
            method="POST",
            url="app/alarm_strategy/search/v3/",
            description=_("查询告警策略"),
        )
        self.save_collect_config = self.generate_data_api(
            method="POST",
            url="app/collect_config/save/",
            description=_("保存采集策略"),
        )
        self.run_collect_config = self.generate_data_api(
            method="POST",
            url="app/collect_config/run/",
            description=_("执行采集配置部分实例"),
        )
        self.query_collect_config = self.generate_data_api(
            method="POST",
            url="app/collect_config/query/",
            description=_("查询采集策略"),
        )
        self.get_collect_config_list = self.generate_data_api(
            method="POST",
            url="app/collect_config/list/",
            description=_("查询采集配置列表"),
        )
        self.query_collect_config_detail = self.generate_data_api(
            method="GET",
            url="app/collect_config/detail/",
            description=_("查询采集策略详情"),
        )
        self.search_user_groups = self.generate_data_api(
            method="POST",
            url="app/user_group/search/",
            description=_("查询用户组列表"),
        )
        self.search_user_group_detail = self.generate_data_api(
            method="POST",
            url="app/user_group/detail/",
            description=_("查询用户组详情"),
        )
        self.delete_user_groups = self.generate_data_api(
            method="POST",
            url="app/legacy/delete_user_groups/",
            description=_("删除用户组"),
        )
        self.save_user_group = self.generate_data_api(
            method="POST",
            url="app/user_group/save/",
            description=_("保存用户组"),
            default_timeout=120,
        )
        self.save_duty_rule = self.generate_data_api(
            method="POST",
            url="app/duty_rule/save/",
            description=_("保存轮值规则"),
        )
        self.search_duty_rules = self.generate_data_api(
            method="POST",
            url="app/duty_rule/search/",
            description=_("查询轮值规则列表"),
        )
        self.delete_duty_rules = self.generate_data_api(
            method="POST",
            url="app/duty_rule/delete/",
            description=_("删除轮值规则"),
        )
        self.save_rule_group = self.generate_data_api(
            method="POST",
            url="app/assign/rule_group/save/",
            description=_("保存分派组"),
        )
        self.search_rule_groups = self.generate_data_api(
            method="POST",
            url="app/assign/rule_group/search/",
            description=_("查询分派组"),
        )
        self.delete_rule_group = self.generate_data_api(
            method="POST",
            url="app/assign/rule_group/delete/",
            description=_("删除分派组"),
        )
        self.search_event = self.generate_data_api(
            method="POST",
            url="app/event/search/",
            description=_("查询事件（老）"),
        )
        self.search_alert = self.generate_data_api(
            method="POST",
            url="app/alert/search/",
            description=_("查询事件（新）"),
        )
        self.unify_query = self.generate_data_api(
            method="POST",
            url="app/data_query/time_series_unify_query/",
            description=_("统一查询时序数据"),
        )
        self.proxy_host_info = self.generate_data_api(
            method="GET",
            url="app/custom_event/proxy_host_info/",
            description=_("获取自定义上报的 proxy 主机信息"),
        )
        self.search_action_config = self.generate_data_api(
            method="GET",
            url="app/action_config/search/",
            description=_("查询处理套餐"),
        )
        self.save_action_config = self.generate_data_api(
            method="POST",
            url="app/action_config/save/",
            description=_("保存处理套餐"),
        )
        self.edit_action_config = self.generate_data_api(
            method="POST",
            url="app/action_config/edit/",
            description=_("编辑处理套餐"),
        )
        self.add_shield = self.generate_data_api(
            method="POST",
            url="app/shield/add/",
            description=_("新增告警屏蔽"),
        )
        self.disable_shield = self.generate_data_api(
            method="POST",
            url="app/shield/disable/",
            description=_("解除告警屏蔽"),
        )
        self.edit_shield = self.generate_data_api(
            method="POST",
            url="app/shield/edit/",
            description=_("编辑告警屏蔽"),
        )
        self.list_shield = self.generate_data_api(
            method="POST",
            url="app/shield/search/",
            description=_("获取告警屏蔽列表"),
        )
        self.get_shield = self.generate_data_api(
            method="GET",
            url="app/shield/detail/",
            description=_("获取告警屏蔽详情"),
        )
        self.bulk_save_subscribe = self.generate_data_api(
            method="POST",
            url="app/subscribe/bulk_save/",
            description=_("新增/保存策略订阅"),
        )
        self.bulk_delete_subscribe = self.generate_data_api(
            method="POST",
            url="app/subscribe/bulk_delete/",
            description=_("删除策略订阅"),
        )
        self.list_subscribe = self.generate_data_api(
            method="GET",
            url="app/subscribe/list/",
            description=_("查询策略订阅列表"),
        )
        self.start_render_image_task = self.generate_data_api(
            method="POST",
            url="app/render_image/start_render_image_task/",
            description=_("启动渲染图片任务"),
        )
        self.get_render_image_result = self.generate_data_api(
            method="GET",
            url="app/render_image/get_render_image_task_result/",
            description=_("获取渲染图片任务结果"),
        )
        self.metric_list = self.generate_data_api(
            method="POST", url="app/metric/get_metric_list/", description=_("获取维度信息")
        )
        self.search_alarm_strategy = self.generate_data_api(
            method="POST",
            url="app/alarm_strategy/search/",
            description=_("查询告警策略"),
        )
        self.save_alarm_strategy = self.generate_data_api(
            method="POST",
            url="app/alarm_strategy/save/",
            description=_("保存告警策略"),
        )
        self.delete_alarm_strategy = self.generate_data_api(
            method="POST",
            url="app/alarm_strategy/delete/",
            description=_("删除告警策略"),
        )
        self.as_code_import_config = self.generate_data_api(
            method="POST", url="app/as_code/import_config/", description=_("导入AsCode配置")
        )
        self.collector_plugin_list = self.generate_data_api(
            method="GET", url="app/collect_plugin/list/", description=_("获取采集插件列表")
        )

        self.plugin_import_without_frontend = self.generate_data_api(
            method="POST", url="app/collect_plugin/plugin_import_without_frontend/", description=_("导入采集插件")
        )

    def bulk_save_subscribe_in_batch(self, bk_biz_id, subscriptions):
        """按批次，批量新增/保存策略订阅"""
        # 500批次一次更新，防止接口超时/OOM
        batch_size = 500
        for i in range(0, len(subscriptions), batch_size):
            params = {"bk_biz_id": bk_biz_id, "subscriptions": subscriptions[i : i + batch_size]}
            self.bulk_save_subscribe(params)

    def list_full_subscribe(self, bk_biz_id, username=""):
        """查询全量策略订阅列表"""
        batch_size = 500
        page, full_results = 1, []
        while True:
            params = {"bk_biz_id": bk_biz_id, "page": page, "page_size": batch_size}
            if username:
                params["sub_username"] = username
            results = self.list_subscribe(params=params)
            if not results:
                return full_results
            full_results.extend(results)
            page += 1


class _BKMonitorV3EventApi(BaseApi):
    MODULE = _("监控自定义事件")
    BASE = ""
    DATA_ID = None
    ACCESS_TOKEN = None

    def __init__(self):
        pass

    def __init_api(self):
        self.send_monitor_event = self.generate_data_api(
            method="POST",
            url="",
            description=_("发送自定义事件"),
        )

    def __init_conf(self):
        if self.BASE and self.DATA_ID and self.ACCESS_TOKEN:
            return

        from backend.configuration.constants import SystemSettingsEnum
        from backend.configuration.models import SystemSettings

        # 初始化配置项
        try:
            dbm_report = SystemSettings.get_setting_value(key=SystemSettingsEnum.BKM_DBM_REPORT)
            self.BASE = dbm_report["proxy"]
            self.DATA_ID, self.ACCESS_TOKEN = dbm_report["event"]["data_id"], dbm_report["event"]["token"]
        except KeyError:
            pass

        if not self.BASE or not self.DATA_ID or not self.ACCESS_TOKEN:
            raise DataAPIException(
                _("事件上报配置错误: proxy={}, data_id={}, token={}").format(self.BASE, self.DATA_ID, self.ACCESS_TOKEN)
            )

        # 初始化API 接口
        self.__init_api()

    def send_event(self, events: List[MonitorEvent]):
        """
        发送自定义告警事件，示例：
        dimension = MySQLAutoFixFailDimension(xxxx)
        event = MonitorEvent(
            event_name=MonitorEventType.MYSQL_DBHA_AUTOFIX_FAILED,
            event={"content": "xxx"},
            dimension=dimension)
        )
        BKMonitorV3EventApi.send_event([event])
        """
        # 初始化请求地址
        self.__init_conf()
        # 补充事件data基础信息
        now_ms = int(time.time() * 1000)
        formatted_events = []
        for event in events:
            event.target = event.target if event.target else "dbm_event"
            event.timestamp = event.timestamp if event.timestamp else now_ms
            formatted_events.append(asdict(event))
        # 上报事件
        self.send_monitor_event(
            params={"data": formatted_events, "access_token": self.ACCESS_TOKEN, "data_id": self.DATA_ID},
            use_admin=True,
        )


BKMonitorV3Api = _BKMonitorV3Api()
BKMonitorV3EventApi = _BKMonitorV3EventApi()
