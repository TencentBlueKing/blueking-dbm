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

from django.utils.translation import gettext as _

from backend import env
from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.exceptions import ClusterNotExistException, DBMetaException
from backend.db_meta.models import Cluster
from backend.flow.consts import LONG_JOB_TIMEOUT
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.initiative_download_file import InitiativeDownloadFileComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    InitiativeDownloadFileKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload


class MysqlPartitionV2Flow(object):
    """
    mysql分区flow v2
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def __get_cluster_info(self):
        """
        拼接集群信息
        @return:
        """
        cluster_id = self.data["cluster_id"]
        try:
            cluster = Cluster.objects.get(id=cluster_id)
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(id=cluster_id, message=_("集群不存在"))

        if cluster.cluster_type == ClusterType.TenDBHA.value:
            ip_port = cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER).ip_port
        elif cluster.cluster_type == ClusterType.TenDBSingle.value:
            ip_port = cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.ORPHAN).ip_port
        elif cluster.cluster_type == ClusterType.TenDBCluster:
            ip_port = cluster.tendbcluster_ctl_primary_address()
        else:
            raise DBMetaException(message=_("集群实例类型不适用于分区"))

        return {
            "bk_biz_id": cluster.bk_biz_id,
            "cluster_id": cluster_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "cluster_type": cluster.cluster_type,
            "ip": ip_port.split(IP_PORT_DIVIDER)[0],
            "port": int(ip_port.split(IP_PORT_DIVIDER)[1]),
        }

    def mysql_partition_v2_flow(self):
        target_cluster = self.__get_cluster_info()

        pipeline = Builder(root_id=self.root_id, data=self.data)

        if env.INITIATIVE_DOWNLOAD:
            file_url, md5sum = GetFileList().get_db_actuator_download_info()
            pipeline.add_act(
                act_name=_("主动下载db-actuator介质]"),
                act_component_code=InitiativeDownloadFileComponent.code,
                kwargs=asdict(
                    InitiativeDownloadFileKwargs(
                        bk_cloud_id=target_cluster["bk_cloud_id"],
                        exec_ip=target_cluster["ip"],
                        file_url=file_url,
                        md5sum=md5sum,
                    )
                ),
            )
        else:
            pipeline.add_act(
                act_name=_("下发db-actuator介质[云区域ID: {}]".format(target_cluster["bk_cloud_id"])),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=target_cluster["bk_cloud_id"],
                        exec_ip=target_cluster["ip"],
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

        pipeline.add_act(
            act_name=_("分区优化执行"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    bk_cloud_id=target_cluster["bk_cloud_id"],
                    cluster_type=target_cluster["cluster_type"],
                    cluster=target_cluster,
                    exec_ip=target_cluster["ip"],
                    job_timeout=LONG_JOB_TIMEOUT,
                    get_mysql_payload_func=MysqlActPayload.get_partition_v2_payload.__name__,
                )
            ),
        )

        pipeline.run_pipeline(is_drop_random_user=True)
