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

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.bigdata.doris.upgrade_policy import DorisUpgradeVersionPolicy
from backend.flow.engine.bamboo.scene.doris.exceptions import DorisUpgradeParamCheckFailedException
from backend.flow.engine.validate.base_validate import BaseValidator

logger = logging.getLogger("flow")


class DorisUpgradeValidator(BaseValidator):
    """
    Doris升级Flow的参数校验类

    校验内容：
    1. 检查cluster_id对应的Doris集群在DBMeta中存在
    2. 检查new_version不为空，且目标版本可从当前版本升级（基于版本升级映射）

    数据格式：
    {
        "bk_biz_id": 2005000002,
        "ticket_type": "DORIS_UPGRADE",
        "cluster_id": 124,
        "new_version": "3.0.4",
        "uid": "111",
        "created_by": "rtx"
    }
    """

    def __call__(self):
        """
        执行校验

        校验流程：
        1. 校验cluster_id对应的Doris集群存在
        2. 校验new_version不为空，且目标版本可从当前版本升级（基于版本升级映射）
        """
        error_msgs = []

        cluster_id = self.data.get("cluster_id")
        new_version = self.data.get("new_version")

        # 校验cluster_id：直接查询Doris类型的集群，不存在即报错
        cluster = None
        if not cluster_id:
            error_msgs.append(_("cluster_id 不能为空"))
        else:
            try:
                cluster = Cluster.objects.get(id=cluster_id, cluster_type=ClusterType.Doris)
            except Cluster.DoesNotExist:
                error_msgs.append(_("Doris集群 {} 不存在").format(cluster_id))

        # 校验new_version：规则收敛在 DorisUpgradeVersionPolicy（series + 严格大于 + 介质存在性）
        if cluster:
            is_valid, msg = DorisUpgradeVersionPolicy.validate(cluster.major_version, new_version)
            if not is_valid:
                error_msgs.append(msg)

        # 如果存在错误，抛出异常
        if error_msgs:
            raise DorisUpgradeParamCheckFailedException("\n".join(error_msgs))

        return None
