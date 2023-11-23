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
from typing import Any, Dict, List

from django.utils.translation import ugettext as _

from backend.utils.cache import class_member_cache
from blue_krill.data_types.enum import EnumField, StructuredEnum


class CosBucketEnum(StructuredEnum):
    """对象存储仓库枚举"""

    # TODO 这里如果加 ugettext_lazy 会有 AppRegistryNotReady 异常，怀疑是 StructuredEnum 的问题，待解决
    PUBLIC = EnumField("public", _("公开仓库"))
    PRIVATE = EnumField("private", _("私有仓库"))


class JobFileType(StructuredEnum):
    """作业平台源文件类型"""

    SERVER = EnumField(1, _("服务器文件"))
    THIRD_PART = EnumField(3, _("第三方源文件"))


class StorageType(StructuredEnum):
    """文件存储类型枚举"""

    FILE_SYSTEM = EnumField("FILE_SYSTEM", _("本地文件系统"))
    BLUEKING_ARTIFACTORY = EnumField("BLUEKING_ARTIFACTORY", _("蓝鲸制品库"))

    @classmethod
    @class_member_cache()
    def list_cos_member_values(cls) -> List[str]:
        """列举属于对象存储类型"""
        return [cls.BLUEKING_ARTIFACTORY.value]

    @classmethod
    @class_member_cache()
    def get_member_value__job_file_type_map(cls) -> Dict[str, int]:
        """
        获取文件存储类型 - JOB源文件类型映射
        """
        return {
            cls.BLUEKING_ARTIFACTORY.value: JobFileType.THIRD_PART.value,
            cls.FILE_SYSTEM.value: JobFileType.SERVER.value,
        }

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.BLUEKING_ARTIFACTORY: _("蓝鲸制品库"), cls.FILE_SYSTEM: _("本地文件系统")}

    @classmethod
    @class_member_cache()
    def get_member_value__alias_map(cls) -> Dict[Any, str]:
        """
        获取枚举成员值与释义的映射关系，缓存计算结果
        :return:
        """
        member_value__alias_map = {}
        member__alias_map = cls._get_member__alias_map()

        for member, alias in member__alias_map.items():
            if type(member) is not cls:
                raise ValueError(f"except member type -> {cls}, but got -> {type(member)}")
            member_value__alias_map[member.value] = alias

        return member_value__alias_map


class FileCredentialType(StructuredEnum):
    """文件凭证类型"""

    SECRET_KEY = EnumField("SECRET_KEY", _("单一SecretKey"))
    ACCESS_KEY_SECRET_KEY = EnumField("ACCESS_KEY_SECRET_KEY", "AppID+SecretKey")
    PASSWORD = EnumField("PASSWORD", _("单一密码"))
    USERNAME_PASSWORD = EnumField("USERNAME_PASSWORD", _("用户名+密码"))
