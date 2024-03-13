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
import gzip
import io
import json
from dataclasses import asdict

from django.db import models
from django.forms import model_to_dict
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.models import AuditedModel
from backend.components import CCApi
from backend.constants import CommonHostDBMeta
from backend.db_meta.enums import AccessLayer, ClusterType, MachineType
from backend.db_meta.exceptions import HostDoseNotExistInCmdbException
from backend.db_meta.models import AppCache, BKCity
from backend.utils.string import base64_encode


class Machine(AuditedModel):
    ip = models.GenericIPAddressField(default="", help_text=_("IP 地址"))
    bk_biz_id = models.IntegerField(default=0)
    db_module_id = models.IntegerField(default=0)
    access_layer = models.CharField(max_length=64, choices=AccessLayer.get_choices(), default="")
    machine_type = models.CharField(max_length=64, choices=MachineType.get_choices(), default="")
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")
    bk_city = models.ForeignKey(BKCity, on_delete=models.PROTECT)
    bk_host_id = models.PositiveBigIntegerField(primary_key=True, default=0)
    bk_os_name = models.CharField(max_length=128, default="", blank=True, null=True, help_text=_("操作系统"))
    bk_idc_area = models.CharField(max_length=128, default="", blank=True, null=True, help_text=_("区域"))
    bk_idc_area_id = models.IntegerField(default=0, help_text=_("区域 ID"))
    bk_sub_zone = models.CharField(max_length=128, default="", blank=True, null=True, help_text=_("子 Zone"))
    bk_sub_zone_id = models.IntegerField(default=0, help_text=_("子 Zone ID"))
    bk_rack = models.CharField(max_length=128, default="", blank=True, null=True, help_text=_("机架"))
    bk_rack_id = models.IntegerField(default=0, help_text=_("机架 ID"))
    bk_svr_device_cls_name = models.CharField(max_length=128, default="", blank=True, null=True, help_text=_("标准设备类型"))
    bk_idc_name = models.CharField(max_length=128, default="", blank=True, null=True, help_text=_("机房"))
    bk_idc_id = models.IntegerField(default=0, help_text=_("机房 ID"))
    bk_cloud_id = models.IntegerField(default=0, help_text=_("云区域 ID"))
    bk_agent_id = models.CharField(max_length=128, default="", blank=True, null=True, help_text=_("Agent ID"))
    net_device_id = models.CharField(max_length=256, default="", blank=True, null=True)  # 这个 id 是个逗号分割的字符串
    spec_id = models.PositiveBigIntegerField(default=0, help_text=_("虚拟规格ID"))
    spec_config = models.JSONField(default=dict, help_text=_("当前的虚拟规格配置"))

    class Meta:
        unique_together = ("ip", "bk_cloud_id")
        verbose_name = verbose_name_plural = _("机器主机(Machine)")

    def __str__(self):
        return self.ip

    @property
    def dbm_meta(self) -> dict:
        proxies = self.proxyinstance_set.all()
        storages = self.storageinstance_set.all()

        host_labels = []

        def compress_dbm_meta_content(dbm_meta: dict) -> str:
            """
            压缩 dbm_meta
            """
            # 使用gzip压缩
            # python3.6 gzip 不支持 mtime 参数，python3.10 可以直接使用 gzip.compress 压缩
            buf = io.BytesIO()
            with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as f:
                f.write(json.dumps(dbm_meta).encode("utf-8"))
            compressed_data = buf.getvalue()

            # 将压缩后的字节转换为Base64编码的字符串
            base64_encoded_str = base64_encode(compressed_data)
            return base64_encoded_str

        for proxy in proxies:
            for cluster in proxy.cluster.all():
                tendb_cluster_spider_ext = getattr(proxy, "tendbclusterspiderext", None)
                host_labels.append(
                    asdict(
                        CommonHostDBMeta(
                            app=AppCache.get_app_attr(cluster.bk_biz_id, default=cluster.bk_biz_id),
                            appid=str(cluster.bk_biz_id),
                            cluster_type=cluster.cluster_type,
                            cluster_domain=cluster.immute_domain,
                            db_type=ClusterType.cluster_type_to_db_type(cluster.cluster_type),
                            # tendbcluster中扩展了proxy的类型，需要特殊处理
                            instance_role=tendb_cluster_spider_ext.spider_role
                            if tendb_cluster_spider_ext
                            else "proxy",
                            instance_port=str(proxy.port),
                        )
                    )
                )

        for storage in storages:
            # influxdb需要单独处理
            if storage.cluster_type == ClusterType.Influxdb.value:
                host_labels.append(
                    asdict(
                        CommonHostDBMeta(
                            app=AppCache.get_app_attr(storage.bk_biz_id, default=storage.bk_biz_id),
                            appid=str(storage.bk_biz_id),
                            cluster_domain=storage.machine.ip,
                            cluster_type=storage.cluster_type,
                            db_type=ClusterType.cluster_type_to_db_type(storage.cluster_type),
                            instance_role=storage.instance_role,
                            instance_port=str(storage.port),
                        )
                    )
                )
                continue

            for cluster in storage.cluster.all():
                host_labels.append(
                    asdict(
                        CommonHostDBMeta(
                            app=AppCache.get_app_attr(cluster.bk_biz_id, default=cluster.bk_biz_id),
                            appid=str(cluster.bk_biz_id),
                            cluster_domain=cluster.immute_domain,
                            cluster_type=cluster.cluster_type,
                            db_type=ClusterType.cluster_type_to_db_type(cluster.cluster_type),
                            instance_role=storage.instance_role,
                            instance_port=str(storage.port),
                        )
                    )
                )

        return {"version": "v2", "content": compress_dbm_meta_content({"common": {}, "custom": host_labels})}

    @classmethod
    def get_host_info_from_cmdb(cls, bk_host_id: int) -> dict:
        """获取主机的基本信息"""
        host_info = CCApi.list_hosts_without_biz(
            {
                "fields": [
                    "bk_host_id",
                    "bk_os_name",
                    "bk_host_innerip",
                    "idc_city_name",
                    "sub_zone",
                    "rack",
                    "bk_svr_device_cls_name",
                    "bk_idc_area",
                    "idc_name",
                    "idc_id",
                    "bk_cloud_name",
                    "net_device_id",
                    "bk_cpu",
                    "bk_disk",
                    "bk_mem",
                    "bk_agent_id",
                ],
                "host_property_filter": {
                    "condition": "AND",
                    "rules": [
                        {"field": "bk_host_id", "operator": "equal", "value": bk_host_id},
                    ],
                },
            }
        )

        try:
            exact_host_info = host_info["info"][0]
            # 格式化idc信息
            exact_host_info["bk_idc_name"] = exact_host_info.pop("idc_name", "")
            exact_host_info["bk_idc_id"] = exact_host_info.pop("idc_id", "")
            return exact_host_info
        except IndexError:
            raise HostDoseNotExistInCmdbException(bk_host_id=bk_host_id)

    @classmethod
    def is_refer_spec(cls, spec_ids):
        """是否引用了相关规格"""
        return cls.objects.filter(spec_id__in=spec_ids).exists()

    @property
    def simple_desc(self):
        return model_to_dict(self)
