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
import logging
from typing import List, Union

from bamboo_engine.builder import SubProcess
from django.utils.translation import ugettext as _

from backend.db_proxy.constants import ExtensionType
from backend.db_proxy.models import DBExtension
from backend.flow.consts import CloudServiceName
from backend.flow.engine.bamboo.scene.cloud.base_service_flow import CloudBaseServiceFlow
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.utils.cloud.cloud_act_payload import CloudServiceActPayload
from backend.flow.utils.cloud.cloud_context_dataclass import CloudDRSKwargs
from backend.flow.utils.cloud.cloud_db_proxy import CloudDBProxy
from backend.flow.utils.cloud.script_template import stop_drs_service_template

logger = logging.getLogger("flow")


class CloudDRSServiceFlow(CloudBaseServiceFlow):
    """云区域部署DRS服务流程"""

    def build_drs_apply_flow(self, drs_pipeline: Union[Builder, SubBuilder], act_name: str = _("部署")):
        drs_kwargs = CloudDRSKwargs(**self._get_or_generate_usr_pwd(service=CloudServiceName.DRS))
        sub_drs_pipeline = SubBuilder(self.root_id, data=self.data)
        sub_drs_pipeline_list: List[SubProcess] = []

        for host_info in self.data["drs"]["host_infos"]:
            drs_deploy_pipeline = SubBuilder(self.root_id, data=self.data)
            drs_deploy_pipeline = self.deploy_drs_service_pipeline(drs_kwargs, host_info, drs_deploy_pipeline)
            sub_drs_pipeline_list.append(
                drs_deploy_pipeline.build_sub_process(sub_name=_("主机{}部署drs服务").format(host_info["ip"]))
            )

        sub_drs_pipeline.add_parallel_sub_pipeline(sub_drs_pipeline_list)
        drs_pipeline.add_sub_pipeline(sub_drs_pipeline.build_sub_process(sub_name=_("{}drs服务").format(act_name)))

        return drs_pipeline, drs_kwargs

    def service_apply_flow(self):
        """
        云区域DRS服务的部署流程执行
        """
        drs_pipeline = Builder(root_id=self.root_id, data=self.data)

        # 部署drs服务
        drs_pipeline, drs_kwargs = self.build_drs_apply_flow(drs_pipeline)

        # 写入dbproxy信息
        drs_apply_host_infos = self.data["drs"]["host_infos"]
        drs_pipeline = self.add_dbproxy_act(
            pipeline=drs_pipeline,
            proxy_func_name=CloudDBProxy.cloud_drs_apply.__name__,
            host_infos=drs_apply_host_infos,
            host_kwargs={"user": drs_kwargs.user, "pwd": drs_kwargs.pwd},
            extra_kwargs=None,
        )

        drs_pipeline.run_pipeline()

    def service_reload_flow(self):
        # drs的重启/重装 等于获取原来部署参数重新部署一遍
        drs_pipeline = Builder(root_id=self.root_id, data=self.data)
        drs_pipeline, __ = self.build_drs_apply_flow(drs_pipeline, act_name=_("重装"))
        drs_pipeline.run_pipeline()

    def service_add_flow(self):
        drs_pipeline = Builder(root_id=self.root_id, data=self.data)
        drs_add_host_infos = self.data["drs"]["host_infos"]

        # 部署新的drs服务
        drs_pipeline, drs_kwargs = self.build_drs_apply_flow(drs_pipeline, act_name=_("安装"))

        # 权限刷新
        drs_pipeline = self.add_privilege_act(
            pipeline=drs_pipeline, host_infos=drs_add_host_infos, user=drs_kwargs.user, pwd=drs_kwargs.pwd
        )

        # 更新dbproxy信息
        drs_pipeline = self.add_dbproxy_act(
            pipeline=drs_pipeline, proxy_func_name=CloudDBProxy.cloud_drs_apply.__name__, host_infos=drs_add_host_infos
        )

        # 重启nginx, 注意这里需要把原来的drs加入更新
        now_drs = DBExtension.get_extension_in_cloud(
            bk_cloud_id=self.data["bk_cloud_id"], extension_type=ExtensionType.DRS
        )
        drs_now_host_infos = [drs.details for drs in now_drs]
        self.data["drs"]["host_infos"].extend(drs_now_host_infos)
        drs_pipeline = self.add_nginx_reload_sub_pipeline(drs_pipeline)

        drs_pipeline.run_pipeline()

    def service_reduce_flow(self):
        drs_pipeline = Builder(root_id=self.root_id, data=self.data)
        drs_reduce_host_infos = self.data["drs"]["host_infos"]

        # 裁撤旧drs服务
        drs_pipeline = self.add_reduce_act(
            pipeline=drs_pipeline,
            host_infos=drs_reduce_host_infos,
            payload_func_name=CloudServiceActPayload.get_drs_reduce_payload.__name__,
            script_tpl=stop_drs_service_template,
        )

        # 权限刷新
        drs_kwargs = CloudDRSKwargs(**self._get_or_generate_usr_pwd(service=CloudServiceName.DRS))
        drs_pipeline = self.add_privilege_act(
            pipeline=drs_pipeline, host_infos=drs_reduce_host_infos, user=drs_kwargs.user, pwd=drs_kwargs.pwd
        )

        # 更新dbproxy信息
        drs_pipeline = self.add_dbproxy_act(
            pipeline=drs_pipeline,
            proxy_func_name=CloudDBProxy.cloud_drs_reduce.__name__,
            host_infos=drs_reduce_host_infos,
        )

        # 重启nginx, 注意这里需要把删除的drs从原来信息中剔除
        delete_drs_ids = [host["id"] for host in self.data["drs"]["host_infos"]]
        now_drs_host_infos = list(
            DBExtension.get_extension_in_cloud(bk_cloud_id=self.data["bk_cloud_id"], extension_type=ExtensionType.DRS)
            .exclude(id__in=delete_drs_ids)
            .values_list("details", flat=True)
        )
        self.data["drs"]["host_infos"] = now_drs_host_infos
        drs_pipeline = self.add_nginx_reload_sub_pipeline(drs_pipeline)

        drs_pipeline.run_pipeline()

    def service_replace_flow(self):
        drs_pipeline = Builder(root_id=self.root_id, data=self.data)
        old_drs_host_infos = self.data["old_drs"]["host_infos"]
        new_drs_host_infos = self.data["drs"]["host_infos"]

        # 部署drs服务
        deploy_drs_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
        deploy_drs_pipeline, drs_kwargs = self.build_drs_apply_flow(deploy_drs_pipeline)
        deploy_drs_pipeline = self.add_privilege_act(
            pipeline=deploy_drs_pipeline, host_infos=new_drs_host_infos, user=drs_kwargs.user, pwd=drs_kwargs.pwd
        )
        drs_pipeline.add_sub_pipeline(deploy_drs_pipeline.build_sub_process(sub_name=_("部署新drs服务")))

        # 重启nginx
        delete_drs_id = old_drs_host_infos[0]["id"]
        now_drs_host_infos = list(
            DBExtension.get_extension_in_cloud(bk_cloud_id=self.data["bk_cloud_id"], extension_type=ExtensionType.DRS)
            .exclude(id=delete_drs_id)
            .values_list("details", flat=True)
        )
        merge_drs_host_infos = [*now_drs_host_infos, *new_drs_host_infos]
        self.data["drs"]["host_infos"] = merge_drs_host_infos

        drs_pipeline = self.add_nginx_reload_sub_pipeline(drs_pipeline)

        # 更新dbproxy信息, 这里加入新的drs机器，并剔除旧的drs机器
        drs_pipeline = self.add_dbproxy_act(
            pipeline=drs_pipeline,
            proxy_func_name=CloudDBProxy.cloud_drs_replace.__name__,
            host_infos=new_drs_host_infos,
            host_kwargs={"user": drs_kwargs.user, "pwd": drs_kwargs.pwd},
            extra_kwargs={"old_drs": old_drs_host_infos},
        )

        # 裁撤旧drs服务
        reduce_drs_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
        reduce_drs_pipeline = self.add_reduce_act(
            pipeline=reduce_drs_pipeline,
            host_infos=old_drs_host_infos,
            payload_func_name=CloudServiceActPayload.get_drs_reduce_payload.__name__,
            script_tpl=stop_drs_service_template,
        )
        reduce_drs_pipeline = self.add_privilege_act(
            pipeline=reduce_drs_pipeline, host_infos=old_drs_host_infos, user=drs_kwargs.user, pwd=drs_kwargs.pwd
        )
        drs_pipeline.add_sub_pipeline(reduce_drs_pipeline.build_sub_process(sub_name=_("裁撤旧drs服务")))

        drs_pipeline.run_pipeline()
