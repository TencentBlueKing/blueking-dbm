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

from backend.db_meta.enums import InstanceRole
from backend.flow.consts import TBinlogDumperAddType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.tbinlogdumper.common.common_sub_flow import (
    add_tbinlogdumper_sub_flow,
    full_sync_sub_flow,
    incr_sync_sub_flow,
)
from backend.flow.engine.bamboo.scene.tbinlogdumper.common.exceptions import NormalTBinlogDumperFlowException
from backend.flow.engine.bamboo.scene.tbinlogdumper.common.util import get_cluster, get_tbinlogdumper_install_port
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.flow.utils.tbinlogdumper.context_dataclass import TBinlogDumperAddContext

logger = logging.getLogger("flow")


class TBinlogDumperAddNodesFlow(object):
    """
    构建  tbinlogdumper节点添加；目前尽量在tendb-ha的master进行部署，作为附属进程，可追加部署，多实例部署
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

    def add_nodes(self):
        pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        for info in self.data["infos"]:

            # 获取对应集群相关对象
            cluster = get_cluster(cluster_id=int(info["cluster_id"]), bk_biz_id=int(self.data["bk_biz_id"]))

            # 获取最新的master实例
            master = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)

            # 获取安装端口
            install_ports = get_tbinlogdumper_install_port(machine=master.machine, install_num=len(info["add_confs"]))
            # 将端口分配到每个add_conf
            for key, conf in enumerate(info["add_confs"]):
                conf["port"] = install_ports[key]

            # 启动子流程
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")
            # 拼接子流程的全局参数
            sub_flow_context.update(info)

            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            sub_pipeline.add_sub_pipeline(
                sub_flow=add_tbinlogdumper_sub_flow(
                    cluster=cluster,
                    root_id=self.root_id,
                    uid=self.data["uid"],
                    add_conf_list=info["add_confs"],
                    created_by=self.data["created_by"],
                )
            )

            for add_conf in info["add_confs"]:
                # 根据不同的添加类型，来确定TBinlogDumper数据同步的行为
                if add_conf["add_type"] == TBinlogDumperAddType.INCR_SYNC.value:
                    sub_pipeline.add_sub_pipeline(
                        sub_flow=incr_sync_sub_flow(
                            cluster=cluster,
                            root_id=self.root_id,
                            uid=self.data["uid"],
                            add_tbinlogdumper_conf=add_conf,
                            created_by=self.data["created_by"],
                        )
                    )
                elif add_conf["add_type"] == TBinlogDumperAddType.FULL_SYNC.value:
                    sub_pipeline.add_sub_pipeline(
                        sub_flow=full_sync_sub_flow(
                            cluster=cluster,
                            root_id=self.root_id,
                            uid=self.data["uid"],
                            add_tbinlogdumper_conf=add_conf,
                            created_by=self.data["created_by"],
                        )
                    )
                else:
                    raise NormalTBinlogDumperFlowException(
                        message=_("非法上架特性，请联系系统管理员：add_type:{}".format(add_conf["add_type"]))
                    )

            # 写元数据
            sub_pipeline.add_act(
                act_name=_("写入实例元信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.add_tbinlogdumper.__name__,
                    )
                ),
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("[{}]集群添加TBinlogDumper实例".format(cluster.name)))
            )

        if not sub_pipelines:
            raise NormalTBinlogDumperFlowException(message=_("计算不到需要上架的实例，拼装TBinlogDumper上架流程失败"))

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline(init_trans_data_class=TBinlogDumperAddContext())
