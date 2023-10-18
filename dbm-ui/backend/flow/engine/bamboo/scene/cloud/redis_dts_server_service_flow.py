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
from typing import List, Union

from bamboo_engine.builder import SubProcess
from django.utils.translation import ugettext as _

from backend.flow.engine.bamboo.scene.cloud.base_service_flow import CloudBaseServiceFlow
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.utils.cloud.cloud_act_payload import CloudServiceActPayload
from backend.flow.utils.cloud.cloud_db_proxy import CloudDBProxy
from backend.flow.utils.cloud.script_template import stop_redis_dts_server_template

logger = logging.getLogger("flow")


class CloudRedisDtsServerServiceFlow(CloudBaseServiceFlow):
    """云区域部署redis dts服务流程"""

    def build_dts_server_apply_flow(self, dts_pipeline: Union[Builder, SubBuilder]) -> Union[Builder, SubBuilder]:
        sub_dts_pipeline = SubBuilder(self.root_id, data=self.data)
        sub_dts_pipeline_list: List[SubProcess] = []

        for host_info in self.data["redis_dts"]["host_infos"]:
            dts_deploy_pipeline = SubBuilder(self.root_id, data=self.data)
            dts_deploy_pipeline = self.deploy_redis_dts_server_service_pipeline(host_info, dts_deploy_pipeline)
            sub_dts_pipeline_list.append(
                dts_deploy_pipeline.build_sub_process(sub_name=_("主机{}部署redis dts服务 s").format(host_info["ip"]))
            )

        sub_dts_pipeline.add_parallel_sub_pipeline(sub_dts_pipeline_list)
        dts_pipeline.add_sub_pipeline(sub_dts_pipeline.build_sub_process(sub_name=_("部署redis dts服务")))
        return dts_pipeline

    def service_apply_flow(self):
        """
        云区域redis dts服务的部署流程执行
        """
        dts_pipeline = Builder(root_id=self.root_id, data=self.data)

        # 部署 redis dts_server
        dts_pipeline = self.build_dts_server_apply_flow(dts_pipeline)

        # 更新dbproxy信息
        dts_pipeline = self.add_dbproxy_act(
            pipeline=dts_pipeline,
            host_infos=self.data["redis_dts"]["host_infos"],
            proxy_func_name=CloudDBProxy.cloud_redis_dts_server_apply.__name__,
        )
        dts_pipeline.run_pipeline()

    def service_reload_flow(self):
        """
        云区域redis dts服务的重启/重装流程执行
        """
        # 重启/重装等同于重新部署，不影响其他组件
        dts_pipeline = Builder(root_id=self.root_id, data=self.data)
        dts_pipeline = self.build_dts_server_apply_flow(dts_pipeline)
        dts_pipeline.run_pipeline()

    def service_add_flow(self):
        """
        云区域redis dts服务的增加流程执行
        """
        dts_pipeline = Builder(root_id=self.root_id, data=self.data)

        dts_pipeline = self.build_dts_server_apply_flow(dts_pipeline)

        # 更新dbproxy信息
        dts_pipeline = self.add_dbproxy_act(
            pipeline=dts_pipeline,
            host_infos=self.data["redis_dts"]["host_infos"],
            proxy_func_name=CloudDBProxy.cloud_redis_dts_server_apply.__name__,
        )
        dts_pipeline.run_pipeline()

    def service_reduce_flow(self):
        """
        云区域redis dts服务的下架流程执行
        """
        dts_pipeline = Builder(root_id=self.root_id, data=self.data)
        reduce_dts_host_infos = self.data["redis_dts"]["host_infos"]

        # 裁撤旧redis dts服务
        dts_pipeline = self.add_reduce_act(
            pipeline=dts_pipeline,
            host_infos=reduce_dts_host_infos,
            payload_func_name=CloudServiceActPayload.get_redis_dts_server_reduce_payload.__name__,
            script_tpl=stop_redis_dts_server_template,
        )

        # 更新proxy机器
        dts_pipeline = self.add_dbproxy_act(
            pipeline=dts_pipeline,
            host_infos=reduce_dts_host_infos,
            proxy_func_name=CloudDBProxy.cloud_redis_dts_server_reduce.__name__,
        )

        dts_pipeline.run_pipeline()

    def service_replace_flow(self):
        """
        云区域redis dts服务的替换流程执行
        """

        dts_pipeline = Builder(root_id=self.root_id, data=self.data)
        new_dts_host_infos = self.data["redis_dts"]["host_infos"]
        old_dts_host_infos = self.data["old_redis_dts"]["host_infos"]

        # 部署新的redis dts流程
        deploy_dts_pipeline = SubBuilder(data=self.data, root_id=self.root_id)
        deploy_dts_pipeline = self.build_dts_server_apply_flow(deploy_dts_pipeline)
        dts_pipeline.add_sub_pipeline(deploy_dts_pipeline.build_sub_process(sub_name=_("部署新redis dts服务流程")))

        # 更新dbproxy信息
        dts_pipeline = self.add_dbproxy_act(
            pipeline=dts_pipeline,
            host_infos=new_dts_host_infos,
            proxy_func_name=CloudDBProxy.cloud_redis_dts_server_replace.__name__,
            extra_kwargs={"old_redis_dts": old_dts_host_infos},
        )

        # 裁撤旧的redis dts流程
        reduce_dts_pipeline = SubBuilder(data=self.data, root_id=self.root_id)
        reduce_dts_pipeline = self.add_reduce_act(
            pipeline=reduce_dts_pipeline,
            host_infos=old_dts_host_infos,
            payload_func_name=CloudServiceActPayload.get_redis_dts_server_reduce_payload.__name__,
            script_tpl=stop_redis_dts_server_template,
        )
        dts_pipeline.add_sub_pipeline(reduce_dts_pipeline.build_sub_process(sub_name=_("裁撤旧redis dts服务流程")))

        dts_pipeline.run_pipeline()
