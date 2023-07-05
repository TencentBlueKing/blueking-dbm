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

from collections import defaultdict
from typing import Dict, Union

from django.db import models
from django.db.models.manager import Manager
from django.utils.translation import gettext_lazy as _

from backend.bk_web.constants import LEN_LONG, LEN_NORMAL, LEN_SHORT
from backend.bk_web.models import AuditedModel
from backend.configuration.constants import DBType
from backend.db_proxy.constants import CLUSTER__SERVICE_MAP, ClusterServiceType, ExtensionServiceStatus, ExtensionType
from backend.db_proxy.exceptions import ProxyPassBaseException
from backend.flow.consts import CloudDBHATypeEnum


class DBCloudProxy(AuditedModel):
    """云区域代理，目前作为 gse mesh 方案未出之前的临时方案，仅提供 http 代理能力"""

    bk_cloud_id = models.IntegerField(verbose_name=_("云区域 ID"), db_index=True)
    # 代理地址，可以是IP、域名、CLB等
    internal_address = models.CharField(verbose_name=_("代理内部地址"), max_length=LEN_LONG)
    external_address = models.CharField(verbose_name=_("代理外部地址"), max_length=LEN_LONG)

    class Meta:
        verbose_name = _("云区域代理")


class DBExtension(AuditedModel):
    """
    云区域组件服务部署记录，如nginx，dns，drs等
    目前的设计理念：
    - 一个云区域内只会有一套云区域组件(例如：不考虑主备的情况下，不会出现两个nginx)
    - 如果组件的类型一样，则认为二者可以互相替换(即如果我需要该组件的元数据，从数据库取任意一个均可)
    - detail信息维护的是单个组件的部署信息和其他必要信息(如drs除了自身的ip, port以外，还有user, pwd这个账户信息)
    - TODO: 目前还没有更新status字段的方案，后面可以通过nginx来心跳探测其他组件
    """

    bk_cloud_id = models.IntegerField(verbose_name=_("云区域 ID"), db_index=True)
    extension = models.CharField(
        _("扩展类型"),
        choices=ExtensionType.get_choices(),
        max_length=LEN_NORMAL,
    )
    status = models.CharField(
        verbose_name=_("服务状态"), max_length=LEN_NORMAL, choices=ExtensionServiceStatus.get_choices()
    )
    details = models.JSONField(verbose_name=_("详情"))

    @classmethod
    def get_extension_in_cloud(cls, bk_cloud_id: int, extension_type: ExtensionType):
        # 默认只返回状态正常的服务
        extensions = cls.objects.filter(
            bk_cloud_id=bk_cloud_id, extension=extension_type, status=ExtensionServiceStatus.RUNNING.value
        )
        return extensions

    @classmethod
    def get_latest_extension(cls, bk_cloud_id: int, extension_type: ExtensionType) -> "DBExtension":
        # 获取最新的服务
        return cls.get_extension_in_cloud(bk_cloud_id, extension_type).last()

    @classmethod
    def get_extension_access_hosts(cls, bk_cloud_id: int, extension_type: ExtensionType):
        extensions = cls.get_extension_in_cloud(bk_cloud_id, extension_type)
        if extension_type == ExtensionType.DBHA:
            extensions = extensions.filter(details__dbha_type=CloudDBHATypeEnum.AGENT)

        access_hosts = [ext.details["ip"] for ext in extensions]
        return access_hosts

    @classmethod
    def get_extension_info_in_cloud(cls, bk_cloud_id: int) -> Dict[str, Union[int, Dict]]:
        """
        获取当前云区域的所有组件信息，格式为：
        {
          "bk_cloud_id": 0,
          "nginx": {
             "host_infos": [....]
          },
          "drs": {
             "host_infos": [....]
          },
          "dns": {
             "host_infos": [....]
          },
          "dbha": {
             "gm": [....],
             "agent": [....]
          }
        }
        """
        extension_info: Dict[str, Union[int, Dict]] = defaultdict(lambda: defaultdict(list))
        extension_info["bk_cloud_id"] = bk_cloud_id
        for ext in cls.objects.filter(bk_cloud_id=bk_cloud_id):
            if ext.extension != ExtensionType.DBHA:
                extension_info[ext.extension.lower()]["host_infos"].append({"id": ext.id, **ext.details})
            else:
                dbha_type = ext.details["dbha_type"]
                extension_info[ext.extension.lower()][dbha_type].append({"id": ext.id, **ext.details})

        return extension_info

    def update_details(self, **kwargs):
        for key, value in kwargs.items():
            self.details[key] = value

        self.save()


class ClusterExtensionManager(Manager):
    def create(self, **kwargs):
        try:
            # 因为ClusterExtension是软删除，所以创建的时候要判断是否有同种配置记录
            # TODO: 后续需要支持定时删除带有软删除标记的nginx文件
            ext = ClusterExtension.objects.filter(
                bk_biz_id=kwargs["bk_biz_id"],
                db_type=kwargs["db_type"],
                cluster_name=kwargs["cluster_name"],
                service_type=kwargs["service_type"],
                is_deleted=False,
            )
            if ext.count():
                raise ProxyPassBaseException(
                    _("在业务{}下已经存在同种配置的服务组件记录，请检查是否在同一业务下部署了同名的集群").format(kwargs["bk_biz_id"])
                )
        except ClusterExtension.DoesNotExist:
            pass

        super().create(**kwargs)


class ClusterExtension(AuditedModel):
    """集群部署所带的额外服务组件记录，如es的kibana"""

    ip = models.CharField(verbose_name=_("部署机器ip"), max_length=LEN_NORMAL)
    port = models.CharField(verbose_name=_("部署机器port"), max_length=LEN_NORMAL)
    service_type = models.CharField(verbose_name=_("服务类型"), max_length=LEN_NORMAL)
    cluster_name = models.CharField(verbose_name=_("集群名"), max_length=LEN_LONG)
    db_type = models.CharField(_("集群类型"), choices=DBType.get_choices(), max_length=LEN_SHORT)
    bk_biz_id = models.IntegerField(verbose_name=_("业务ID"))
    bk_cloud_id = models.IntegerField(verbose_name=_("云区域ID"))

    # 当集群上架/下架时，需要更新is_deleted并且将is_flush更新为False，表示未执行;
    # 当定时任务执行的时候，需要拉去is_flush为False的进行操作，并刷新为True
    is_flush = models.BooleanField(verbose_name=_("是否刷新(该条记录是否执行)"), default=False)
    is_deleted = models.BooleanField(verbose_name=_("是否删除"), default=False)
    access_url = models.TextField(verbose_name=_("服务访问地址"), default="")

    objects = ClusterExtensionManager()

    class Meta:
        index_together = [("bk_biz_id", "db_type", "cluster_name", "service_type")]

    @classmethod
    def get_extension_by_flush(cls, is_flush: bool = False, is_deleted: bool = False):
        flush_extension = cls.objects.filter(is_flush=is_flush, is_deleted=is_deleted)
        return flush_extension

    def save_access_url(self, nginx_url):
        slash = (
            "" if self.service_type in [ClusterServiceType.KAFKA_MANAGER, ClusterServiceType.PULSAR_MANAGER] else "/"
        )
        self.access_url = (
            f"http://{nginx_url}/{self.bk_biz_id}/{self.db_type}/{self.cluster_name}/{self.service_type}{slash}"
        )
        self.save()

    @classmethod
    def get_cluster_service_url(cls, cluster):
        # 如果当前服务类型不支持，则直接返回空
        service_type = CLUSTER__SERVICE_MAP.get(cluster.cluster_type)
        if not service_type:
            return ""

        try:
            access_url = cls.objects.get(
                bk_biz_id=cluster.bk_biz_id,
                db_type=cluster.cluster_type,
                cluster_name=cluster.name,
                service_type=service_type,
            ).access_url
        except ClusterExtension.DoesNotExist:
            access_url = ""

        return access_url
