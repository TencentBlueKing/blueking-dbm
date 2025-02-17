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
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.core import consts
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.instance_role import InstanceRole
from backend.db_meta.enums.machine_type import MachineType
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
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
from backend.flow.utils.mysql.mysql_commom_query import merge_resp_to_cluster, parse_db_from_sqlfile
from backend.flow.utils.mysql.mysql_version_parse import major_version_parse
from backend.flow.utils.spider.spider_bk_config import get_spider_version_and_charset
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
            master_ctl_addr = cluster.tendbcluster_ctl_primary_address()
            cluster_bk_cloud_id_map_list.setdefault(cluster.bk_cloud_id, []).append(
                master_ctl_addr.split(IP_PORT_DIVIDER)[0]
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

        for cluster_id in self.data["cluster_ids"]:
            # 这样获取顺便可以验证是否传入非法的集群id
            cluster = clusters.get(id=cluster_id)
            master_ctl_addr = cluster.tendbcluster_ctl_primary_address()

            sub_pipeline = SubBuilder(self.root_id, self.data)
            sub_pipeline.add_act(
                act_name=_("执行SQL导入"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        job_timeout=LONG_JOB_TIMEOUT,
                        exec_ip=master_ctl_addr.split(IP_PORT_DIVIDER)[0],
                        bk_cloud_id=cluster.bk_cloud_id,
                        cluster={"port": int(master_ctl_addr.split(IP_PORT_DIVIDER)[1])},
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
        增加单据临时ADMIN账号的添加和删除逻辑
        """

        semantic_check_pipeline = Builder(
            root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=[self.data["cluster_ids"][0]]
        )
        cluster_id = self.data["cluster_ids"][0]
        cluster = self.__get_master_ctl_info(cluster_id)
        remotedb_version = self.__get_remotedb_version(cluster_id)
        spider_version = self.__get_spider_version(cluster_id)
        spider_charset = self.data["charset"]
        if self.data["charset"] == "default":
            spider_charset, config_spider_ver = get_spider_version_and_charset(
                bk_biz_id=cluster["bk_biz_id"], db_module_id=cluster["db_module_id"]
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
        # parse db from sqlfile
        sqlfile_list = itertools.chain(*[set(obj["sql_files"]) for obj in self.data["execute_objects"]])
        path = self.data["path"]
        resp = parse_db_from_sqlfile(path=path, files=list(sqlfile_list))
        if resp is None:
            logger.warning("root id:[{}]parse db from sqlfile resp is None,set dump_all to True.".format(self.root_id))
        else:
            cluster.update(merge_resp_to_cluster(resp))
        cluster["execute_objects"] = self.data["execute_objects"]
        cluster["semantic_dump_schema_file_name_suffix"] = self.semantic_dump_schema_file_name_suffix
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
                    "path": BKREPO_SQLFILE_PATH.format(biz=self.data["bk_biz_id"]),
                    "task_id": self.root_id,
                    "schema_sql_file": self.semantic_dump_schema_file_name,
                    "execute_objects": self.data["execute_objects"],
                },
            },
        )

        semantic_check_pipeline.add_act(
            act_name=_("创建SQL执行单据"),
            act_component_code=CreateTicketComponent.code,
            kwargs={
                "ticket_data": {
                    "is_auto_commit": self.data["is_auto_commit"],
                    "remark": "",
                    "ticket_type": TicketType.TENDBCLUSTER_IMPORT_SQLFILE,
                    "details": {"root_id": self.root_id},
                }
            },
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
            "bk_biz_id": cluster.bk_biz_id,
            "db_module_id": cluster.db_module_id,
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
            raise Exception(_("backend remote 存在多个版本:{}").format(version))
        return version.pop()

    def __get_spider_version(self, cluster_id: int) -> str:
        cluster = Cluster.objects.get(id=cluster_id)
        proxy_list = ProxyInstance.objects.filter(
            cluster=cluster,
            machine_type__in=[MachineType.SPIDER],
        ).all()
        if not proxy_list:
            raise Exception(_("查询spider version 失败"))
        logger.info(f"get spider list: {proxy_list}")
        version = set()
        major_version_set = set()
        for spider in proxy_list:
            major_version, sub_version = major_version_parse(spider.version)
            # 只判断spider1.x 和 spider 3.x 这样的差异性
            major_version_set.add(int(major_version / 1000000))
            version.add(spider.version)
        if len(major_version_set) > 1:
            raise Exception(_("spider中存在多个大版本不一致的情况:{},请找DBA处理下").format(version))
        return version.pop()

    def __get_sql_file_name_list(self) -> list:
        file_list = []
        for obj in self.data["execute_objects"]:
            file_list.extend(obj["sql_files"])
        return file_list
