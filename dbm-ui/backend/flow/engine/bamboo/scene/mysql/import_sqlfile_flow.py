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
import itertools
import logging.config
import os
from dataclasses import asdict
from typing import Any, Dict, Optional

from django.utils.translation import ugettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.configuration.constants import DBType
from backend.core import consts
from backend.db_meta.enums.instance_role import InstanceRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_services.mysql.sql_import.constants import BKREPO_SQLFILE_PATH
from backend.flow.consts import LONG_JOB_TIMEOUT
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.create_ticket import CreateTicketComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.semantic_check import SemanticCheckComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_commom_query import (
    merge_resp_to_cluster,
    parse_db_from_sqlfile,
    query_mysql_variables,
)
from backend.ticket.constants import TicketType

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
        self.semantic_dump_schema_file_name_suffix = "_semantic_dump_schema"
        self.semantic_dump_schema_file_name = f"{self.root_id}{self.semantic_dump_schema_file_name_suffix}.sql"

        # 定义SQL文件的下发位置
        self.sql_path_suffix = "sqlfile_"
        self.data["file_path_suffix"] = self.sql_path_suffix
        self.data["file_base_dir"] = consts.BK_PKG_INSTALL_PATH
        self.sql_path = os.path.join(consts.BK_PKG_INSTALL_PATH, f"{self.sql_path_suffix}{self.uid}") + "/"
        self.data["sql_path"] = self.sql_path

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
        clusters = Cluster.objects.filter(id__in=self.data["cluster_ids"])

        # 合并下发需要变更的文件，不同的bk_cloud_id需要分组处理
        act_lists = []
        cluster_bk_cloud_id_map_list = {}
        for cluster in clusters:
            cluster_bk_cloud_id_map_list.setdefault(cluster.bk_cloud_id, []).append(
                cluster.storageinstance_set.get(
                    instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
                ).machine.ip
            )

        for bk_cloud_id, ip_list in cluster_bk_cloud_id_map_list.items():
            act_lists.append(
                {
                    "act_name": _("下发db-actuator介质[云区域ID:{}]".format(bk_cloud_id)),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=bk_cloud_id,
                            exec_ip=list(filter(None, list(set(ip_list)))),
                            file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                        )
                    ),
                }
            )
            act_lists.append(
                {
                    "act_name": _("下发SQL文件[云区域ID:{}]".format(bk_cloud_id)),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=bk_cloud_id,
                            exec_ip=list(filter(None, list(set(ip_list)))),
                            file_target_path=self.sql_path,
                            file_list=GetFileList(db_type=DBType.MySQL).mysql_import_sqlfile(
                                path=base_path, filelist=sql_files
                            ),
                        )
                    ),
                }
            )

        p.add_parallel_acts(acts_list=act_lists)

        # 根据集群下发执行sql文件
        for cluster_id in self.data["cluster_ids"]:
            # 这样获取顺便可以验证是否传入非法的集群id
            cluster = clusters.get(id=cluster_id)
            master = cluster.storageinstance_set.get(
                instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
            )

            sub_pipeline = SubBuilder(self.root_id, self.data)
            sub_pipeline.add_act(
                act_name=_("执行SQL导入"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        job_timeout=LONG_JOB_TIMEOUT,
                        exec_ip=master.machine.ip,
                        bk_cloud_id=cluster.bk_cloud_id,
                        cluster={"port": master.port},
                        get_mysql_payload_func=MysqlActPayload.get_import_sqlfile_payload.__name__,
                    )
                ),
            )
            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("[{}]执行SQL变更".format(cluster.immute_domain)))
            )

        p.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        p.run_pipeline(is_drop_random_user=True)

    def sql_semantic_check_flow(self):
        """
        SQL语义检测流程编排，如果是个多集群执行SQL导入，默认拿集群列表第一位的库表结构来检验，加速输出校验结果
        todo 这块涉及到调用bcs来创建临时实例，这块需要怎么考虑兼容跨云管理
        """

        cluster_ids = self.data["cluster_ids"]
        if len(cluster_ids) <= 0:
            raise Exception(_("查询不到可执行的集群！！！"))
        templ_cluster_id = cluster_ids[0]
        cluster = Cluster.objects.get(id=templ_cluster_id)
        template_cluster = self.__get_master_instance_info(cluster=cluster)
        cluster_type = template_cluster["cluster_type"]
        template_db_version = self.__get_version_and_charset(
            db_module_id=cluster.db_module_id, cluster_type=cluster_type
        )
        backend_ip = template_cluster["backend_ip"]
        backend_port = template_cluster["port"]
        bk_cloud_id = template_cluster["bk_cloud_id"]
        origin_mysql_var_map = query_mysql_variables(host=backend_ip, port=backend_port, bk_cloud_id=bk_cloud_id)
        backend_charset = origin_mysql_var_map.get("character_set_client")
        start_mysqld_configs = {}
        logger.info(f"backend_charset: {backend_charset}")

        for var in ["sql_mode", "log_bin_trust_function_creators"]:
            if origin_mysql_var_map.__contains__(var):
                start_mysqld_configs[var] = origin_mysql_var_map.get(var)

        semantic_check_pipeline = Builder(
            root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=[templ_cluster_id]
        )

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
        # parse db from sqlfile
        sqlfile_list = itertools.chain(*[set(obj["sql_files"]) for obj in self.data["execute_objects"]])
        path = self.data["path"]
        resp = parse_db_from_sqlfile(path=path, files=list(sqlfile_list))
        if resp is None:
            logger.warning("root id:[{}]parse db from sqlfile resp is None,set dump_all to True.".format(self.root_id))
        else:
            template_cluster.update(merge_resp_to_cluster(resp))
        template_cluster["semantic_dump_schema_file_name_suffix"] = self.semantic_dump_schema_file_name_suffix
        template_cluster["execute_objects"] = self.data["execute_objects"]
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
                    "path": BKREPO_SQLFILE_PATH.format(biz=self.data["bk_biz_id"]),
                    "task_id": self.root_id,
                    "schema_sql_file": self.semantic_dump_schema_file_name,
                    "execute_objects": self.data["execute_objects"],
                    "mysql_start_config": start_mysqld_configs,
                },
            },
        )

        # 模拟执行成功串提单操作
        semantic_check_pipeline.add_act(
            act_name=_("创建SQL执行单据"),
            act_component_code=CreateTicketComponent.code,
            kwargs={
                "ticket_data": {
                    "is_auto_commit": self.data["is_auto_commit"],
                    "remark": "",
                    "ticket_type": TicketType.MYSQL_IMPORT_SQLFILE,
                    "details": {"root_id": self.root_id},
                }
            },
        )

        semantic_check_pipeline.run_pipeline(is_drop_random_user=True)

    def __get_master_instance_info(self, cluster: Cluster) -> dict:
        backend_info = StorageInstance.objects.filter(
            cluster=cluster,
            instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER],
        ).first()
        if not backend_info:
            raise Exception(_("查询不到可执行的实例！！！"))
        logger.info(f"get backend info: {backend_info}")
        return {
            "id": cluster.id,
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
            file_list.extend(obj["sql_files"])
        return list(set(file_list))

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
