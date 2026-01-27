"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from datetime import datetime
from typing import Dict, List

from django.utils.translation import gettext as _

from backend import env
from backend.components import BKMonitorV3Api
from backend.db_monitor.constants import AlertLevelEnum, AlertStatusEnum


class QueryMonitorAlarm(object):
    """
    处理查询监控数据的类
    """

    @staticmethod
    def filter_alarm_by_create_time(alerts: List[Dict], start_time: datetime, end_time: datetime):
        """
        感觉蓝鲸监控返回的告警条数，在做二次过滤，过滤出某个时间范围中，生成的告警记录
        因为search_alert返回告警条目的时候，只要某类告警记录，它的未恢复的时间区间，和你传入的时间区间有交集，则也会返回过来
        但往往我们可能需要这个时间区间所产生的告警记录，所以设计这个方法，根据每条记录的 create_time, 做二次过滤
        同时这里还要过滤掉，处理阶段为“已屏蔽”的告警记录，因为通过接口过滤比较困难，所有把这块逻辑移到这里。
        @param alerts: 蓝鲸监控返回的告警记录列表
        @param start_time: 起始时间点
        @param end_time: 截止时间点
        """
        filter_alerts = []
        for alert in alerts:
            if (
                int(start_time.timestamp()) <= alert["create_time"] <= int(end_time.timestamp())
                and not alert["is_shielded"]
            ):
                # 精准匹配到过滤时间
                # 同时处理阶段不属于“已屏蔽”
                filter_alerts.append(alert)
        return filter_alerts

    @staticmethod
    def query_alarm_for_cluster_ids(
        bk_biz_id: int, cluster_domains: List[str], start_time: datetime, end_time: datetime
    ):
        """
        根据传入的时间范围，查询这段时间内的这批集群ID的告警信息
        @param cluster_domains: 查询的集群域名列表
        @param start_time: 查询的起始时间点
        @param end_time： 查询的截止时间点
        """
        query_param = {
            "bk_biz_ids": [env.DBA_APP_BK_BIZ_ID],
            "start_time": int(start_time.timestamp()),
            "end_time": int(end_time.timestamp()),
            "page": 1,
            "page_size": 10,
            "status": ["ABNORMAL"],
            "show_aggs": False,
            "show_overview": False,
            "query_string": "",
        }
        # 通用查询条件拼接 querystring
        # 过滤出对应的业务ID
        # 过滤出对应的集群域名的告警记录
        conditions = [
            f'tags.appid:"{bk_biz_id}"',
            " OR ".join([f'tags.cluster_domain:"{c}"' for c in cluster_domains]),
        ]
        query_param["query_string"] = " AND ".join(conditions)

        # 获取所有告警记录
        all_alerts = []
        while True:
            try:
                data = BKMonitorV3Api.search_alert(query_param)
                all_alerts.extend(data["alerts"])
                if len(data["alerts"]) == int(data["total"]):
                    # 代表返回的实际条数，与匹配到总条数相等，则证明这次的返回，已经全部返回，无需进入下一轮请求
                    break
                if len(data["alerts"]) == 0:
                    # 代表这次分页调用，已经到最后一步，无需进入下一轮请求
                    break

                # 修改query_param的分页参数，进入下一轮请求
                query_param["page"] += 1

            except Exception as err:
                raise Exception(_("调用BKMonitorV3Api失败:{}".format(err)))

        # 查询出来的结果
        return [
            {
                "alert_id": alart["id"],
                "alert_name": alart["alert_name"],
                "alert_status": AlertStatusEnum.get_choice_label(alart["status"]),
                "alert_severity": AlertLevelEnum.get_choice_label(int(alart["severity"])),
                "alert_create_time": int(alart["create_time"]),
                "tags": alart["tags"],
            }
            for alart in QueryMonitorAlarm.filter_alarm_by_create_time(all_alerts, start_time, end_time)
        ]
