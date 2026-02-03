"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import json
import re

from django.utils import timezone
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow import StaticIntervalGenerator

import backend.dbm_aiagent.agent.commands as commands
from backend.configuration.constants import DBType
from backend.core import notify
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.agent.handlers import AgentHandler
from backend.flow.models import FlowTree
from backend.flow.plugins.components.collections.common.sidecar_service_abc import SidecarServiceABC
from backend.utils.time import datetime2str

cpl = re.compile(r"\[ai_result](?P<context>.+?)\[ai_result]")

# 定义不同DB组件调用对应的智能体快捷指令的MAP
ASK_AI_COMMAND_MAP = {
    DBType.MySQL: commands.CheckMysqlClusterCommand,
    DBType.TenDBCluster: commands.CheckMysqlClusterCommand,
    DBType.Sqlserver: commands.CheckSQLServerClusterCommand,
}


class CheckClusterAlarmForAIService(SidecarServiceABC):
    """
    定义单据值守通用的component
    检查单据运行期间， 通过AI方式计算出对应集群信息，所产生的告警记录
    收集到告警记录，推送给DBA+提单者

    Attributes:
        interval: 轮询间隔时间生成器，每30秒执行一次检查
    """

    interval = StaticIntervalGenerator(30)

    def sidecar_func(self, data, parent_data) -> bool:
        """
        侧车服务核心函数：监控集群告警并通过AI分析风险

        该方法会定期检查单据执行期间相关集群的告警信息，通过AI智能体分析风险等级，
        并在检测到高风险时自动推送通知给DBA和提单者。

        工作流程:
            1. 获取单据关联的集群ID列表和全局数据
            2. 查询集群元数据信息（域名等）
            3. 调用AI智能体分析集群在单据执行期间的告警情况
            4. 解析AI分析结果，判断是否需要推送通知
            5. 如果存在高风险，通过机器人推送消息给相关人员

        Args:
            data: Pipeline数据对象，包含以下输入参数:
                - kwargs (dict): 关键字参数，必须包含:
                    - cluster_ids (list): 需要监控的集群ID列表
                - global_data (dict): 全局数据，必须包含:
                    - job_root_id (str): 任务根ID，用于查询FlowTree
            parent_data: Pipeline父节点数据对象（本方法中未使用）

        Returns:
            bool: 执行结果
                - True: 执行成功（包括AI调用失败或推送失败的情况，这些被视为非致命错误）
                - False: 执行失败（仅在集群元数据查询为空时返回）

        Raises:
            不会主动抛出异常，所有异常都会被捕获并记录日志

        Note:
            - AI调用失败或消息推送失败不会导致方法返回False，而是记录错误日志后返回True
            - 这样设计是为了避免AI服务异常影响主流程的执行
            - AI返回结果中需要包含特定格式的标记: [ai_result]{"is_send_user": true/false}[ai_result]

        Example:
            AI返回结果格式示例:
            ```
            分析结果：集群存在高风险告警...
            [ai_result]{"is_send_user": true}[ai_result]
            ```
        """
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        cluster_ids = kwargs["cluster_ids"]
        root_id = global_data["job_root_id"]
        flow_tree = FlowTree.objects.get(root_id=root_id)
        flow_start_time = flow_tree.created_at
        ticket_id = int(flow_tree.uid)
        now_time = timezone.now()

        clusters = Cluster.objects.filter(id__in=cluster_ids)
        if not clusters:
            # 打印异常日志，但是不报错
            self.log_error(_("查询集群元数据为空，请检查传入的cluster_ids列表是否有问题:{}".format(cluster_ids)))
            return True
        cluster_domains = [c.immute_domain for c in clusters]
        self.log_info(_("-------------------分割线-------------------"))
        self.log_info(_("监听集群有：{}".format(cluster_domains)))
        self.log_info(_("监听的时间区间是：{}-{}".format(datetime2str(flow_start_time), datetime2str(now_time))))
        try:
            ai_result = AgentHandler.ask_agent_with_command(
                command=ASK_AI_COMMAND_MAP[DBType(flow_tree.db_type)].command,
                command_params={
                    "bk_biz_id": clusters[0].bk_biz_id,
                    "cluster_domains": cluster_domains,
                    "start_time": datetime2str(flow_start_time),
                    "end_time": datetime2str(now_time),
                },
            )
        except Exception as err:
            # 消息推送出现失败，正常输出错误日志，不触发异常
            self.log_error(_("调用智能体分析失败，失败原因：{}".format(err)))
            return True

        self.log_info(_("智能体输出的结果：{}".format(ai_result)))

        try:
            # 根据ai的分析结果，捕捉是否推送的用户的关键信息
            is_send_info = json.loads(re.search(cpl, ai_result).group("context"))
            if is_send_info and is_send_info.get("is_send_user"):
                # 从智能体根据结果分析来看， 结果为高风险，需要推送给提单者
                # 通过机器人给相关人员推送信息
                # 过滤无效信息
                self.log_info(_("正在把AI分析结果推送给提单者..."))
                send_result = ai_result.replace('[ai_result]{"is_send_user": true}[ai_result]', "")
                notify.send_msg_for_ai_task_guardian(ticket_id=ticket_id, ai_result=send_result)
                self.log_info(_("推送完成"))

        except Exception as err:
            # 消息推送出现失败，正常输出错误日志，不触发异常
            self.log_error(_("推送AI分析结果失败，失败原因：{}".format(err)))

        return True


class CheckClusterAlarmForAIComponent(Component):
    """
    集群告警AI检查组件

    Pipeline组件封装类，用于在流程中集成集群告警AI检查服务。
    该组件会作为侧车服务定期运行，监控集群健康状态。

    Attributes:
        name (str): 组件名称，使用模块名
        code (str): 组件唯一标识码
        bound_service (class): 绑定的服务类，指向CheckClusterAlarmForAIService
    """

    name = __name__
    code = "sidecar_check_cluster_alarm_for_ai"
    bound_service = CheckClusterAlarmForAIService
