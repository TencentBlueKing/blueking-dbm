import copy
import json
import logging
import os
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.crypto import get_random_string
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.core.consts import BK_PKG_INSTALL_PATH
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.exceptions import ClusterNotExistException, MasterInstanceNotExistException
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.consts import DBA_SYSTEM_USER
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.mysql.upload_file import UploadFileServiceComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs, UploadFile
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import MysqlPartitionContext

logger = logging.getLogger("flow")
BKREPO_PARTITION_PATH = "mysql/partition"


class SpiderPartitionFlow(object):
    """
    分区单据的流程引擎
    {
        "uid": "xxx",
        "root_id": 123,
        "created_by": "xxx",
        "bk_biz_id": "xxx",
        "ticket_type": "TENDBCLUSTER_PARTITION",
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

    def spider_partition_flow(self):
        """
        每个分区配置一个子流程：
        （1）检查表结构
        （2）获取分区变更的sql
        （3）dbactor执行分区指令
        """
        partition_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        for info in self.data["infos"]:
            sub_data = copy.deepcopy(self.data)
            sub_data.pop("infos")
            sub_pipeline = SubBuilder(root_id=self.root_id, data={**sub_data, **info})
            bk_cloud_id = info["bk_cloud_id"]

            sub_pipeline.add_act(
                act_name=_("下发actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=list(set([partition_object["ip"] for partition_object in info["partition_objects"]])),
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            upload_sql_file_list = []
            download_sql_file_list = []
            actuator_exec_list = []

            for partition_object in info["partition_objects"]:
                ip = partition_object["ip"]
                port = partition_object["port"]
                shard = partition_object["shard_name"]
                address_tip = "{} {}:{}".format(shard, ip, port)
                filename = _("partition_sql_file_{}_{}_{}_{}.txt".format(ip, port, shard, self.data["uid"]))

                upload_sql_file = dict()
                upload_sql_file["act_name"] = _("{}: {}".format("上传sql文件", address_tip))
                upload_sql_file["act_component_code"] = UploadFileServiceComponent.code
                upload_sql_file["kwargs"] = asdict(
                    UploadFile(
                        path=os.path.join(BKREPO_PARTITION_PATH, filename),
                        content=json.dumps(partition_object["execute_objects"]),
                    )
                )
                upload_sql_file_list.append(upload_sql_file)

                sql_file_info = dict()
                sql_file_info["act_name"] = _("{}: {}".format(_("下发sql文件"), address_tip))
                sql_file_info["act_component_code"] = TransFileComponent.code
                sql_file_info["kwargs"] = asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=ip,
                        file_target_path=os.path.join(BK_PKG_INSTALL_PATH, "partition"),
                        file_list=GetFileList(db_type=DBType.MySQL).mysql_import_sqlfile(
                            path=BKREPO_PARTITION_PATH, filelist=[filename]
                        ),
                    )
                )
                download_sql_file_list.append(sql_file_info)

                cluster = {
                    "ip": ip,
                    "port": port,
                    "shard_name": shard,
                    "file_path": os.path.join(BK_PKG_INSTALL_PATH, filename),
                }
                exec_info = dict()
                exec_info["act_name"] = _("{}: {}".format(_("actuator执行partition"), address_tip))
                exec_info["act_component_code"] = ExecuteDBActuatorScriptComponent.code
                exec_info["kwargs"] = asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        bk_cloud_id=bk_cloud_id,
                        run_as_system_user=DBA_SYSTEM_USER,
                        get_mysql_payload_func=MysqlActPayload.get_partition_payload.__name__,
                        cluster=cluster,
                    )
                )
                actuator_exec_list.append(exec_info)

            sub_pipeline.add_parallel_acts(acts_list=upload_sql_file_list)
            sub_pipeline.add_parallel_acts(acts_list=download_sql_file_list)
            sub_pipeline.add_parallel_acts(acts_list=actuator_exec_list)

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("cluster[{}]的分区任务").format(info["immute_domain"]))
            )

        partition_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        logger.info(_("构建spider partition流程成功"))
        partition_pipeline.run_pipeline(init_trans_data_class=MysqlPartitionContext())
