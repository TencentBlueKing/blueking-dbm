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
import logging.config
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.crypto import get_random_string
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.models import Cluster
from backend.flow.consts import ACCOUNT_PREFIX
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.pt_table_sync import PtTableSyncComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, PtTableSyncKwargs

logger = logging.getLogger("flow")


class PtTableSyncFlow(object):
    """
    构建pt-table-sync执行流程抽象类
    这里可以兼容两类触发修复单据的场景：1：例行校验触发逻辑 2：单据校验触发逻辑
    支持多云区域合并操作
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_sync_account():
        """
        定义获取数据修复时临时账号和密码的方法
        """
        sync_pwd = get_random_string(length=16)
        sync_account = f"{ACCOUNT_PREFIX}{get_random_string(length=10)}"
        return sync_account, sync_pwd

    def exec_pt_table_sync_flow(self):
        """
        定义执行pt-table-sync 流程
        增加单据临时ADMIN账号的添加和删除逻辑
        """
        cluster_ids = [i["cluster_id"] for i in self.data["infos"]]
        table_sync_pipeline = Builder(
            root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=list(set(cluster_ids))
        )

        sync_account, sync_pwd = self.__get_sync_account()
        sub_pipelines = []

        # 这里优化场景，计算不一致的存储对的slave-ip，然后去重，避免阻塞异常
        target_ips = {}
        for info in self.data["infos"]:
            cluster = Cluster.objects.get(id=info["cluster_id"])
            for slave in info["slaves"]:
                if not slave["is_consistent"]:
                    if cluster.bk_cloud_id not in target_ips:
                        target_ips[cluster.bk_cloud_id] = []
                    target_ips[cluster.bk_cloud_id].append(slave["ip"])

        acts_list = []
        for k, v in target_ips.items():
            acts_list.append(
                {
                    "act_name": _("下发db-actuator介质"),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=k,
                            exec_ip=v,
                            file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                        )
                    ),
                }
            )
        if not acts_list:
            raise Exception(_("修复单据找不到可修复的存储对"))

        table_sync_pipeline.add_parallel_acts(acts_list=acts_list)

        for info in self.data["infos"]:
            # 拼接子流程需要全局参数
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")
            cluster = Cluster.objects.get(id=info["cluster_id"])

            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            cluster_sync_sub_list = []
            for slave in info["slaves"]:
                # 遍历每个集群的slave信息，拼接需要修复的子流程
                if slave["is_consistent"]:
                    # slave节点数据一致，则不需要生成修复流程
                    continue

                slave_sync_global_data = copy.deepcopy(sub_flow_context)
                slave_sync_global_data["slave_ip"] = slave["ip"]
                slave_sync_global_data["slave_port"] = slave["port"]
                slave_sync_global_data["master_ip"] = info["master"]["ip"]
                slave_sync_global_data["master_port"] = info["master"]["port"]

                slave_sync_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(slave_sync_global_data))

                slave_sync_sub_pipeline.add_act(
                    act_name=_("执行数据修复"),
                    act_component_code=PtTableSyncComponent.code,
                    kwargs=asdict(
                        PtTableSyncKwargs(
                            bk_cloud_id=cluster.bk_cloud_id,
                            sync_user=sync_account,
                            sync_pass=sync_pwd,
                            check_sum_table=self.data["checksum_table"],
                        )
                    ),
                )
                cluster_sync_sub_list.append(
                    slave_sync_sub_pipeline.build_sub_process(
                        sub_name=_("{}:{}做数据修复").format(slave["ip"], slave["port"])
                    )
                )

            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_sync_sub_list)
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("{}数据修复").format(cluster.name)))

        if not sub_pipelines:
            raise Exception(_("修复单据找不到可修复的集群"))

        table_sync_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        table_sync_pipeline.run_pipeline(is_drop_random_user=True)
