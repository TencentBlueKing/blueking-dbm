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
from typing import Dict, Optional

from bamboo_engine.builder import SubProcess
from django.utils.translation import ugettext as _

from backend.flow.consts import WriteContextOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.common.check_resolv_conf import (
    CheckResolvConfComponent,
    ExecuteShellScriptComponent,
)
from backend.flow.plugins.components.collections.common.dns_server import DNSServerSetComponent
from backend.flow.plugins.components.collections.common.get_common_payload import GetCommonActPayloadComponent
from backend.flow.utils.common_act_dataclass import DNSContext
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs

logger = logging.getLogger("flow")


def SetDnsAtomJob(root_id, ticket_data, act_kwargs: ActKwargs, param: Dict) -> Optional[SubProcess]:
    """
    配置dns子流程
    Args:
        param:{
            "force":False,
            "ip":"",
            "bk_biz_id":"",
            "bk_cloud_id":"",
            "bk_city":"",
        }
    """
    ip = param["ip"]
    set_dns_sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    set_dns_sub_pipeline.add_act(
        act_name=_("初始化配置"), act_component_code=GetCommonActPayloadComponent.code, kwargs=asdict(act_kwargs)
    )

    act_kwargs.exec_ip = ip
    act_kwargs.write_op = WriteContextOpType.APPEND.value
    act_kwargs.cluster["bk_biz_id"] = param["bk_biz_id"]
    act_kwargs.cluster[
        "shell_command"
    ] = """
               d=`cat /etc/resolv.conf | sed "/^$/d" | sed "/^#/d" |awk 1 ORS=' '`
               echo "<ctx>{\\\"data\\\":\\\"${d}\\\"}</ctx>"
            """
    set_dns_sub_pipeline.add_act(
        act_name=_("获取/etc/resolv.conf: {}").format(ip),
        act_component_code=ExecuteShellScriptComponent.code,
        kwargs=asdict(act_kwargs),
        write_payload_var="resolv_content",
    )

    #  非强制情况下，需要检查配置
    if not param["force"]:
        set_dns_sub_pipeline.add_act(
            act_name=_("检查/etc/resolv.conf: {}").format(ip),
            act_component_code=CheckResolvConfComponent.code,
            kwargs=asdict(act_kwargs),
            splice_payload_var="resolv_content",
        )

    # 执行job写入配置
    act_kwargs.cluster = {"bk_cloud_id": param["bk_cloud_id"], "bk_city": param["bk_city"]}
    set_dns_sub_pipeline.add_act(
        act_name=_("{}修改DNS配置").format(ip),
        act_component_code=DNSServerSetComponent.code,
        kwargs=asdict(act_kwargs),
    )

    # TODO 检查是否能解析是否成功

    return set_dns_sub_pipeline.build_sub_process(sub_name=_("{}配置DNS子流程").format(ip))
