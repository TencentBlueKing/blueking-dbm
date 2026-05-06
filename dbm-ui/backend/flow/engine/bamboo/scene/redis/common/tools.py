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
from copy import deepcopy
from dataclasses import asdict
from typing import List

from django.utils.translation import gettext_lazy as _

from backend.flow.plugins.components.collections.redis.EmptyAct import SimpleEmptyComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent

logger = logging.getLogger("flow")


# 分批下发介质
def RedisMedia(machines: List, act_kwargs, sub_pipeline):
    acts_list, max_batch, batch_ips, batch_seq = [], 150, [], 0
    for ip in machines:
        batch_ips.append(ip)
        if len(batch_ips) < max_batch:
            continue
        else:
            batch_seq += 1
            act_kwargs.exec_ip = deepcopy(batch_ips)
            acts_list.append(
                {
                    "act_name": _("第{}批-下发介质").format(batch_seq),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
            batch_ips = []
    if len(batch_ips) > 0:
        batch_seq += 1
        act_kwargs.exec_ip = deepcopy(batch_ips)
        acts_list.append(
            {
                "act_name": _("第{}批-下发介质").format(batch_seq),
                "act_component_code": TransFileComponent.code,
                "kwargs": asdict(act_kwargs),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)
    # Add An Empty Node
    sub_pipeline.add_act(act_name=_("Redis-空节点"), act_component_code=SimpleEmptyComponent.code, kwargs={})


def GetBatchIPArries(ips):
    max_batch, batch_arries, batch_ips = 59, [], []
    for ip in ips:
        batch_ips.append(ip)
        if len(batch_ips) < max_batch:
            continue
        else:
            batch_arries.append(deepcopy(batch_ips))
            batch_ips = []
    if len(batch_ips) > 0:
        batch_arries.append(deepcopy(batch_ips))
    return batch_arries
