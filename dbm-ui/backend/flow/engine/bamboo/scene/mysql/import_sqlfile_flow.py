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

from backend.components import DBConfigApi
from backend.components.db_remote_service.client import DRSApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.core import consts
from backend.db_meta.enums.instance_role import InstanceRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_services.mysql.sql_import.constants import BKREPO_SQLFILE_PATH
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.create_ticket import CreateTicketComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.semantic_check import SemanticCheckComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload

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
        增加单据临时ADMIN账号的添加和删除逻辑
        """
        p = Builder(
            root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=list(set(self.data["cluster_ids"]))
        )
        sub_pipelines = []
        base_path = self.data["path"]
        sql_files = self.__get_sql_file_name_list()

        for cluster_id in self.data["cluster_ids"]:
            cluster = self.__get_master_instance_info(cluster_id=cluster_id)
            backend_port = cluster["port"]
            sqlpath = os.path.join(consts.BK_PKG_INSTALL_PATH, f"sqlfile_{self.uid}_{cluster_id}_{backend_port}") + "/"
            sub_pipeline = SubBuilder(self.root_id, self.data)

            sub_pipeline.add_parallel_acts(
                acts_list=[
                    (
                        {
                            "act_name": _("下发db-actuator介质"),
                            "act_component_code": TransFileComponent.code,
                            "kwargs": asdict(
                                DownloadMediaKwargs(
                                    bk_cloud_id=cluster["bk_cloud_id"],
                                    exec_ip=cluster["backend_ip"],
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
                                    bk_cloud_id=cluster["bk_cloud_id"],
                                    exec_ip=cluster["backend_ip"],
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
                        exec_ip=cluster["backend_ip"],
                        bk_cloud_id=cluster["bk_cloud_id"],
                        cluster=cluster,
                        get_mysql_payload_func=MysqlActPayload.get_import_sqlfile_payload.__name__,
                    )
                ),
            )
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("[{}]执行SQL变更".format(cluster["name"]))))

        p.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        p.run_pipeline(is_drop_random_user=True)

    def sql_semantic_check_flow(self):
        """
        SQL语义检测流程编排，如果是个多集群执行SQL导入，默认拿集群列表第一位的库表结构来检验，加速输出校验结果
        todo 这块涉及到调用bcs来创建临时实例，这块需要怎么考虑兼容跨云管理
        """

        semantic_check_pipeline = Builder(
            root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=[self.data["cluster_ids"][0]]
        )

        template_cluster = self.__get_master_instance_info(cluster_id=self.data["cluster_ids"][0])
        cluster_type = template_cluster["cluster_type"]
        template_db_version = self.__get_version_and_charset(
            db_module_id=template_cluster["db_module_id"], cluster_type=cluster_type
        )
        backend_ip = template_cluster["backend_ip"]
        backend_port = template_cluster["port"]
        bk_cloud_id = template_cluster["bk_cloud_id"]
        backend_charset = self.__get_backend_charset(backend_ip, backend_port, bk_cloud_id)
        logger.info(f"backend_charset: {backend_charset}")

        semantic_check_pipeline.add_act(
            act_name=_("给模板集群下发db-actuator"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=bk_cloud_id,
                    exec_ip=backend_ip,
                    file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                )
            ),
        )

        semantic_check_pipeline.add_act(
            act_name=_("备份测试库表结构"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    bk_cloud_id=bk_cloud_id,
                    exec_ip=backend_ip,
                    cluster=template_cluster,
                    get_mysql_payload_func=MysqlActPayload.get_semantic_dump_schema_payload.__name__,
                )
            ),
        )

        semantic_check_pipeline.add_act(
            act_name=_("对SQL文件进行语义测试"),
            act_component_code=SemanticCheckComponent.code,
            kwargs={
                "cluster": template_cluster,
                "cluster_type": cluster_type,
                "payload": {
                    "uid": self.data["uid"],
                    "mysql_version": template_db_version,
                    "mysql_charset": backend_charset,
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

        semantic_check_pipeline.run_pipeline(is_drop_random_user=True)

    def __get_master_instance_info(self, cluster_id: int) -> dict:
        cluster = Cluster.objects.get(id=cluster_id)
        backend_info = StorageInstance.objects.filter(
            cluster=cluster,
            instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER],
        ).first()
        if not backend_info:
            raise Exception(_("查询不到可执行的实例！！！"))
        logger.info(f"get backend info: {backend_info}")
        return {
            "id": cluster_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "name": cluster.name,
            "port": backend_info.port,
            "backend_ip": backend_info.machine.ip,
            "db_module_id": cluster.db_module_id,
            "cluster_type": cluster.cluster_type,
            "semantic_dump_schema_file_name": self.semantic_dump_schema_file_name,
        }

    def __get_sql_file_name_list(self) -> list:
        file_list = []
        for obj in self.data["execute_objects"]:
            file_list.append(obj["sql_file"])
        return file_list

    def __get_version_and_charset(self, db_module_id, cluster_type) -> Any:
        """
        获取集群版本号(大版本号)
        @param db_module_id 集群记录的db模块id
        @param cluster_type 集群集群的类型
        todo 由于db-meta没有存储实例的版本信息，所以需要回调查询，后续优化后会删除这块代码
        """
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(self.data["bk_biz_id"]),
                "level_name": LevelName.MODULE,
                "level_value": str(db_module_id),
                "conf_file": "deploy_info",
                "conf_type": "deploy",
                "namespace": cluster_type,
                "format": FormatType.MAP,
            }
        )["content"]
        return data["db_version"]

    def __get_backend_charset(self, ip, port, bk_cloud_id) -> str:
        # 获取远端字符集
        logger.info(f"param: {ip}:{port}")
        body = {
            "addresses": ["{}{}{}".format(ip, IP_PORT_DIVIDER, port)],
            "cmds": ["show global variables like 'character_set_client'"],
            "force": False,
            "bk_cloud_id": bk_cloud_id,
        }

        resp = DRSApi.rpc(body)
        logger.info(f"query charset {resp}")

        if not resp[0]["cmd_results"]:
            raise Exception(_("DRS查询字符集失败：{}").format(resp[0]["error_msg"]))

        charset = resp[0]["cmd_results"][0]["table_data"][0]["Value"]
        if not charset:
            logger.error(_("获取字符集为空..."))
            raise Exception(_("获取字符集为空"))
        return charset
