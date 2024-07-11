"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.core.consts import BK_PKG_INSTALL_PATH
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.exceptions import ClusterNotExistException, DBMetaException
from backend.db_meta.models import Cluster
from backend.db_services.mysql.sql_import.constants import BKREPO_SQLFILE_PATH
from backend.flow.consts import LONG_JOB_TIMEOUT
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload


class MysqlDataMigrateFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        此flow用于数据迁移
        1个源集群迁移数据到多个目标集群
        tenDBHA导出导入库表结构、数据都在主db上进行
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data
        self.data["uid"] = self.data.get("uid") or self.root_id
        self.uid = self.data["uid"]
        self.work_dir = "mysql_data_migration"

    def __get_cluster_info(self, cluster_id: int, bk_biz_id: int) -> dict:
        """
        获取集群基本信息 source与target共用
        @param cluster_id: 集群cluster_id
        @param bk_biz_id: 业务id
        @return:
        """
        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(cluster_id=cluster_id, bk_biz_id=bk_biz_id, message=_("集群不存在"))

        if cluster.cluster_type == ClusterType.TenDBHA.value:
            ip_port = cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER).ip_port
        elif cluster.cluster_type == ClusterType.TenDBSingle.value:
            ip_port = cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.ORPHAN).ip_port
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

    def __get_target_cluster(self, info: dict) -> list:
        """
        @param target_cluster_ids: 列表，循环获取详细集群信息
        @return: 获取目标集群相关信息
        """
        target_clusters = []
        for tc_id in info["target_clusters"]:
            target_cluster = self.__get_cluster_info(cluster_id=tc_id, bk_biz_id=self.data["bk_biz_id"])
            target_cluster["open_area_param"] = [{"db_list": info["db_list"], "schema": "migrate_database"}]
            target_clusters.append(target_cluster)
            target_cluster["work_dir"] = self.work_dir

        return target_clusters

    def __get_source_cluster(self, info: dict) -> dict:
        """
        @param target_cluster_ids: 列表，循环获取详细集群信息
        @return: 获取目标集群相关信息
        """
        # 返回字典类型
        source_cluster = self.__get_cluster_info(cluster_id=info["source_cluster"], bk_biz_id=self.data["bk_biz_id"])
        # 字典增加键值
        source_cluster["open_area_param"] = [{"db_list": info["db_list"]}]
        source_cluster["work_dir"] = self.work_dir
        return source_cluster

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

    def __get_all_cluster_id(self) -> list:
        """
        获取所有集群id，包括原集群与目标集群，用于密码随机化
        @return:
        """
        cluster_ids = []
        for info in self.data["infos"]:
            cluster_ids.append(info["source_cluster"])
            for target_cluster in info["target_clusters"]:
                cluster_ids.append(target_cluster)

        return cluster_ids

    def mysql_data_migrate_flow(self):
        cluster_ids = self.__get_all_cluster_id()
        pipeline = Builder(root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=list(set(cluster_ids)))
        sub_pipelines = []
        n = 0
        for info in self.data["infos"]:
            n += 1
            source_cluster = self.__get_source_cluster(info)
            target_clusters = self.__get_target_cluster(info)
            exec_ip_list = self.__get_exec_ip_list(source_cluster, target_clusters)

            dump_dir_name = "{}_{}_migrate".format(self.root_id, n)

            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            sub_pipeline.add_act(
                act_name=_("下发db_actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=source_cluster["bk_cloud_id"],
                        exec_ip=exec_ip_list,
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            source_cluster["dump_dir_name"] = dump_dir_name
            sub_pipeline.add_act(
                act_name=_("从源实例{}#{}获取库".format(source_cluster["ip"], source_cluster["port"])),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        bk_cloud_id=source_cluster["bk_cloud_id"],
                        cluster_type=source_cluster["cluster_type"],
                        cluster=source_cluster,
                        exec_ip=source_cluster["ip"],
                        job_timeout=LONG_JOB_TIMEOUT,
                        get_mysql_payload_func=MysqlActPayload.get_data_migrate_dump_payload.__name__,
                    )
                ),
            )

            # 源集群不需要下发，移除其ip
            exec_ip_list.remove(source_cluster["ip"])
            # 源实例与目标实例在同一个机器上，下发ip列表为空，会报错
            if len(exec_ip_list) > 0:
                migrate_tar_file_name = "{}.tar.gz".format(dump_dir_name)
                migrate_md5sum_file_name = "{}.md5sum".format(dump_dir_name)
                sub_pipeline.add_act(
                    act_name=_("下发库表文件到目标实例"),
                    act_component_code=TransFileComponent.code,
                    kwargs=asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=source_cluster["bk_cloud_id"],
                            exec_ip=exec_ip_list,
                            file_target_path="{}/{}".format(BK_PKG_INSTALL_PATH, self.work_dir),
                            file_list=GetFileList(db_type=DBType.MySQL).mysql_import_sqlfile(
                                path=BKREPO_SQLFILE_PATH.format(biz=self.data["bk_biz_id"]),
                                filelist=[migrate_tar_file_name, migrate_md5sum_file_name],
                            ),
                        )
                    ),
                )

            acts_list = []
            for target_cluster in target_clusters:
                target_cluster["dump_dir_name"] = dump_dir_name
                acts_list.append(
                    {
                        "act_name": _("向目标实例:{}#{}导入库".format(target_cluster["ip"], target_cluster["port"])),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(
                            ExecActuatorKwargs(
                                bk_cloud_id=target_cluster["bk_cloud_id"],
                                cluster_type=target_cluster["cluster_type"],
                                cluster=target_cluster,
                                exec_ip=target_cluster["ip"],
                                job_timeout=LONG_JOB_TIMEOUT,
                                get_mysql_payload_func=MysqlActPayload.get_data_migrate_import_payload.__name__,
                            )
                        ),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("数据迁移流程")))

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline(is_drop_random_user=True)
