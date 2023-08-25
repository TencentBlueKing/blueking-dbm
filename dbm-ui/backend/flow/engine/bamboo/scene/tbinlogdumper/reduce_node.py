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
import logging.config
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.models.extra_process import ExtraProcessInstance
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.tbinlogdumper.common.exceptions import TBinlogDumperFlowBaseException
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs, DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.flow.utils.tbinlogdumper.context_dataclass import TBinlogDumperAddContext

logger = logging.getLogger("flow")


class TBinlogDumperReduceNodesFlow(object):
    """
    构建  tbinlogdumper节点删除
    目前仅支持 tendb-ha 架构
    支持不同云区域的合并操作
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    def reduce_nodes(self):

        pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        for instance_id in self.data["reduce_ids"]:

            # 获取对应集群相关对象
            try:
                tbinlogdumper = ExtraProcessInstance.objects.get(id=instance_id)
            except ExtraProcessInstance.DoesNotExist:
                raise TBinlogDumperFlowBaseException(message=_("TBinlogDumper进程不存在[{}]".format(instance_id)))

            # 启动子流程
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("reduce_ids")
            # 拼接子流程的全局参数
            sub_flow_context.update({"id_list": [instance_id]})
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 阶段1 下发db-actuator介质包
            sub_pipeline.add_act(
                act_name=_("下发db-actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=tbinlogdumper.machine.bk_cloud_id,
                        exec_ip=tbinlogdumper.machine.ip,
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            # 阶段2 卸载实例
            sub_pipeline.add_act(
                act_name=_("卸载TBinlogDumper实例"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        bk_cloud_id=tbinlogdumper.machine.bk_cloud_id,
                        exec_ip=tbinlogdumper.machine.ip,
                        get_mysql_payload_func=MysqlActPayload.uninstall_tbinlogdumper_payload.__name__,
                        cluster={"listen_ports": [instance_id]},
                    )
                ),
            )

            # 删除元数据
            sub_pipeline.add_act(
                act_name=_("删除实例元信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.reduce_tbinlogdumper.__name__,
                    )
                ),
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(
                    sub_name=_(
                        "[{}:{}]集群添加TBinlogDumper实例".format(tbinlogdumper.machine.ip, tbinlogdumper.listen_port)
                    )
                )
            )

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline(init_trans_data_class=TBinlogDumperAddContext())
