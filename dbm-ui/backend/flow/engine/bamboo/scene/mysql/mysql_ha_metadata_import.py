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
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder, SubProcess
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_ha_import_metadata import MySQLHAImportMetadataComponent
from backend.flow.plugins.components.collections.mysql.mysql_ha_modify_cluster_phase import (
    MySQLHAModifyClusterPhaseComponent,
)
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import MySQLHAImportMetadataContext

logger = logging.getLogger("flow")


class TenDBHAMetadataImportFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def import_meta(self):
        """
        很多检查都前置了, 能走到这里可以认为基本没啥问题
        尝试无脑导入
        """
        import_pipe = Builder(root_id=self.root_id, data=self.data)

        import_pipe_sub = SubBuilder(root_id=self.root_id, data=self.data)

        import_pipe_sub.add_act(
            act_name=_("写入元数据"),
            act_component_code=MySQLHAImportMetadataComponent.code,
            kwargs={**copy.deepcopy(self.data)},
        )

        proxy_machines = []
        storage_machines = []
        for cluster_json in self.data["json_content"]:
            proxy_machines += [ele["ip"] for ele in cluster_json["proxies"]]
            storage_machines.append(cluster_json["master"]["ip"])
            storage_machines += [ele["ip"] for ele in cluster_json["slaves"]]

        proxy_machines = list(set(proxy_machines))
        storage_machines = list(set(storage_machines))

        # 不做这个, 导入后有独立单据做
        # import_pipe.add_parallel_sub_pipeline(
        #     sub_flow_list=[
        #         self._build_install_dbatool_sub(ips=proxy_machines, is_proxy=True),
        #         self._build_install_dbatool_sub(ips=storage_machines, is_proxy=False),
        #     ]
        # )

        # 没法测试
        # import_pipe_sub.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})

        import_pipe_sub.add_act(
            act_name=_("修改集群状态"), act_component_code=MySQLHAModifyClusterPhaseComponent.code, kwargs={}
        )

        import_pipe.add_sub_pipeline(sub_flow=import_pipe_sub.build_sub_process(sub_name=_("TenDBHA 元数据导入")))

        logger.info(_("构建TenDBHA元数据导入流程成功"))
        import_pipe.run_pipeline(init_trans_data_class=MySQLHAImportMetadataContext())

    # def _build_install_dbatool_sub(self, ips: List[str], is_proxy: bool) -> SubProcess:
    #     bk_cloud_id = 0
    #     cluster_type = ClusterType.TenDBHA.value
    #
    #     pipes = []
    #
    #     for ip in ips:
    #         pipe = SubBuilder(root_id=self.root_id, data=self.data)
    #
    #         pipe.add_act(
    #             act_name=_("下发MySQL周边程序介质"),
    #             act_component_code=TransFileComponent.code,
    #             kwargs=asdict(
    #                 DownloadMediaKwargs(
    #                     bk_cloud_id=bk_cloud_id,
    #                     exec_ip=ip,
    #                     file_list=GetFileList(db_type=DBType.MySQL).get_mysql_surrounding_apps_package(),
    #                 )
    #             ),
    #         )
    #         pipe.add_act(
    #             act_name=_("下发actuator介质"),
    #             act_component_code=TransFileComponent.code,
    #             kwargs=asdict(
    #                 DownloadMediaKwargs(
    #                     bk_cloud_id=bk_cloud_id,
    #                     exec_ip=ip,
    #                     file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
    #                 )
    #             ),
    #         )
    #         pipe.add_act(
    #             act_name=_("部署mysql-crond"),
    #             act_component_code=ExecuteDBActuatorScriptComponent.code,
    #             kwargs=asdict(
    #                 ExecActuatorKwargs(
    #                     exec_ip=ip,
    #                     bk_cloud_id=bk_cloud_id,
    #                     get_mysql_payload_func=MysqlActPayload.get_deploy_mysql_crond_payload.__name__,
    #                     cluster_type=cluster_type,
    #                 )
    #             ),
    #         )
    #         pipe.add_act(
    #             act_name=_("部署监控程序"),
    #             act_component_code=ExecuteDBActuatorScriptComponent.code,
    #             kwargs=asdict(
    #                 ExecActuatorKwargs(
    #                     exec_ip=ip,
    #                     bk_cloud_id=bk_cloud_id,
    #                     get_mysql_payload_func=MysqlActPayload.get_deploy_mysql_monitor_payload.__name__,
    #                     cluster_type=cluster_type,
    #                 )
    #             ),
    #         )
    #
    #         if not is_proxy:
    #             pipe.add_act(
    #                 act_name=_("部署备份程序"),
    #                 act_component_code=ExecuteDBActuatorScriptComponent.code,
    #                 kwargs=asdict(
    #                     ExecActuatorKwargs(
    #                         exec_ip=ip,
    #                         bk_cloud_id=bk_cloud_id,
    #                         get_mysql_payload_func=MysqlActPayload.get_install_db_backup_payload.__name__,
    #                         cluster_type=cluster_type,
    #                     )
    #                 ),
    #             )
    #
    #             pipe.add_act(
    #                 act_name=_("部署rotate binlog"),
    #                 act_component_code=ExecuteDBActuatorScriptComponent.code,
    #                 kwargs=asdict(
    #                     ExecActuatorKwargs(
    #                         exec_ip=ip,
    #                         bk_cloud_id=bk_cloud_id,
    #                         get_mysql_payload_func=MysqlActPayload.get_install_mysql_rotatebinlog_payload.__name__,
    #                         cluster_type=cluster_type,
    #                     )
    #                 ),
    #             )
    #
    #             pipe.add_act(
    #                 act_name=_("部署数据校验程序"),
    #                 act_component_code=ExecuteDBActuatorScriptComponent.code,
    #                 kwargs=asdict(
    #                     ExecActuatorKwargs(
    #                         exec_ip=ip,
    #                         bk_cloud_id=bk_cloud_id,
    #                         get_mysql_payload_func=MysqlActPayload.get_install_mysql_checksum_payload.__name__,
    #                         cluster_type=cluster_type,
    #                     )
    #                 ),
    #             )
    #
    #         pipes.append(pipe.build_sub_process(sub_name=_("{} 部署dba工具".format(ip))))
    #
    #     p = SubBuilder(root_id=self.root_id, data=self.data)
    #     p.add_parallel_sub_pipeline(sub_flow_list=pipes)
    #     return p.build_sub_process(sub_name=_("部署 dba 工具"))


# @transaction.atomic
# def clear_trans_stage(cluster_ids: List[int]):
#     StorageInstanceTuple.objects.filter(
#         Q(ejector__cluster__in=cluster_ids)
#         & Q(ejector__phase=InstancePhase.TRANS_STAGE.value)
#         & Q(ejector__cluster__phase=ClusterPhase.TRANS_STAGE)
#     ).delete()
#
#     # 这样其实不对, 因为延迟执行, 等到删除 machine 的时候已经找不到了
#     machines = Machine.objects.filter(
#         Q(
#             Q(proxyinstance__cluster__in=cluster_ids)
#             & Q(proxyinstance__cluster__phase=ClusterPhase.TRANS_STAGE.value)
#             & Q(proxyinstance__phase=InstancePhase.TRANS_STAGE.value)
#         )
#         | Q(
#             Q(storageinstance__cluster__in=cluster_ids)
#             & Q(storageinstance__cluster__phase=ClusterPhase.TRANS_STAGE.value)
#             & Q(storageinstance__phase=InstancePhase.TRANS_STAGE.value)
#         )
#     )
#
#
#     StorageInstance.objects.filter(
#         Q(cluster__in=cluster_ids)
#         & Q(cluster__phase=ClusterPhase.TRANS_STAGE.value)
#         & Q(phase=InstancePhase.TRANS_STAGE.value)
#     ).delete()
#
#     ProxyInstance.objects.filter(
#         Q(cluster__in=cluster_ids)
#         & Q(cluster__phase=ClusterPhase.TRANS_STAGE.value)
#         & Q(phase=InstancePhase.TRANS_STAGE.value)
#     ).delete()
#
#     print(machines)
#     machines.delete()
#     # try:
#     #     machines.delete()
#     # except ProtectedError:
#     #     pass
#
#     ClusterEntry.objects.filter(
#     Q(cluster__in=cluster_ids) & Q(cluster__phase=ClusterPhase.TRANS_STAGE.value)).delete()
#     Cluster.objects.filter(Q(id__in=cluster_ids) & Q(phase=ClusterPhase.TRANS_STAGE.value)).delete()
