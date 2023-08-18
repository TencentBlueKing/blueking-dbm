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
from enum import IntFlag, auto
from typing import List

from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import gettext_lazy as _


class ClusterStatus(str, StructuredEnum):
    NORMAL = EnumField("normal", _("normal"))
    ABNORMAL = EnumField("ABNORMAL", _("ABNORMAL"))
    # spider 定点构造的集群状态标记为临时集群
    TEMPORARY = EnumField("temporary", _("temporary"))


class ClusterStatusFlags(IntFlag):
    def flag_text(self) -> List[str]:
        flag_str = self.__str__()[len(self.__class__.__name__) + 1 :]
        return flag_str.split("|")


class ClusterDBHAStatusFlags(ClusterStatusFlags):
    ProxyUnavailable = auto()
    BackendMasterUnavailable = auto()
    BackendSlaveUnavailable = auto()


class ClusterTenDBClusterStatusFlag(ClusterStatusFlags):
    SpiderUnavailable = auto()
    RemoteMasterUnavailable = auto()
    RemoteSlaveUnavailable = auto()
