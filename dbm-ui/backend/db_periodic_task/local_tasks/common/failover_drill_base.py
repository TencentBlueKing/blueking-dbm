"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from backend.components.hadb.client import HADBApi
from backend.db_report.models.failover_drill_report import FailoverDrillReport
from backend.db_services.redis.autofix.enums import DBHASwitchResult
from backend.utils.basic import generate_root_id


class BaseFailoverDrill:
    def __init__(
        self,
        city: str,
        labels: List[str],
        bk_biz_id: int,
        bk_cloud_id: int,
        city_map: Dict,
    ):
        self.main_task_id = generate_root_id()
        self.labels = labels
        self.city = city
        self.bk_biz_id = bk_biz_id
        self.bk_cloud_id = bk_cloud_id
        self.city_map = city_map
        self.failover_drill_info = {}

    @staticmethod
    def cluster_type() -> str:
        raise NotImplementedError

    def get_immute_domain(self):
        raise NotImplementedError

    def init_report(self):
        FailoverDrillReport.objects.create(
            bk_biz_id=self.bk_biz_id,
            bk_cloud_id=self.bk_cloud_id,
            status=False,
            main_task_id=self.main_task_id,
            cluster_domain=self.get_immute_domain(),
            cluster_type=self.cluster_type(),
            city=self.city,
            dhha_status=DBHASwitchResult.FAIL.value,
        )

    def get_city_abbr(self) -> str:
        """
        城市缩写
        """
        return self.city_map.get(self.city, "default")

    def get_cluster_name(self):
        """
        集群名称
        """
        return "failover-drill-{}".format(self.get_city_abbr())

    def get_dbha_switch_data(self):
        finished_time = datetime.now().astimezone(timezone.utc)
        start_time = finished_time - timedelta(hours=8)
        kwargs = {
            "cloud_id": self.bk_cloud_id,
            "app": str(self.bk_biz_id),
            "switch_start_time": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "switch_finished_time": finished_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        resp = HADBApi.switch_queue(params={"name": "query_switch_queue", "query_args": kwargs}, raw=True)
        return resp

    def update_drill_report(
        self, info: str, dbha_info: str = "", status: bool = False, dbha_status: str = DBHASwitchResult.FAIL.value
    ):
        """
        更新演练报告内容
        """
        report = FailoverDrillReport.objects.get(main_task_id=self.main_task_id)
        report.task_info = f"{report.task_info}\n{info}".strip()
        report.status = status
        report.dbha_status = dbha_status
        report.dbha_info = dbha_info
        report.save(update_fields=["task_info", "status", "dhha_status", "dbha_info"])
