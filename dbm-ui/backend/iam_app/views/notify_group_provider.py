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

from django.db import models

from backend.db_monitor.models import NoticeGroup
from backend.iam_app.dataclass.resources import MonitorPolicyResourceMeta, ResourceEnum
from backend.iam_app.handlers.converter import NotifyGroupDjangoQuerySetConverter
from backend.iam_app.views.monitor_policy_provider import MonitorPolicyResourceProvider

logger = logging.getLogger("root")


class NotifyGroupResourceProvider(MonitorPolicyResourceProvider):
    """
    告警组资源的反向拉取基类，和监控策略的provider类似，可直接继承使用
    """

    model: models.Model = NoticeGroup
    resource_meta: MonitorPolicyResourceMeta = ResourceEnum.NOTIFY_GROUP

    @staticmethod
    def parse_iam_path(iam_path):
        topo_type, topo_value = iam_path.strip("/").split(",")
        topo_type = "bk_biz_id" if topo_type == "biz" else "db_type"
        return {topo_type: topo_value}

    def list_instance_by_policy(self, filter, page, **options):
        options.update(converter_class=NotifyGroupDjangoQuerySetConverter)
        super().list_instance_by_policy(filter, page, **options)
