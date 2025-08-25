"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.utils.translation import ugettext as _

from backend.flow.engine.validate.base_validate import BaseValidator, validator_log_format
from backend.flow.utils.redis.redis_util import version_ge


class RedisBaseValidator(BaseValidator):
    """
    redis相关架构的通用基础校验类
    """

    @classmethod
    @validator_log_format
    def check_version_allow(cls, version_list: list, target_version: str):
        """
        检查version_list中的版本是否允许变更到目标版本
        只允许从低版本到高版本
        """
        err_msg = ""
        for version in version_list:
            if not version_ge(target_version, version):
                err_msg += _("存在源版本{} 大于 目标版本{} \n".format(version, target_version))
        return err_msg
