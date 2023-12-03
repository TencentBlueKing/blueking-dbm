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

from backend.core.encrypt.constants import AsymmetricCipherConfigType
from backend.core.encrypt.handlers import AsymmetricHandler
from backend.db_meta.enums import InstanceRole
from backend.db_meta.enums.extra_process_type import ExtraProcessType
from backend.db_meta.models import Cluster
from backend.db_meta.models.extra_process import ExtraProcessInstance
from backend.flow.consts import TBINLOGDUMPER_KAFKA_GLOBAL_CONF, TBinlogDumperProtocolType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.tbinlogdumper.common.common_sub_flow import (
    add_tbinlogdumper_sub_flow,
    reduce_tbinlogdumper_sub_flow,
    switch_sub_flow,
)
from backend.flow.engine.bamboo.scene.tbinlogdumper.common.exceptions import NormalTBinlogDumperFlowException
from backend.flow.engine.bamboo.scene.tbinlogdumper.common.util import get_cluster
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")


class TBinlogDumperSwitchNodesFlow(object):
    """
    构建  tbinlogdumper 节点迁移部署，目的是为了保证节点在最新的master机器上部署
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

    @staticmethod
    def _get_real_switch_inst_for_cluster(cluster: Cluster, switch_instances: list) -> list:
        """
        根据传入的cluster对象以及待切换的TBinlogDumper实例列表
        @param cluster: 集群model
        @param switch_instances: 待切换TBinlogDumper实例列表
        """
        real_switch_instances = []
        master = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)

        for instance in switch_instances:
            # 判断节点是否在元信息记录
            try:
                binlogdumper = ExtraProcessInstance.objects.get(
                    ip=instance["host"],
                    bk_cloud_id=cluster.bk_cloud_id,
                    listen_port=instance["port"],
                    proc_type=ExtraProcessType.TBINLOGDUMPER,
                )
            except ExtraProcessInstance.DoesNotExist:
                logger.warning(
                    f"TBinlogDumper node [{instance['host']}:{instance['port']}] "
                    f"does not exist in cluster [{cluster.name}]"
                )
                continue

            # 判断当前每个TBinlogDumper实例是否和当前的master一致，如果一致，跳过这次的迁移
            if master.machine.ip == instance["host"]:
                logger.warning(
                    f"The current TBinlogDumper instance "
                    f"[{instance['host']}:instance{'port'}] is on master [{master.machine.ip},skip]"
                )
                continue

            tmp = {
                "dumper_id": binlogdumper.extra_config["dumper_id"],
                "area_name": binlogdumper.extra_config["area_name"],
                "port": binlogdumper.listen_port,
                "repl_binlog_file": instance["repl_binlog_file"],
                "repl_binlog_pos": instance["repl_binlog_pos"],
                "reduce_id": binlogdumper.id,
                "repl_tables": binlogdumper.extra_config["repl_tables"],
                "target_address": binlogdumper.extra_config["target_address"],
                "target_port": binlogdumper.extra_config["target_port"],
                "protocol_type": binlogdumper.extra_config["protocol_type"],
            }
            if binlogdumper.extra_config["protocol_type"] == TBinlogDumperProtocolType.KAFKA.value:
                tmp.update(
                    {
                        "kafka_user": AsymmetricHandler.decrypt(
                            name=AsymmetricCipherConfigType.PASSWORD.value,
                            content=binlogdumper.extra_config["kafka_user"],
                        ),
                        "kafka_pwd": AsymmetricHandler.decrypt(
                            name=AsymmetricCipherConfigType.PASSWORD.value,
                            content=binlogdumper.extra_config["kafka_pwd"],
                        ),
                    }
                )
            elif binlogdumper.extra_config["protocol_type"] == TBinlogDumperProtocolType.L5_AGENT.value:
                tmp.update(
                    {
                        "l5_modid": binlogdumper.extra_config["l5_modid"],
                        "l5_cmdid": binlogdumper.extra_config["l5_cmdid"],
                    }
                )
            else:
                pass

            real_switch_instances.append(tmp)

        return real_switch_instances

    def switch_nodes(self):
        """
        定义TBinlogDumper切换过程
        """
        cluster_ids = [i["cluster_id"] for i in self.data["infos"]]
        pipeline = Builder(root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=list(set(cluster_ids)))
        sub_pipelines = []
        for info in self.data["infos"]:
            # 获取对应集群相关对象
            cluster = get_cluster(cluster_id=int(info["cluster_id"]), bk_biz_id=int(self.data["bk_biz_id"]))

            # 获取真正需要迁移的实例对象
            real_switch_instances = self._get_real_switch_inst_for_cluster(cluster, info["switch_instances"])

            if len(real_switch_instances) == 0:
                logger.warning(
                    f"There is no TBinlogdumper that needs to be "
                    f"migrated and deployed in this cluster [{cluster.name}]"
                )
                continue

            # 启动子流程
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")
            # 拼接子流程的全局参数
            sub_flow_context.update(info)

            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 阶段1 安装新实例
            sub_pipeline.add_sub_pipeline(
                sub_flow=add_tbinlogdumper_sub_flow(
                    cluster=cluster,
                    root_id=self.root_id,
                    uid=self.data["uid"],
                    add_conf_list=real_switch_instances,
                    created_by=self.data["created_by"],
                )
            )

            # 阶段2 关闭旧实例的同步，同时新实例同步位点数据
            sub_pipeline.add_sub_pipeline(
                sub_flow=switch_sub_flow(
                    cluster=cluster,
                    root_id=self.root_id,
                    uid=self.data["uid"],
                    is_safe=self.data["is_safe"],
                    switch_instances=real_switch_instances,
                    created_by=self.data["created_by"],
                )
            )

            # 阶段3 卸载旧实例
            sub_pipeline.add_sub_pipeline(
                sub_flow=reduce_tbinlogdumper_sub_flow(
                    bk_biz_id=cluster.bk_biz_id,
                    bk_cloud_id=cluster.bk_cloud_id,
                    root_id=self.root_id,
                    uid=self.data["uid"],
                    reduce_ids=[i["reduce_id"] for i in real_switch_instances],
                    created_by=self.data["created_by"],
                )
            )

            # 阶段4 修改元数据
            sub_pipeline.add_act(
                act_name=_("变更实例元信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.switch_tbinlogdumper.__name__,
                        cluster={"switch_ids": [i["reduce_id"] for i in real_switch_instances]},
                    )
                ),
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("[{}]集群迁移TBinlogDumper实例".format(cluster.name)))
            )

        if not sub_pipelines:
            raise NormalTBinlogDumperFlowException(message=_("没检测到需要迁移的实例，拼装TBinlogDumper迁移部署流程失败"))

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline(is_drop_random_user=True)
