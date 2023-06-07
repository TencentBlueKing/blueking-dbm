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
from enum import Enum
from typing import Dict

from django.utils.translation import ugettext as _

from backend.utils import env
from backend.utils.basic import choices_to_namedtuple, tuple_choices
from backend.utils.enum import EnhanceEnum


class CommonEnum(EnhanceEnum):
    SEP = ":"
    PAGE_RETURN_ALL_FLAG = -1
    DEFAULT_HOST_FUZZY_SEARCH_FIELDS = ["bk_host_innerip", "bk_host_innerip_v6", "bk_host_name"]
    DEFAULT_HOST_FIELDS = [
        "bk_host_id",
        "bk_cloud_id",
        "bk_host_innerip",
        "bk_host_innerip_v6",
        "bk_host_name",
        "bk_os_type",
        "bk_agent_id",
        "bk_cloud_vendor",
        "bk_mem",
        "bk_disk",
        "bk_cpu",
        "bk_cpu_architecture",
        "bk_cpu_module",
        "operator",
    ]

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {
            cls.SEP: _("字段分隔符"),
            cls.PAGE_RETURN_ALL_FLAG: _("全量返回标志"),
            cls.DEFAULT_HOST_FUZZY_SEARCH_FIELDS: _("默认模糊查询字段"),
            cls.DEFAULT_HOST_FIELDS: _("主机列表默认返回字段"),
        }


class ScopeType(EnhanceEnum):
    """作用域类型"""

    BIZ = "biz"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.BIZ: _("业务")}


class ModeType(EnhanceEnum):
    """模式类型"""

    ALL = "all"
    IDLE_ONLY = "idle_only"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.ALL: _("完整模式"), cls.IDLE_ONLY: _("空闲机模式")}


class ObjectType(EnhanceEnum):
    """CMDB 拓扑节点类型"""

    BIZ = "biz"
    SET = "set"
    MODULE = "module"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.BIZ: _("业务"), cls.SET: _("集群"), cls.MODULE: _("模块")}


class AgentStatusType(EnhanceEnum):
    """对外展示的 Agent 状态"""

    ALIVE = 1
    NO_ALIVE = 0

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.ALIVE: _("存活"), cls.NO_ALIVE: _("未存活")}


PROC_STATE_TUPLE = ("RUNNING", "UNKNOWN", "TERMINATED", "NOT_INSTALLED", "UNREGISTER", "REMOVED", "MANUAL_STOP")
PROC_STATE_CHOICES = tuple_choices(PROC_STATE_TUPLE)
ProcStateType = choices_to_namedtuple(PROC_STATE_CHOICES)

OS_TUPLE = ("LINUX", "WINDOWS", "AIX", "SOLARIS")
OS_CHOICES = tuple_choices(OS_TUPLE)
OsType = choices_to_namedtuple(OS_CHOICES)
OS_CHN = {os_type: os_type if os_type == OsType.AIX else os_type.capitalize() for os_type in OS_TUPLE}
BK_OS_TYPE = {"LINUX": "1", "WINDOWS": "2", "AIX": "3", "SOLARIS": "5"}

# 默认云区域ID
DEFAULT_CLOUD = int(env.get_type_env("DEFAULT_CLOUD", 0))
DEFAULT_CLOUD_NAME = env.get_type_env("DEFAULT_CLOUD_NAME", "直连区域")

# cc默认模块类型
IDLE_HOST_MODULE = 1  # 空闲机
FAULT_HOST_MODULE = 2  # 故障机
RECYCLE_HOST_MODULE = 3  # 待回收

# DBM管理的CC集群名
DB_MANAGE_SET = "db.manage.set"

# 磁盘类型，目前固定写死
DEVICE_CLASS = ["SSD", "HDD", "ALL"]
