import copy
import logging
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.flow.consts import DBA_ROOT_USER, LONG_JOB_TIMEOUT
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_partition_report import MysqlPartitionReportComponent
from backend.flow.utils.mysql.mysql_act_dataclass import ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import MysqlPartitionContext

logger = logging.getLogger("flow")


class MysqlPartitionCronFlow(object):
    """
    分区定时任务单据的流程引擎
    {
        "uid": "xxx",
        "root_id": 123,
        "created_by": "xxx",
        "bk_biz_id": "xxx",
        "ticket_type": "MYSQL_PARTITION_CRON",
        "infos": [
            {
                "bk_cloud_id": 0,
                "ip": "1.1.1.1",
                "file_name": "xxx"
            }
        ]
    }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def mysql_partition_cron_flow(self):
        """
        每个分区配置一个子流程：
        （1）检查表结构
        （2）获取分区变更的sql
        （3）dbactor执行分区指令
        """
        mysql_partition_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        for info in self.data["infos"]:
            sub_data = copy.deepcopy(self.data)
            sub_data.pop("infos")
            sub_pipeline = SubBuilder(root_id=self.root_id, data={**sub_data, **info})
            sub_pipeline.add_act(
                act_name=_("actuator执行partition"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        job_timeout=LONG_JOB_TIMEOUT,
                        exec_ip=info["ip"],
                        bk_cloud_id=info["bk_cloud_id"],
                        run_as_system_user=DBA_ROOT_USER,
                        get_mysql_payload_func=MysqlActPayload.get_partition_cron_payload.__name__,
                    )
                ),
                write_payload_var="partition_report",
            )

            sub_pipeline.add_act(
                act_name=_("生成分区执行报告"),
                act_component_code=MysqlPartitionReportComponent.code,
                kwargs={},
            )
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("ip[{}]的分区任务").format(info["ip"])))
        mysql_partition_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        logger.info(_("构建mysql partition 定时任务流程成功"))
        mysql_partition_pipeline.run_pipeline(init_trans_data_class=MysqlPartitionContext(), is_drop_random_user=True)
