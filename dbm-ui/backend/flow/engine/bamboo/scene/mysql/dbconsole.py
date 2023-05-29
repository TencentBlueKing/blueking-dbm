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
import time
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.components.db_remote_service.client import DRSApi
from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.instance_role import InstanceRole, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.flow.consts import LONG_JOB_TIMEOUT
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload

logger = logging.getLogger("flow")


class DbConsoleDumpSqlFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data
        self.data["uid"] = self.data.get("uid") or self.root_id
        self.uid = self.data["uid"]
        self.cluster_id = self.data["cluster_id"]
        self.cluster = Cluster.objects.get(id=self.cluster_id)
        self.dbconsole_dump_file_name = f"{self.cluster.immute_domain}_{int(time.time())}_dbm_console_dump.sql"

    def dump_flow(self):
        p = Builder(root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=[self.cluster_id])
        ro_instance_info = self.__get_read_instance(self.cluster)
        bk_cloud_id = ro_instance_info["bk_cloud_id"]
        exec_ip = ro_instance_info["ip"]
        # 此处可以根据延迟来考虑是否需要抛出错误
        if ro_instance_info["instance_role"] == InstanceRole.BACKEND_SLAVE:
            behind_master_sec = self.get_slave_delay_second(exec_ip, ro_instance_info["port"], bk_cloud_id)
            logger.info(f"slave delay sec: {behind_master_sec}")

        p.add_act(
            act_name=_("下发db-actuator介质"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=bk_cloud_id,
                    exec_ip=exec_ip,
                    file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                )
            ),
        )

        p.add_act(
            act_name=_("运行数据导出任务"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    job_timeout=LONG_JOB_TIMEOUT,
                    bk_cloud_id=bk_cloud_id,
                    exec_ip=exec_ip,
                    cluster=ro_instance_info,
                    get_mysql_payload_func=MysqlActPayload.get_dbconsole_schema_payload.__name__,
                )
            ),
        )
        # 运行pipeine
        p.run_pipeline(is_drop_random_user=True)

    def __get_read_instance(self, cluster: Cluster) -> dict:
        if cluster.cluster_type == ClusterType.TenDBCluster:
            backend_info = ProxyInstance.objects.filter(
                cluster=cluster,
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE,
            ).first()
            # 如果不存在slave spider,则使用master spider
            if backend_info is None:
                backend_info = ProxyInstance.objects.filter(
                    cluster=cluster,
                    tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER,
                ).first()
        else:
            backend_info = StorageInstance.objects.filter(
                cluster=cluster,
                instance_role__in=[
                    InstanceRole.ORPHAN,
                    InstanceRole.BACKEND_SLAVE,
                ],
            ).first()
        if backend_info is None:
            raise Exception(_("查询不到可执行的实例！！！"))

        logger.info(f"get backend info: {backend_info}")
        return {
            "id": cluster.id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "name": cluster.name,
            "port": backend_info.port,
            "ip": backend_info.machine.ip,
            "db_module_id": cluster.db_module_id,
            "cluster_type": cluster.cluster_type,
            "instance_role": backend_info.instance_role,
            "dbconsole_dump_file_name": self.dbconsole_dump_file_name,
        }

    def get_slave_delay_second(self, ip, port, bk_cloud_id) -> str:
        # 获取slave延迟
        logger.info(f"param: {ip}:{port}")
        body = {
            "addresses": ["{}{}{}".format(ip, IP_PORT_DIVIDER, port)],
            "cmds": ["show slave status"],
            "force": False,
            "bk_cloud_id": bk_cloud_id,
        }

        resp = DRSApi.rpc(body)
        logger.info(f"query slave status: {resp}")

        if not resp[0]["cmd_results"]:
            raise Exception(_("DRS查询主从延迟失败：{}").format(resp[0]["error_msg"]))

        # TODO: 暂时注释这一块延时校验
        # behind_master_sec = resp[0]["cmd_results"][0]["Seconds_Behind_Master"][0]["Value"]
        # if not behind_master_sec:
        #     logger.error(_("slave Seconds_Behind_Master 为空..."))
        #     raise Exception(_("获取Seconds_Behind_Master为空"))
        # return behind_master_sec
        return ""
