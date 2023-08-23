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
import logging.config
import os
from dataclasses import asdict
from typing import Any, Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import DEFAULT_BK_CLOUD_ID, IP_PORT_DIVIDER
from backend.core import consts
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.instance_role import InstanceRole
from backend.db_meta.enums.machine_type import MachineType
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.db_services.mysql.sql_import.constants import BKREPO_SQLFILE_PATH
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.create_ticket import CreateTicketComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.semantic_check import SemanticCheckComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.spider.spider_bk_config import get_spider_version_and_charset

logger = logging.getLogger("flow")


class ImportSQLFlow(object):
    """
    执行SQL导入
    支持多云区域合并操作
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data
        self.data["uid"] = self.data.get("uid") or self.root_id
        self.uid = self.data["uid"]

        # 定义好每次语义检测的库表备份文件名称
        self.semantic_dump_schema_file_name = f"{self.root_id}_semantic_dump_schema.sql"

    def import_sqlfile_flow(self):
        """
        执行SQL文件的流程编排定义
        """
        p = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        base_path = self.data["path"]
        sql_files = self.__get_sql_file_name_list()

        for cluster_id in self.data["cluster_ids"]:
            cluster = self.__get_master_ctl_info(cluster_id)
            ctl_ip = cluster["master_ctl_ip"]
            bk_cloud_id = cluster["bk_cloud_id"]
            port = cluster["port"]

            sqlpath = os.path.join(consts.BK_PKG_INSTALL_PATH, f"sqlfile_{self.uid}_{cluster_id}_{port}") + "/"
            sub_pipeline = SubBuilder(self.root_id, self.data)

            sub_pipeline.add_parallel_acts(
                acts_list=[
                    (
                        {
                            "act_name": _("下发db-actuator介质"),
                            "act_component_code": TransFileComponent.code,
                            "kwargs": asdict(
                                DownloadMediaKwargs(
                                    bk_cloud_id=bk_cloud_id,
                                    exec_ip=ctl_ip,
                                    file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                                )
                            ),
                        }
                    ),
                    (
                        {
                            "act_name": _("下发SQL文件"),
                            "act_component_code": TransFileComponent.code,
                            "kwargs": asdict(
                                DownloadMediaKwargs(
                                    bk_cloud_id=bk_cloud_id,
                                    exec_ip=ctl_ip,
                                    file_target_path=sqlpath,
                                    file_list=GetFileList(db_type=DBType.MySQL).mysql_import_sqlfile(
                                        path=base_path, filelist=sql_files
                                    ),
                                )
                            ),
                        }
                    ),
                ]
            )

            sub_pipeline.add_act(
                act_name=_("执行SQL导入"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=ctl_ip,
                        bk_cloud_id=bk_cloud_id,
                        cluster=cluster,
                        get_mysql_payload_func=MysqlActPayload.get_import_sqlfile_payload.__name__,
                    )
                ),
            )
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("[{}]执行SQL变更".format(cluster["name"]))))

        p.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        p.run_pipeline()

    def sql_semantic_check_flow(self):
        """
        SQL语义检测流程编排，如果是个多集群执行SQL导入，默认拿集群列表第一位的库表结构来检验，加速输出校验结果
        todo 这块涉及到调用bcs来创建临时实例，这块需要怎么考虑兼容跨云管理
        """

        semantic_check_pipeline = Builder(root_id=self.root_id, data=self.data)
        cluster_id = self.data["cluster_ids"][0]
        cluster = self.__get_master_ctl_info(cluster_id)
        remotedb_version = self.__get_remotedb_version(cluster_id)
        spider_version = self.__get_spider_version(cluster_id)
        spider_charset = self.data["charset"]
        if self.data["charset"] == "default":
            spider_charset, config_spider_ver = get_spider_version_and_charset(
                bk_biz_id=cluster.bk_biz_id, db_module_id=cluster.db_module_id
            )
        semantic_check_pipeline.add_act(
            act_name=_("给模板集群下发db-actuator"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=cluster["bk_cloud_id"],
                    exec_ip=cluster["master_ctl_ip"],
                    file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                )
            ),
        )

        semantic_check_pipeline.add_act(
            act_name=_("备份测试库表结构"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    bk_cloud_id=cluster["bk_cloud_id"],
                    exec_ip=cluster["master_ctl_ip"],
                    cluster=cluster,
                    get_mysql_payload_func=MysqlActPayload.get_semantic_dump_schema_payload.__name__,
                )
            ),
        )

        semantic_check_pipeline.add_act(
            act_name=_("对SQL文件进行语义测试"),
            act_component_code=SemanticCheckComponent.code,
            kwargs={
                "cluster_type": ClusterType.TenDBCluster,
                "payload": {
                    "uid": self.data["uid"],
                    "spider_version": spider_version,
                    "mysql_version": remotedb_version,
                    "mysql_charset": spider_charset,
                    "path": BKREPO_SQLFILE_PATH,
                    "task_id": self.root_id,
                    "schema_sql_file": self.semantic_dump_schema_file_name,
                    "execute_objects": self.data["execute_objects"],
                },
            },
        )

        semantic_check_pipeline.add_act(
            act_name=_("创建SQL执行单据"), act_component_code=CreateTicketComponent.code, kwargs={}
        )

        semantic_check_pipeline.run_pipeline()

    def __get_master_ctl_info(self, cluster_id: int) -> dict:
        cluster = Cluster.objects.get(id=cluster_id)
        logger.info("get ")
        master_ctl_addr = cluster.tendbcluster_ctl_primary_address()
        master_ctl_ip = master_ctl_addr.split(IP_PORT_DIVIDER)[0]
        master_ctl_port = master_ctl_addr.split(IP_PORT_DIVIDER)[1]
        return {
            "id": cluster_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "name": cluster.name,
            "port": int(master_ctl_port),
            "master_ctl_ip": master_ctl_ip,
            "semantic_dump_schema_file_name": self.semantic_dump_schema_file_name,
        }

    def __get_remotedb_version(self, cluster_id: int) -> str:
        cluster = Cluster.objects.get(id=cluster_id)
        remotedb_list = StorageInstance.objects.filter(
            cluster=cluster,
            instance_role__in=[InstanceRole.REMOTE_MASTER],
        ).all()
        if not remotedb_list:
            raise Exception(_("查询remotedb version 失败"))
        logger.info(f"get backend info: {remotedb_list}")
        version = set()
        for remotedb in remotedb_list:
            version.add(remotedb.version)
        if len(version) > 1:
            raise Exception(_("存在多个版本{version}"))
        return version.pop()

    def __get_spider_version(self, cluster_id: int) -> str:
        cluster = Cluster.objects.get(id=cluster_id)
        proxy_list = ProxyInstance.objects.filter(
            cluster=cluster,
            machine_type__in=[MachineType.SPIDER],
        ).all()
        if not proxy_list:
            raise Exception(_("查询spider version 失败"))
        logger.info(f"get backend info: {proxy_list}")
        version = set()
        for remotedb in proxy_list:
            version.add(remotedb.version)
        if len(version) > 1:
            raise Exception(_("存在多个版本{version}"))
        return version.pop()

    def __get_sql_file_name_list(self) -> list:
        file_list = []
        for obj in self.data["execute_objects"]:
            file_list.append(obj["sql_file"])
        return file_list
