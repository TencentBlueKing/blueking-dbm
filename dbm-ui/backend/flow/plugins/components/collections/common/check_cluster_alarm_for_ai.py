"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import datetime

from django.utils import timezone
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow import StaticIntervalGenerator

from backend.core import notify
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.common.impl.query_monitor_alarm_info import QueryMonitorAlarm
from backend.flow.models import FlowTree
from backend.flow.plugins.components.collections.common.sidecar_service_abc import SidecarServiceABC
from backend.utils.time import datetime2str


class CheckClusterAlarmForAIService(SidecarServiceABC):
    """
    定义单据值守通用的component
    检查单据运行期间， 通过AI方式计算出对应集群信息，所产生的告警记录
    收集到告警记录，推送给DBA+提单者
    """

    interval = StaticIntervalGenerator(30)

    def sidecar_func(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        cluster_ids = kwargs["cluster_ids"]
        root_id = global_data["job_root_id"]
        flow_tree = FlowTree.objects.get(root_id=root_id)
        flow_start_time = flow_tree.created_at
        ticket_id = int(flow_tree.uid)
        now_time = datetime.datetime.now(timezone.utc)

        clusters = Cluster.objects.filter(id__in=cluster_ids)
        if not clusters:
            self.log_error(_("查询集群元数据为空，请检查传入的cluster_ids列表是否有问题:{}".format(cluster_ids)))
            return False
        cluster_domains = [c.immute_domain for c in clusters]
        self.log_info(_("监听集群有：{}".format(cluster_domains)))
        self.log_info(_("监听的时间区间是：{}-{}".format(datetime2str(flow_start_time), datetime2str(now_time))))

        # todo 后续需要非交互式AI问答框架
        # 这里先直接调用mcp工具测试一下
        result = QueryMonitorAlarm.query_alarm_for_cluster_ids(
            bk_biz_id=clusters[0].bk_biz_id,
            cluster_domains=cluster_domains,
            start_time=flow_start_time,
            end_time=now_time,
        )
        # todo 目前集群无论是健康还是异常， 通过智能体分析的，都会返回结果。但是如何通过返回结果，判断是否推送给用户，这是目前的难题
        if result:
            # 通过机器人给相关人员推送信息
            notify.send_msg_for_ai_task_guardian(ticket_id=ticket_id, ai_result=result)
        return True


class CheckClusterAlarmForAIComponent(Component):
    name = __name__
    code = "sidecar_check_cluster_alarm_for_ai"
    bound_service = CheckClusterAlarmForAIService
