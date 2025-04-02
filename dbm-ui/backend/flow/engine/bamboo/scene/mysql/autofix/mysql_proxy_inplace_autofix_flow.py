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
import logging
from dataclasses import asdict
from typing import Dict, List, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import ProxyInstance
from backend.db_monitor.models import MySQLAutofixTicketStatus, MySQLAutofixTodo
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import DeployPeripheralToolsDepart
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.subflow import standardize_mysql_cluster_subflow
from backend.flow.plugins.components.collections.mysql.autofix.fix_dns import FixDnsComponent
from backend.flow.plugins.components.collections.mysql.autofix.fix_proxy_inplace_dbmeta import (
    FixProxyInplaceDBMetaComponent,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_file_with_retry import TransFileWithRetryComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaWithRetryKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload

logger = logging.getLogger("flow")


class ProxyInplaceAutofixFlow(object):
    """
    原地启动 proxy
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def autofix(self):
        """
        self.data = {
            "bk_cloud_id": int,
            "bk_biz_id": int,
            "ip": str,
            "check_id": int,
            "port_list": list[int],
            "machine_type": str,
        }
        1. 从集群另外一台 proxy 拉取 user list 文件
        2. 启动进程
        3. 修复dns
        4. 修复元数据
        """

        bk_cloud_id = self.data["bk_cloud_id"]
        bk_biz_id = self.data["bk_biz_id"]
        ip = self.data["ip"]
        check_id = self.data["check_id"]
        port_list = self.data["port_list"]
        machine_type = self.data["machine_type"]

        autofix_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

        autofix_pipeline.add_act(
            act_name=_("下发actuator"),
            act_component_code=TransFileWithRetryComponent.code,
            kwargs=asdict(
                DownloadMediaWithRetryKwargs(
                    bk_cloud_id=bk_cloud_id,
                    exec_ip=ip,
                    file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    retry_seconds=7200,
                )
            ),
        )

        # 启动 proxy, 同步权限, set backend
        # 同步权限, set backend为了安全还是都做一下
        # 因为没法保证会不会有人手动去搞事情
        autofix_pipeline.add_act(
            act_name=_("原地自愈proxy {}".format(ip)),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    bk_cloud_id=bk_cloud_id,
                    run_as_system_user=DBA_ROOT_USER,
                    exec_ip=ip,
                    cluster={
                        "ip": ip,
                        "port_list": port_list,
                    },
                    get_mysql_payload_func=MysqlActPayload.proxy_inplace_autofix.__name__,
                )
            ),
        )

        # 修复元数据
        # DBHA 实际做的只有把实例改为 unavailable, 理论上只需要做这个
        # 但是为了安全, 要多做一些, 具体要做的是
        # 1. 改实例状态
        # 2. 改集群状态
        # 3. set proxy instance bind entry
        # 4. set proxy - storage relation
        autofix_pipeline.add_act(
            act_name=_("修复{}元数据".format(self.data["ip"])),
            act_component_code=FixProxyInplaceDBMetaComponent.code,
            kwargs={
                "bk_cloud_id": bk_cloud_id,
                "ip": ip,
                "port_list": port_list,
            },
        )

        # 修复 dns
        autofix_pipeline.add_act(
            act_name=_("修复dns记录"),
            act_component_code=FixDnsComponent.code,
            kwargs={
                "bk_cloud_id": bk_cloud_id,
                "bk_biz_id": bk_biz_id,
                "ip": ip,
                "port_list": port_list,
                "machine_type": machine_type,
            },
        )

        clusters_detail: Dict[str, Dict[str, List[str]]] = {}
        for p in ProxyInstance.objects.filter(machine__ip=ip, machine__bk_cloud_id=bk_cloud_id):
            cluster_obj = p.cluster.first()
            clusters_detail[cluster_obj.immute_domain] = {"proxy": [p.ip_port]}

        autofix_pipeline.add_sub_pipeline(
            sub_flow=standardize_mysql_cluster_subflow(
                root_id=self.root_id,
                data=copy.deepcopy(self.data),
                bk_cloud_id=bk_cloud_id,
                bk_biz_id=bk_biz_id,
                cluster_type=ClusterType.TenDBHA,
                clusters_detail=clusters_detail,
                departs=[DeployPeripheralToolsDepart.MySQLMonitor],
                with_deploy_binary=False,
                with_collect_sysinfo=False,
                with_actuator=False,
                with_bk_plugin=False,
                with_cc_standardize=False,
                with_instance_standardize=False,
            )
        )

        pipeline = Builder(root_id=self.root_id, data=self.data)
        pipeline.add_sub_pipeline(sub_flow=autofix_pipeline.build_sub_process(sub_name=_("proxy原地自愈")))
        logger.info(_("构建proxy原地自愈成功"))

        if pipeline.run_pipeline():
            MySQLAutofixTodo.objects.filter(check_id=check_id).update(
                inplace_ticket_status=MySQLAutofixTicketStatus.RUNNING
            )
