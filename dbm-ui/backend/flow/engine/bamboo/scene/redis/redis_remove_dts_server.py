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

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_dts_server_meta import RedisDtsServerMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext

logger = logging.getLogger("flow")


class RedisRemoveDtsServerFlow(object):
    """
    Redis 删除 DTS Server
    """

    def __init__(self, root_id, data):
        self.root_id = root_id
        self.data = data

    def redis_remove_dts_server_flow(self):
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        sub_pipelines = []
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_remove_dts_server()
        act_kwargs.is_update_trans_data = True

        for info in self.data["infos"]:
            """
            info: {"ip": "3.3.3.1", "bk_cloud_id": 0}
            """
            logger.info("redis_remove_dts_server_flow info:{}".format(info))
            cluster = {**info}
            act_kwargs.cluster = cluster
            act_kwargs.exec_ip = info["ip"]

            sub_pipeline.add_act(
                act_name=_("DTS_Server-{}-下发介质").format(info["ip"]),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(act_kwargs),
            )

            sub_pipeline.add_act(
                act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
            )

            sub_pipeline.add_act(
                act_name=_("下发介质包"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
            )

            act_kwargs.get_redis_payload_func = RedisActPayload.get_remove_dts_server_payload.__name__
            sub_pipeline.add_act(
                act_name=_("DTS_Server-{}-删除").format(info["ip"]),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            sub_pipeline.add_act(
                act_name=_("DTS_Server-{}-清理dbmeta").format(info["ip"]),
                act_component_code=RedisDtsServerMetaComponent.code,
                kwargs=asdict(act_kwargs),
            )

        sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("REMOVE DTS_SERVER")))
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()
