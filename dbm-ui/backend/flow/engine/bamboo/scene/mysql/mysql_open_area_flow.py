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
import copy
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.core.consts import BK_PKG_INSTALL_PATH
from backend.db_meta.enums import ClusterType, InstanceInnerRole, TenDBClusterSpiderRole
from backend.db_meta.exceptions import ClusterNotExistException, DBMetaException
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.authorize_rules import AuthorizeRulesComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload


class MysqlOpenAreaFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        tenDBHA导出导入库表结构、数据都在主db上进行
        tenDBCluster在中控主节点上导出导入库表结构、在spider节点上导出导入数据
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data
        self.data["uid"] = self.data.get("uid") or self.root_id
        self.uid = self.data["uid"]

        self.work_dir = f"{BK_PKG_INSTALL_PATH}/mysql_open_area"
        self.schema_tar_file_name = f"{self.root_id}_schema.tar.gz"
        self.schema_md5sum_file_name = f"{self.root_id}_schema.md5sum"
        self.data_tar_file_name = f"{self.root_id}_data.tar.gz"
        self.data_md5sum_file_name = f"{self.root_id}_data.md5sum"

    def __get_cluster_info(self, cluster_id: int, bk_biz_id: int, data_flag=False) -> dict:
        """
        获取集群基本信息 source与target共用
        @param cluster_id:
        @param bk_biz_id:
        @param data_flag: tenDBClusterspider节点上导出和导入数据，因此需要的是spider节点的信息
        @return:
        """
        try:
            # get查询时，结果只能有一个 查到多个结果会报错
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(cluster_id=cluster_id, bk_biz_id=bk_biz_id, message=_("集群不存在"))
        # 不同集群类型，下发的ip角色不一样
        # tenDBHA下发主db tenDBCluster库表下发中控主节点 数据下发spider节点
        if cluster.cluster_type == ClusterType.TenDBCluster.value:
            if data_flag:
                ip_port = (
                    cluster.proxyinstance_set.filter(
                        tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
                    )
                    .first()
                    .ip_port
                )
            else:
                ip_port = cluster.tendbcluster_ctl_primary_address()
        elif cluster.cluster_type == ClusterType.TenDBHA.value:
            ip_port = cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER).ip_port
        else:
            raise DBMetaException(message=_("集群实例类型不适用于开区"))

        return {
            "cluster_id": cluster.id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "cluster_type": cluster.cluster_type,
            "ip": ip_port.split(":")[0],
            "port": int(ip_port.split(":")[1]),
            "root_id": self.root_id,
        }

    def __get_source_cluster(self, data_flag=False) -> dict:
        """
        获取源实例的库表结构，可指定表
        区分tenDBHA与tenDBCluster
        @return:
        """
        source_cluster = self.__get_cluster_info(
            cluster_id=self.data["source_cluster"], bk_biz_id=self.data["bk_biz_id"], data_flag=data_flag
        )
        source_cluster["is_upload_bkrepo"] = self.__is_upload_bkrepo(
            source_cluster=self.data["source_cluster"], target_clusters=self.data["target_clusters"]
        )
        # 表列表只有在导出的时候才需要 导入的时候只需要知道新旧库名
        # 多个目标集群开区，但规则用的是一套相同的，因此取第一个获取库表开区规则
        if data_flag:
            source_cluster["open_area_param"] = [
                {"schema": exec_obj["source_db"], "tables": exec_obj["data_tblist"]}
                for exec_obj in self.data["target_clusters"][0]["execute_objects"]
                if len(exec_obj["data_tblist"]) > 0
            ]
        else:
            source_cluster["open_area_param"] = [
                {"schema": exec_obj["source_db"], "tables": exec_obj["schema_tblist"]}
                for exec_obj in self.data["target_clusters"][0]["execute_objects"]
            ]

        return source_cluster

    def __get_target_cluster(self, data_flag=False) -> list:
        """
        获取目标集群相关信息
        目标集群执行导入库表结构操作，需要知道原库表名称和新库表名称
        @return:
        """
        target_clusters = []
        for tc in self.data["target_clusters"]:
            target_cluster = self.__get_cluster_info(
                cluster_id=tc["target_cluster"], bk_biz_id=self.data["bk_biz_id"], data_flag=data_flag
            )
            if data_flag:
                target_cluster["open_area_param"] = [
                    {"schema": exec_obj["source_db"], "newdb": exec_obj["target_db"]}
                    for exec_obj in tc["execute_objects"]
                    if len(exec_obj["data_tblist"]) > 0
                ]
            else:
                target_cluster["open_area_param"] = [
                    {"schema": exec_obj["source_db"], "newdb": exec_obj["target_db"]}
                    for exec_obj in tc["execute_objects"]
                ]

            target_clusters.append(target_cluster)

        return target_clusters

    def __is_upload_bkrepo(self, source_cluster: int, target_clusters: list) -> bool:
        """
        本地开区，不用上传制品库
        集群维度判断
        tendbcluster集群 库表结构在中控 数据在spider节点 但属于同一集群
        有上传必然有下发 是否下发文件也用这个来判断
        @param source_cluster:
        @param target_clusters:
        @return:
        """
        for tc in target_clusters:
            if int(source_cluster) != int(tc["target_cluster"]):
                # 只要存在跟源集群不一样的 就要上传制品库
                return True

        return False

    def __get_exec_ip_list(self, source_cluster: dict, target_clusters: list) -> list:
        """
        过滤需要下发act的IP
        @param source_cluster:
        @param target_clusters:
        @return:
        """
        exec_ip_list = []
        exec_ip_list.append(source_cluster["ip"])
        for tc in target_clusters:
            if tc["ip"] not in exec_ip_list:
                exec_ip_list.append(tc["ip"])

        return exec_ip_list

    def __get_data_flag(self) -> bool:
        """
        判断是否需要迁移数据
        @return:
        """
        execute_objects = self.data["target_clusters"][0]["execute_objects"]
        for exe_obj in execute_objects:
            if len(exe_obj["data_tblist"]) > 0:
                return True

        return False

    def __get_all_cluster_id(self):
        """
        获取所有集群id，包括原集群与目标集群，用于密码随机化
        @return:
        """
        cluster_ids = []
        cluster_ids.append(self.data["source_cluster"])
        for target_cluster in self.data["target_clusters"]:
            cluster_ids.append(target_cluster["target_cluster"])

        return cluster_ids

    def mysql_open_area_flow(self):
        source_cluster_schema = self.__get_source_cluster(data_flag=False)
        target_clusters_schema = self.__get_target_cluster(data_flag=False)
        # 获取源集群与目标集群id
        cluster_ids = self.__get_all_cluster_id()
        # 提取要下发act的机器ip（过滤重复）
        exec_ip_list = self.__get_exec_ip_list(source_cluster_schema, target_clusters_schema)

        pipeline = Builder(root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=list(set(cluster_ids)))

        pipeline.add_act(
            act_name=_("下发db-actuator介质"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=source_cluster_schema["bk_cloud_id"],
                    exec_ip=exec_ip_list,
                    file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                )
            ),
        )

        pipeline.add_act(
            act_name=_("从源实例获取开区所需库表结构"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    bk_cloud_id=source_cluster_schema["bk_cloud_id"],
                    cluster_type=source_cluster_schema["cluster_type"],
                    cluster=source_cluster_schema,
                    exec_ip=source_cluster_schema["ip"],
                    get_mysql_payload_func=MysqlActPayload.get_open_area_dump_schema_payload.__name__,
                )
            ),
        )

        # 本地开区，没有上传制品库，也不用下发
        if source_cluster_schema["is_upload_bkrepo"]:
            # 目标集群下发库表文件，源集群不用下发
            exec_ip_list.remove(source_cluster_schema["ip"])
            pipeline.add_act(
                act_name=_("下发开区库表文件"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=0,
                        exec_ip=exec_ip_list,
                        file_target_path=self.work_dir,
                        file_list=GetFileList(db_type=DBType.MySQL).mysql_import_sqlfile(
                            path="mysql/sqlfile", filelist=[self.schema_tar_file_name, self.schema_md5sum_file_name]
                        ),
                    )
                ),
            )

        sub_pipelines = []
        for target_cluster in target_clusters_schema:
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            sub_pipeline.add_act(
                act_name=_("向目标实例导入库表结构"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        bk_cloud_id=target_cluster["bk_cloud_id"],
                        cluster_type=target_cluster["cluster_type"],
                        cluster=target_cluster,
                        exec_ip=target_cluster["ip"],
                        get_mysql_payload_func=MysqlActPayload.get_open_area_import_schema_payload.__name__,
                    )
                ),
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("目标集群开区导入表结构流程")))
        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 判断是否需要进行数据的迁移
        data_flag = self.__get_data_flag()
        if data_flag:
            pipeline.add_sub_pipeline(sub_flow=self.open_area_data_flow())

        # 判断是否对开区的集群进行授权
        if self.data.get("rules_set"):
            pipeline.add_act(
                act_name=_("添加mysql规则授权"), act_component_code=AuthorizeRulesComponent.code, kwargs=self.data
            )

        pipeline.run_pipeline(is_drop_random_user=True)

    def open_area_data_flow(self):
        """
        用于构建导入导出数据的子流程
        库表信息和导入导出表结构不一样 主要是指定表不一样
        对于数据来说，空列表表示不导出数据，只有指定的时候才进行操作
        另外，对于tenDBCluster集群来说，导出导入数据在spider节点上进行，需要单独再下发一次act
        @return:
        """
        # 获取导入导出数据集群参数
        source_cluster_data = self.__get_source_cluster(data_flag=True)
        target_clusters_data = self.__get_target_cluster(data_flag=True)
        # 获取之后操作的所有ip，过滤重复值
        exec_ip_list = self.__get_exec_ip_list(source_cluster_data, target_clusters_data)

        sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))

        # tenDBCluster集群需要给spider下发act
        if source_cluster_data["cluster_type"] == ClusterType.TenDBCluster.value:
            sub_pipeline.add_act(
                act_name=_("下发db-actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=source_cluster_data["bk_cloud_id"],
                        exec_ip=exec_ip_list,
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )
        sub_pipeline.add_act(
            act_name=_("从源实例获取开区所需库表数据"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    bk_cloud_id=source_cluster_data["bk_cloud_id"],
                    cluster_type=source_cluster_data["cluster_type"],
                    cluster=source_cluster_data,
                    exec_ip=source_cluster_data["ip"],
                    get_mysql_payload_func=MysqlActPayload.get_open_area_dump_data_payload.__name__,
                )
            ),
        )

        # 本地开区，没有上传制品库，也不用下发
        if source_cluster_data["is_upload_bkrepo"]:
            # 目标集群下发库表文件，源集群不用下发
            exec_ip_list.remove(source_cluster_data["ip"])
            sub_pipeline.add_act(
                act_name=_("下发开区库表数据文件"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=0,
                        exec_ip=exec_ip_list,
                        file_target_path=self.work_dir,
                        file_list=GetFileList(db_type=DBType.MySQL).mysql_import_sqlfile(
                            path="mysql/sqlfile", filelist=[self.data_tar_file_name, self.data_md5sum_file_name]
                        ),
                    )
                ),
            )

        acts_list = []
        for target_cluster in target_clusters_data:
            acts_list.append(
                {
                    "act_name": _("向目标实例导入库表数据"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=target_cluster["bk_cloud_id"],
                            cluster_type=target_cluster["cluster_type"],
                            cluster=target_cluster,
                            exec_ip=target_cluster["ip"],
                            get_mysql_payload_func=MysqlActPayload.get_open_area_import_data_payload.__name__,
                        )
                    ),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=acts_list)

        return sub_pipeline.build_sub_process(sub_name=_("开区数据迁移流程"))
