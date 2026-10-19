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
from django.utils.translation import gettext as _

from backend.exceptions import AppBaseException, ErrorCode


class HdfsFlowBaseException(AppBaseException):
    MODULE_CODE = ErrorCode.FLOW_CODE
    MESSAGE = _("Flow模块HDFS异常")


class NormalHdfsFlowException(HdfsFlowBaseException):
    ERROR_CODE = "001"
    MESSAGE = _("通用异常")
    MESSAGE_TPL = _("{message}")


class ReplaceMachineNullException(HdfsFlowBaseException):
    ERROR_CODE = "003"
    MESSAGE = _("替换旧机器不能为空")
    MESSAGE_TPL = _("HDFS集群替换旧机器不能为空")


class ReplaceMachineCountException(HdfsFlowBaseException):
    ERROR_CODE = "004"
    MESSAGE = _("HDFS替换新旧机器数量不一致")
    MESSAGE_TPL = _("HDFS集群替换角色{hdfs_role}数量不一致")


class HaProxyHostNullException(HdfsFlowBaseException):
    ERROR_CODE = "005"
    MESSAGE = _("没有可用于安装HAProxy的机器")
    MESSAGE_TPL = _("HDFS集群没有与NameNode不同机的ZooKeeper节点，无法确定HAProxy安装机器")


class AuthInfoNullException(HdfsFlowBaseException):
    ERROR_CODE = "006"
    MESSAGE = _("获取HDFS集群账号信息失败")
    MESSAGE_TPL = _("密码服务和dbconfig均未获取到HDFS集群的用户名或密码")
