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
from rest_framework.response import Response

from backend.flow.engine.controller.doris import DorisController
from backend.flow.views.base import FlowTestView
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


class UpgradeDorisSceneApiView(FlowTestView):
    """
    api: /apis/v1/flow/scene/upgrade_doris
    params:
    {
        // bk_biz_id: 业务ID（必填）
        "bk_biz_id": 2005000002,

        // ticket_type: 单据类型，固定为 DORIS_UPGRADE（必填）
        "ticket_type": "DORIS_UPGRADE",

        // cluster_id: 待升级的Doris集群ID（必填，需在DBMeta中存在且为Doris类型）
        "cluster_id": 124,

        // new_version: 目标升级版本号（必填，不能与集群当前版本相同）
        "new_version": "3.0.4",

        // db_app_abbr: 业务英文缩写（必填）
        "db_app_abbr": "blueking",

        // uid: 单据唯一标识（必填）
        "uid": "111",

        // created_by: 单据创建人RTX（必填）
        "created_by": "rtx"
    }

    """

    def post(self, request):
        logger.info(_("开始升级Doris集群"))

        root_id = generate_root_id()
        logger.info("define root_id: {}".format(root_id))
        DorisController(root_id=root_id, ticket_data=request.data).doris_upgrade_scene()

        return Response({"root_id": root_id})
