import copy
import json
import logging
import os
import time
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.core.consts import BK_PKG_INSTALL_PATH
from backend.flow.consts import DBA_ROOT_USER, LONG_JOB_TIMEOUT
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_partition_report import MysqlPartitionReportComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.mysql.upload_file import UploadFileServiceComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs, UploadFile
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import MysqlPartitionContext

logger = logging.getLogger("flow")
BKREPO_PARTITION_PATH = "mysql/partition"


class MysqlPartitionFlow(object):
    """
    分区单据的流程引擎
    {
        "uid": "xxx",
        "root_id": 123,
        "created_by": "xxx",
        "bk_biz_id": "xxx",
        "db_app_abbr": "xxx",
        "bk_biz_name": "xxx",
        "ticket_type": "MYSQL_PARTITION",
        "infos": [
            {
                "config_id": 1,
                "cluster_id": 1,
                "immute_domain": "immute_domain",
                "bk_cloud_id": 0,
                "partition_objects": [
                    {
                        "ip": "xxx",
                        "port": xxx,
                        "shard_name": "SPT0",
                        "execute_objects": [
                            {
                                "config_id": 6,
                                "dblike": "db%",
                                "tblike": "tb1",
                                "init_partition": [
                                    "select * from db1.tb1;",
                                    "select * from db1.tb1;"
                                ],
                                "add_partition": [],
                                "drop_partition": []
                            }
                        ]
                    }
                ]
            }
        ]
    }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def mysql_partition_flow(self):
        """
        每个分区配置一个子流程：
        （1）检查表结构
        （2）获取分区变更的sql
        （3）dbactor执行分区指令
        """
        mysql_partition_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        cron_date = {"cron_date": time.strftime("%Y%m%d", time.localtime())}
        for info in self.data["infos"]:
            sub_data = copy.deepcopy(self.data)
            sub_data.pop("infos")
            sub_pipeline = SubBuilder(root_id=self.root_id, data={**sub_data, **info, **cron_date})
            bk_cloud_id = info["bk_cloud_id"]
            ip, port = info["partition_objects"][0]["ip"], info["partition_objects"][0]["port"]
            filename = "partition_sql_file_{}_{}_{}.json".format(ip, port, self.data["uid"])

            sub_pipeline.add_act(
                act_name=_("上传sql文件"),
                act_component_code=UploadFileServiceComponent.code,
                kwargs=asdict(
                    UploadFile(
                        path=os.path.join(BKREPO_PARTITION_PATH, filename),
                        content=json.dumps(info["partition_objects"]),
                    )
                ),
            )

            sub_pipeline.add_act(
                act_name=_("下发sql文件"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=ip,
                        file_target_path=os.path.join(BK_PKG_INSTALL_PATH, "partition"),
                        file_list=GetFileList(db_type=DBType.MySQL).mysql_import_sqlfile(
                            path=BKREPO_PARTITION_PATH, filelist=[filename]
                        ),
                    )
                ),
            )
            sub_pipeline.add_act(
                act_name=_("下发actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=ip,
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            cluster = {"ip": ip, "file_path": filename}
            sub_pipeline.add_act(
                act_name=_("actuator执行partition"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        job_timeout=LONG_JOB_TIMEOUT,
                        exec_ip=ip,
                        bk_cloud_id=bk_cloud_id,
                        run_as_system_user=DBA_ROOT_USER,
                        get_mysql_payload_func=MysqlActPayload.get_partition_payload.__name__,
                        cluster=cluster,
                    )
                ),
                write_payload_var="partition_report",
            )

            sub_pipeline.add_act(
                act_name=_("生成分区执行报告"),
                act_component_code=MysqlPartitionReportComponent.code,
                kwargs={},
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("cluster[{}]的分区任务").format(info["immute_domain"]))
            )
        mysql_partition_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        logger.info(_("构建mysql partition流程成功"))
        mysql_partition_pipeline.run_pipeline(init_trans_data_class=MysqlPartitionContext())
