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

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterEntryRole
from backend.db_meta.models import Cluster
from backend.flow.consts import DBA_ORACLE_USER, ManagerDefaultPort
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.oracle.base_flow import OracleBaseFlow
from backend.flow.engine.bamboo.scene.oracle.sub_task.master_failover_common import (
    build_fetch_and_dispatch_tnsnames_sub_flow,
)
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.oracle.exec_actuator_script import (
    ExecuteOracleActuatorScriptComponent,
)
from backend.flow.plugins.components.collections.oracle.oracle_db_meta import OracleDBMetaComponent
from backend.flow.plugins.components.collections.oracle.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import UpdateDnsRecordKwargs
from backend.flow.utils.oracle.oracle_act_dataclass import DownloadMediaKwargs
from backend.flow.utils.oracle.oracle_act_payload import OracleActPayload
from backend.flow.utils.oracle.oracle_context_dataclass import (
    MasterFailoverContext,
    MetaReplaceKwargs,
    OracleActKwargs,
)
from backend.flow.utils.oracle.oracle_db_meta import OracleDBMeta

logger = logging.getLogger("flow")


class OracleMasterFailoverFlow(OracleBaseFlow):
    """
    Oracle主库故障切换单据的流程引擎

    {
        "uid": "2022111212001000",
        "root_id": 123,
        "created_by": "admin",
        "bk_biz_id": 9991001,
        "ticket_type": "ORACLE_MASTER_FAILOVER",
        "infos": [
            {
                "cluster_id": 2,
                "master": {"ip": "1.1.1.1", "bk_cloud_id": 0},
                "slave": {"ip": "1.1.1.2", "bk_cloud_id": 0},
                "is_check_process": False,
            }
        ],
    }
    """

    def oracle_master_failover_flow(self):
        """
        oracle 主库故障切换流程
        """
        oracle_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        for info in self.data["infos"]:
            sub_data = copy.deepcopy(self.data)
            sub_data.pop("infos")
            sub_flow_data = {**info, **sub_data}
            sub_pipeline = SubBuilder(root_id=self.root_id, data=sub_flow_data)

            cluster = Cluster.objects.get(id=info["cluster_id"])
            bk_cloud_id = cluster.bk_cloud_id
            master = info["master"]["ip"]
            slave = info["slave"]["ip"]

            sub_pipeline.add_act(
                act_name=_("下发actuator"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=[master, slave],
                        file_list=GetFileList(db_type=DBType.Oracle).get_db_actuator_package(),
                    )
                ),
            )

            if self.data["is_check_process"]:
                sub_pipeline.add_act(
                    act_name=_("检查故障主库连接"),
                    act_component_code=ExecuteOracleActuatorScriptComponent.code,
                    kwargs=asdict(
                        OracleActKwargs(
                            exec_ip=master,
                            bk_cloud_id=bk_cloud_id,
                            run_as_system_user=DBA_ORACLE_USER,
                            get_oracle_payload_func=OracleActPayload.get_check_connections_payload.__name__,
                        )
                    ),
                )

            sub_pipeline.add_act(
                act_name=_("检查同步状态"),
                act_component_code=ExecuteOracleActuatorScriptComponent.code,
                kwargs=asdict(
                    OracleActKwargs(
                        exec_ip=slave,
                        bk_cloud_id=bk_cloud_id,
                        run_as_system_user=DBA_ORACLE_USER,
                        get_oracle_payload_func=OracleActPayload.get_check_sync_status_payload.__name__,
                    )
                ),
            )

            sub_pipeline.add_act(
                act_name=_("关闭故障主库实例与监听"),
                act_component_code=ExecuteOracleActuatorScriptComponent.code,
                kwargs=asdict(
                    OracleActKwargs(
                        exec_ip=master,
                        bk_cloud_id=bk_cloud_id,
                        run_as_system_user=DBA_ORACLE_USER,
                        get_oracle_payload_func=OracleActPayload.get_shutdown_force_payload.__name__,
                    )
                ),
            )

            sub_pipeline.add_act(
                act_name=_("关闭备库监听"),
                act_component_code=ExecuteOracleActuatorScriptComponent.code,
                kwargs=asdict(
                    OracleActKwargs(
                        exec_ip=slave,
                        bk_cloud_id=bk_cloud_id,
                        run_as_system_user=DBA_ORACLE_USER,
                        get_oracle_payload_func=OracleActPayload.get_stop_listener_payload.__name__,
                    )
                ),
            )

            sub_pipeline.add_act(
                act_name=_("激活备库"),
                act_component_code=ExecuteOracleActuatorScriptComponent.code,
                kwargs=asdict(
                    OracleActKwargs(
                        exec_ip=slave,
                        bk_cloud_id=bk_cloud_id,
                        run_as_system_user=DBA_ORACLE_USER,
                        get_oracle_payload_func=OracleActPayload.get_activate_standby_payload.__name__,
                    )
                ),
            )

            # 获取并下发 tnsnames 文件(获取 -> 上传 -> 下发 -> 修改)
            sub_pipeline.add_sub_pipeline(
                sub_flow=build_fetch_and_dispatch_tnsnames_sub_flow(
                    root_id=self.root_id,
                    data=sub_flow_data,
                    bk_cloud_id=bk_cloud_id,
                    master=master,
                    slave=slave,
                    uid=self.data["uid"],
                )
            )

            sub_pipeline.add_act(
                act_name=_("启动新主库监听"),
                act_component_code=ExecuteOracleActuatorScriptComponent.code,
                kwargs=asdict(
                    OracleActKwargs(
                        exec_ip=slave,
                        bk_cloud_id=bk_cloud_id,
                        run_as_system_user=DBA_ORACLE_USER,
                        get_oracle_payload_func=OracleActPayload.get_start_listener_payload.__name__,
                    )
                ),
            )

            sub_pipeline.add_act(
                act_name=_("写入元数据-主备切换"),
                act_component_code=OracleDBMetaComponent.code,
                kwargs=asdict(
                    MetaReplaceKwargs(
                        meta_func_name=OracleDBMeta.swap_primary_standby.__name__,
                        bk_biz_id=int(self.data["bk_biz_id"]),
                        cluster_id=info["cluster_id"],
                        failover=True,
                    )
                ),
            )

            dns = cluster.clusterentry_set.get(role=ClusterEntryRole.MASTER_ENTRY.value).entry
            sub_pipeline.add_act(
                act_name=_("[{}]替换域名映射".format(dns)),
                act_component_code=MySQLDnsManageComponent.code,
                kwargs=asdict(
                    UpdateDnsRecordKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        old_instance=_("{}#{}".format(master, ManagerDefaultPort.ORACLE_PORT.value)),
                        new_instance=_("{}#{}".format(slave, ManagerDefaultPort.ORACLE_PORT.value)),
                        update_domain_name=dns,
                    ),
                ),
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("集群[{}]主库故障切换").format(cluster.immute_domain))
            )

        oracle_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        logger.info(_("构建Oracle主库故障切换流程成功"))
        oracle_pipeline.run_pipeline(init_trans_data_class=MasterFailoverContext())
