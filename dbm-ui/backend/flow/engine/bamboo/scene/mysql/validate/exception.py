"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import gettext as _

from backend.flow.engine.validate.exceptions import FlowValidateBaseException


class ProxyReduceCountFailedException(FlowValidateBaseException):
    ERROR_CODE = "35001"
    MESSAGE = _("集群proxy缩容没有可用的proxy")
    MESSAGE_TPL = _("{message}")


class ProxySpecFailedException(FlowValidateBaseException):
    ERROR_CODE = "35002"
    MESSAGE = _("出现两个以后的proxy规格")
    MESSAGE_TPL = _("{message}")


class MySQLStorageVersionFailedException(FlowValidateBaseException):
    ERROR_CODE = "35003"
    MESSAGE = _("MySQL存储节点版本一致性检查失败")
    MESSAGE_TPL = _("{message}")


class MySQLUpgradeVersionFailedException(FlowValidateBaseException):
    ERROR_CODE = "35004"
    MESSAGE = _("MySQL升级版本检查失败")
    MESSAGE_TPL = _("{message}")


class MySQLMasterSlaveVersionFailedException(FlowValidateBaseException):
    ERROR_CODE = "35005"
    MESSAGE = _("MySQL主从实例版本不一致")
    MESSAGE_TPL = _("{message}")
