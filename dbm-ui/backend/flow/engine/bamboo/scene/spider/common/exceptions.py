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

from backend.exceptions import AppBaseException, ErrorCode


class TenDBClusterFlowBaseException(AppBaseException):
    MODULE_CODE = ErrorCode.FLOW_CODE
    MESSAGE = _("Flow模块TenDB Cluster异常")


class NormalSpiderFlowException(TenDBClusterFlowBaseException):
    ERROR_CODE = "001"
    MESSAGE = _("通用异常")
    MESSAGE_TPL = _("{message}")


class FailedToAssignIncrException(TenDBClusterFlowBaseException):
    ERROR_CODE = "002"
    MESSAGE = _("添加spider-master节点是分配incr初始值失败")
    MESSAGE_TPL = _("{message}")


class AddSpiderNodeFailedException(TenDBClusterFlowBaseException):
    ERROR_CODE = "003"
    MESSAGE = _("添加spider节点路由失败")
    MESSAGE_TPL = _("{message}")


class CtlSwitchToSlaveFailedException(TenDBClusterFlowBaseException):
    ERROR_CODE = "004"
    MESSAGE = _("中控集群切换失败")
    MESSAGE_TPL = _("{message}")


class DropSpiderNodeFailedException(TenDBClusterFlowBaseException):
    ERROR_CODE = "005"
    MESSAGE = _("删除spider节点路由失败")
    MESSAGE_TPL = _("{message}")
