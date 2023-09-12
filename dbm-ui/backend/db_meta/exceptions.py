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
from django.utils.translation import ugettext_lazy as _

from backend.exceptions import AppBaseException, ErrorCode


class DBMetaBaseException(AppBaseException):
    MODULE_CODE = ErrorCode.DB_META_CODE
    MESSAGE = _("DBMeta模块异常")


class SearchBusinessCountException(DBMetaBaseException):
    ERROR_CODE = "001"
    MESSAGE = _("通用异常")
    MESSAGE_TPL = _("{message}")


class CreateTenDBHAPreCheckException(DBMetaBaseException):
    ERROR_CODE = "002"
    MESSAGE = _("新建TenDBHA前置检查异常")
    MESSAGE_TPL = _("{msg}")


class StorageInstanceTupleExistException(DBMetaBaseException):
    ERROR_CODE = "003"
    MESSAGE = _("同步关系记录已存在")
    MESSAGE_TPL = _("{ejector}和{receiver}的同步关系记录已存在")


class ProxyBackendNotEmptyException(DBMetaBaseException):
    ERROR_CODE = "004"
    MESSAGE = _("proxy已绑定后端存储")
    MESSAGE_TPL = _("{proxy}已绑定后端存储")


class DbModuleExistException(DBMetaBaseException):
    ERROR_CODE = "005"
    MESSAGE = _("DB模块已存在")
    MESSAGE_TPL = _("DB模块[{db_module_name}]已存在，请重新命名")


class TenDBHAClusterExistException(DBMetaBaseException):
    ERROR_CODE = "006"
    MESSAGE = _("TenDBHA集群已存在")
    MESSAGE_TPL = _("TenDBHA集群{cluster}已存在")


class ClusterEntryExistException(DBMetaBaseException):
    ERROR_CODE = "007"
    MESSAGE = _("集群访问入口已存在")
    MESSAGE_TPL = _("集群访问入口{entry}已存在")


class CreateTendisPreCheckException(DBMetaBaseException):
    ERROR_CODE = "008"
    MESSAGE = _("新建Tendis前置检查异常")
    MESSAGE_TPL = _("{msg}")


class TendisClusterExistException(DBMetaBaseException):
    ERROR_CODE = "009"
    MESSAGE = _("Tendis集群已存在")
    MESSAGE_TPL = _("Tendis集群{cluster}已存在")


class HostDoseNotExistInCmdbException(DBMetaBaseException):
    ERROR_CODE = "010"
    MESSAGE = _("主机在CMDB中不存在")
    MESSAGE_TPL = _("主机[bk_host_id={bk_host_id}]在CMDB中不存在")


class TendisClusterNotExistException(DBMetaBaseException):
    ERROR_CODE = "011"
    MESSAGE = _("Tendis集群不存在")
    MESSAGE_TPL = _("Tendis集群{cluster}不存在")


class ClusterSetDtlExistException(DBMetaBaseException):
    ERROR_CODE = "012"
    MESSAGE = _("集群,分片不存在")
    MESSAGE_TPL = _("集群{cluster}分片不存在")


class ClusterEntryNotExistException(DBMetaBaseException):
    ERROR_CODE = "013"
    MESSAGE = _("集群访问入口不存在")
    MESSAGE_TPL = _("集群访问入口 {entry} 不存在")


class DBMetaException(DBMetaBaseException):
    ERROR_CODE = "014"
    MESSAGE = _("通用异常")
    MESSAGE_TPL = _("{message}")


class ClusterNotExistException(DBMetaBaseException):
    ERROR_CODE = "015"
    MESSAGE = _("集群不存在")
    MESSAGE_TPL = _("集群类型:{cluster_type}, ID:{cluster_id}, 域名:{immute_domain} 不存在")


class InstanceNotExistException(DBMetaBaseException):
    ERROR_CODE = "016"
    MESSAGE = _("实例不存在")
    MESSAGE_TPL = _("实例 云区域{bk_cloud_id} {ip}:{port} 不存在")


class ClusterExclusiveOperateException(DBMetaBaseException):
    ERROR_CODE = "017"
    MESSAGE = _("执行互斥")
    MESSAGE_TPL = _("操作{ticket_type}与集群{cluster_id}正在运行的动作{active_ticket_type}存在互斥/重复操作")


class MasterInstanceNotExistException(DBMetaBaseException):
    ERROR_CODE = "018"
    MESSAGE = _("主库不存在")
    MESSAGE_TPL = _("集群类型:{cluster_type}, ID:{cluster_id} 主库不存在")


class ClusterNoStorageSetException(DBMetaBaseException):
    ERROR_CODE = "019"
    MESSAGE = _("集群不支持分片")
    MESSAGE_TPL = _("集群类型:{cluster_type}, ID:{cluster_id} 没有数据分片逻辑")


class TenDBClusterInvalidCTLPrimaryNode(DBMetaBaseException):
    ERROR_CODE = "020"
    MESSAGE = _("无效中控主节点")
    MESSAGE_TPL = _("中控主节点必须是 spider_master")


class ClusterProxyExtraNotDefine(DBMetaBaseException):
    ERROR_CODE = "021"
    MESSAGE = _("集群 proxy 无附加信息")
    MESSAGE_TPL = _("集群类型:{cluster_type} proxy 无附加信息")


class ClusterDeployHasRefException(DBMetaBaseException):
    ERROR_CODE = "023"
    MESSAGE = _("部署方案使用中")
    MESSAGE_TPL = _("部署方案:{name} 被 {ref_cnt} 个集群引用")


class ClusterEntryBindForwardException(DBMetaBaseException):
    ERROR_CODE = "024"
    MESSAGE = _("访问入口请求转发和IP绑定混用")
    MESSAGE_TPL = _("访问入口 {entry} 绑定到 {bind_cnt} 台机器, 转发到 {forward_to} 不能同时存在")


class ClusterEntryNotBindException(DBMetaBaseException):
    ERROR_CODE = "025"
    MESSAGE = _("访问入口未绑定")
    MESSAGE_TPL = _("访问入口 {entry} 未绑定到 IP")
