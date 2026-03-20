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
from django.utils.translation import gettext_lazy as _

from blue_krill.data_types.enum import EnumField, IntStructuredEnum, StrStructuredEnum


class InstanceStatus(StrStructuredEnum):
    RUNNING = EnumField("running", _("running"))
    UNAVAILABLE = EnumField("unavailable", _("unavailable"))
    AVAILABLE = EnumField("available", _("available"))
    RESTORING = EnumField("restoring", _("restoring"))
    UPGRADING = EnumField("upgrading", _("upgrading"))


class MongoDBStorageInstanceStatus(IntStructuredEnum):
    """MongoDB ReplicaSet Storage Instance Status"""

    STARTUP = EnumField(0, _("STARTUP"))
    PRIMARY = EnumField(1, _("PRIMARY"))
    SECONDARY = EnumField(2, _("SECONDARY"))
    RECOVERING = EnumField(3, _("RECOVERING"))
    FATAL = EnumField(4, _("FATAL"))
    STARTUP2 = EnumField(5, _("STARTUP2"))
    UNKNOWN = EnumField(6, _("UNKNOWN"))
    ARBITER = EnumField(7, _("ARBITER"))
    DOWN = EnumField(8, _("DOWN"))
    ROLLBACK = EnumField(9, _("ROLLBACK"))
    REMOVED = EnumField(10, _("REMOVED"))
    # 其他状态，用于未知状态
    OTHER = EnumField(99, _("OTHER"))

    """
    0: STARTUP进程刚启动，尚未加载副本集配置。
    1: PRIMARY主节点，接收所有写操作。
    2: SECONDARY从节点，复制数据并保持同步。
    3: RECOVERING正在恢复或准备成员身份转换，此时不可读写。
    4: FATAL节点遇到不可恢复的错误（现版本较少见，通常直接宕机）。
    5: STARTUP2已加载配置，正在进行初始同步（Initial Sync）。
    6: UNKNOWN无法连接到该成员，状态未知。
    7: ARBITER仲裁者，仅投票，不存储数据。
    8: DOWN节点已被判定为不可达/宕机。
    9: ROLLBACK节点正在回滚数据，通常在执行成员身份转换时出现。
    10: REMOVED节点已被显式移除，不再参与副本集操作。
    """

    @classmethod
    def get_status_by_value(cls, code: int) -> "MongoDBStorageInstanceStatus":
        for status in cls:
            if status.value == code:
                return status
        return cls.OTHER

    @classmethod
    def get_status_by_name(cls, name: str) -> "MongoDBStorageInstanceStatus":
        for status in cls:
            if status.name == name:
                return status
        return cls.OTHER
