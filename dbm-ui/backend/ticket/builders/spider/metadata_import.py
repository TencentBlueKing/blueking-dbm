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
import json
import logging

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.components import DBConfigApi
from backend.components.dbconfig import constants as dbconf_const
from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache, DBModule, Spec
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, TicketType

logger = logging.getLogger("root")


class TenDBClusterMetadataImportDetailSerializer(MySQLBaseOperateDetailSerializer):
    json_content = serializers.JSONField(help_text=_("元数据json内容"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    db_module_id = serializers.IntegerField(help_text=_("模块ID"))
    spider_spec_id = serializers.IntegerField(help_text=_("spider规格ID"))
    remote_spec_id = serializers.IntegerField(help_text=_("remote规格ID"))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__module_version = ""
        self.__module_charset = ""
        self.__proxy_spec = None
        self.__storage_spec = None

    def validate(self, attrs):
        self.__validate_bk_biz_id_exists(attrs=attrs)
        self.__validate_db_module_id_exists(attrs=attrs)
        self.__validate_proxy_spec_id_exists(attrs=attrs)
        self.__validate_storage_spec_id_exists(attrs=attrs)
        self.__validate_file_content(attrs=attrs)
        return attrs

    @staticmethod
    def __validate_bk_biz_id_exists(attrs):
        bk_biz_id = attrs["bk_biz_id"]
        if not AppCache.objects.filter(bk_biz_id=bk_biz_id).exists():
            raise serializers.ValidationError(_("bk_biz_id: {} 不存在".format(bk_biz_id)))

    def __validate_db_module_id_exists(self, attrs):
        bk_biz_id = attrs["bk_biz_id"]
        db_module_id = attrs["db_module_id"]
        if not DBModule.objects.filter(db_module_id=db_module_id, bk_biz_id=bk_biz_id).exists():
            raise serializers.ValidationError(_("db_module_id: {} 不存在".format(db_module_id)))

        db_config = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(bk_biz_id),
                "level_name": dbconf_const.LevelName.MODULE,
                "level_value": str(db_module_id),
                "conf_file": dbconf_const.DEPLOY_FILE_NAME,
                "conf_type": dbconf_const.ConfType.DEPLOY,
                "namespace": ClusterType.TenDBCluster,
                "format": dbconf_const.FormatType.MAP,
            }
        )["content"]
        logger.info("app: {}, db module: {}, db config: {}".format(bk_biz_id, db_module_id, db_config))
        self.__module_version = db_config.get("db_version")
        self.__module_charset = db_config.get("charset")

    def __validate_proxy_spec_id_exists(self, attrs):
        spider_spec_id = attrs["spider_spec_id"]
        if not Spec.objects.filter(spec_id=spider_spec_id).exists():
            raise serializers.ValidationError(_("spider_spec_id: {} 不存在".format(spider_spec_id)))

        self.__proxy_spec = Spec.objects.get(spec_id=spider_spec_id)  # .get_spec_info()

    def __validate_storage_spec_id_exists(self, attrs):
        remote_spec_id = attrs["remote_spec_id"]
        if not Spec.objects.filter(spec_id=remote_spec_id).exists():
            raise serializers.ValidationError(_("remote_spec_id: {} 不存在".format(remote_spec_id)))

        self.__storage_spec = Spec.objects.get(spec_id=remote_spec_id)

    def __validate_file_content(self, attrs):
        # file_content = json.load(attrs["file"]).decode("utf-8")
        logger.info("json_content: {}".format(attrs["json_content"]))
        # tendbcluster 导出的文件数据结构和 tendbha 不太一样
        # 这里是一个字典, tendbha 的是个 list
        for cluster_json in attrs["json_content"].values():
            logger.info("cluster_json: {}".format(cluster_json))
            self.__validate_cluster_json(cluster_json=cluster_json, attrs=attrs)

    def __validate_cluster_json(self, cluster_json, attrs):
        self.__validate_cluster_version_charset(cluster_json=cluster_json, attrs=attrs)
        self.__validate_proxy_spec_match(cluster_json=cluster_json)
        self.__validate_storage_spec_match(cluster_json=cluster_json)
        self.__validate_cluster_disaster(cluster_json=cluster_json)

    @staticmethod
    def __validate_cluster_disaster(cluster_json):
        disaster = cluster_json["disaster_level"]
        if disaster not in AffinityEnum.get_values():
            raise serializers.ValidationError(_("隔离级别 {} 不支持".format(disaster)))

    def __validate_cluster_version_charset(self, cluster_json, attrs):
        db_module_id = attrs["db_module_id"]

        cluster_version = cluster_json["version"]
        cluster_charset = cluster_json["charset"]

        # db module 的 version = MySQL-5.7
        # 上报的版本是 5.7.20
        trans_cluster_version = "MySQL-{}".format(".".join(cluster_version.split(".")[:2]))
        logger.info("{} trans to {}".format(cluster_version, trans_cluster_version))

        if cluster_charset != self.__module_charset or trans_cluster_version != self.__module_version:
            immute_domain = cluster_json["immute_domain"]
            raise serializers.ValidationError(
                _(
                    "{} version: {} or charset: {} not match to db module: {}: {}, {}".format(
                        immute_domain,
                        cluster_version,
                        cluster_charset,
                        db_module_id,
                        self.__module_version,
                        self.__module_charset,
                    )
                )
            )

    def __validate_proxy_spec_match(self, cluster_json):
        """
        只检查 spider master 的规格
        """
        proxies = (
            cluster_json["master_spiders"]
            # + cluster_json["slave_spiders"]
            # + cluster_json["master_tmp_spiders"]
            # + cluster_json["slave_tmp_spiders"]
        )
        for ip in list(set([ele["ip"] for ele in proxies])):
            mj = list(filter(lambda e: e["IP"] == ip, cluster_json["machines"]))
            if not mj:
                raise serializers.ValidationError(_("{} not found in machine part".format(ip)))

            self.__validate_machine_spec_match(machine_json=mj[0], spec_obj=self.__proxy_spec)

    def __validate_storage_spec_match(self, cluster_json):
        remotes = []
        for s in cluster_json["sets"]:
            remotes.append(s["master"])
            remotes.append(s["slave"])

        ips = list(set([ele["ip"] for ele in remotes]))

        for ip in ips:
            mj = list(filter(lambda e: e["IP"] == ip, cluster_json["machines"]))
            if not mj:
                raise serializers.ValidationError(_("{} not found in machine part".format(ip)))

            self.__validate_machine_spec_match(machine_json=mj[0], spec_obj=self.__storage_spec)

    @staticmethod
    def __validate_machine_spec_match(machine_json, spec_obj: Spec):
        machine_cpu = machine_json["Cpu"]
        machine_mem = machine_json["Mem"]  # MB
        machine_ip = machine_json["IP"]

        machine_mem /= 1024  # 规格是 GB, 所以转换下

        machine_disks_json = json.loads(machine_json["Disks"])

        if not (spec_obj.cpu["min"] <= machine_cpu <= spec_obj.cpu["max"]):
            raise serializers.ValidationError(
                _("{} cpu={} not match to {}".format(machine_ip, machine_cpu, spec_obj.cpu))
            )

        # 内存 MB, GB转换时很难保证完全匹配, 所以规格区间需要扩展匹配
        spec_obj.mem["min"] = spec_obj.mem["min"] - 1 if spec_obj.mem["min"] > 1 else 1
        spec_obj.mem["max"] += 1
        logger.info("mem spec expand to {}".format(spec_obj.mem))

        if not (spec_obj.mem["min"] <= machine_mem <= spec_obj.mem["max"]):
            raise serializers.ValidationError(
                _("{} mem={}GB not match to {}GB".format(machine_ip, machine_mem, spec_obj.mem))
            )

        for spec_disk in spec_obj.storage_spec:
            spec_mount_point = spec_disk["mount_point"]
            spec_size = spec_disk["size"]  # GB
            spec_type = spec_disk["type"].lower()

            if spec_mount_point in machine_disks_json:
                machine_disk_size = machine_disks_json[spec_mount_point]["size"]  # GB
                machine_disk_type = machine_disks_json[spec_mount_point]["disk_type"].lower()

                if machine_disk_size < spec_size:
                    raise serializers.ValidationError(
                        _(
                            "{} {} size={}GB not match to {}".format(
                                machine_ip, spec_mount_point, machine_disk_size, spec_disk
                            )
                        )
                    )

                if spec_type != "all" and spec_type != machine_disk_type:
                    raise serializers.ValidationError(
                        _(
                            "{} {} type={} not match to {}".format(
                                machine_ip, spec_mount_point, machine_disk_type, spec_disk
                            )
                        )
                    )
            else:
                raise serializers.ValidationError(
                    _("{} mount point {} not found".format(machine_ip, spec_mount_point))
                )


class TenDBClusterMetadataImportFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.metadata_import_scene


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_METADATA_IMPORT)
class TenDBClusterMetadataImportFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = TenDBClusterMetadataImportDetailSerializer
    inner_flow_builder = TenDBClusterMetadataImportFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 元数据导入")
    retry_type = FlowRetryType.MANUAL_RETRY
