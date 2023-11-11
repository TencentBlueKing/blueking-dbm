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
from dataclasses import asdict
from typing import Dict, List, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta import api
from backend.db_meta.models import Machine
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import RedisDbmonAtomJob
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext

logger = logging.getLogger("flow")


class RedisDbmonSceneFlow(object):
    """
    ## Redis cluster Master 裁撤/迁移替换, 成对替换
    {
      "bk_biz_id":"", # 必须有
      "bk_cloud_id":11, # 必须有
      "hosts":[1.1.a.1,2.2.2.b], # 可选， 不传就是app 下所有redis机器
      "ticket_type": "REDIS_INSTALL_DBMON"
    }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_cluster_info(bk_biz_id: int, hosts: List) -> dict:
        """获取集群现有信息"""
        if len(hosts) == 0:
            hosts = [machine_obj.ip for machine_obj in Machine.objects.filter(bk_biz_id=bk_biz_id)]
        return api.meta.query_cluster_by_hosts(hosts)

    def __init_builder(self, operate_name: str):
        flow_data = self.data

        redis_pipeline = Builder(root_id=self.root_id, data=flow_data)
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = True
        act_kwargs.cluster = {
            "operate": operate_name,
        }
        act_kwargs.bk_biz_id = self.data["bk_biz_id"]
        act_kwargs.bk_cloud_id = self.data["bk_cloud_id"]
        logger.info("+===+++++===+++++===++++current tick_data info :: {}".format(act_kwargs))

        redis_pipeline.add_act(
            act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )
        return redis_pipeline, act_kwargs

    def batch_update_dbmon(self):
        """### 适用于 集群中Master 机房裁撤/迁移替换场景 (成对替换)

        步骤：   获取机器实例列表--> 按照机器重装dbmon
        """
        hosts_cluster_info = self.__get_cluster_info(self.data["bk_biz_id"], self.data["hosts"])
        logger.info("+===+++++===+++++===++++current hosts info :: {}".format(hosts_cluster_info))
        redis_pipeline, act_kwargs = self.__init_builder(_("REDIS-重装DBMON"))
        # ### 部署DBMON #############################################################################
        sub_pipelines = []
        for one_host in hosts_cluster_info:
            params = {
                "ip": one_host["ip"],
                "ports": one_host["ports"],
                "meta_role": one_host["instance_role"],
                "cluster_type": one_host["cluster_type"],
                "immute_domain": one_host["cluster"],
                "cluster_name": one_host["cluster_name"],
            }
            sub_builder = RedisDbmonAtomJob(self.root_id, self.data, act_kwargs, params)
            sub_pipelines.append(sub_builder)
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        # ### 部署DBMON ########################################################################## 完毕 ###

        redis_pipeline.run_pipeline()
