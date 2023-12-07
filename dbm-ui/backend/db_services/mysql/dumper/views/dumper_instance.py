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

from django.forms.models import model_to_dict
from django.utils.translation import ugettext as _

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.enums.extra_process_type import ExtraProcessType
from backend.db_meta.models import Cluster
from backend.db_meta.models.dumper import DumperSubscribeConfig
from backend.db_meta.models.extra_process import ExtraProcessInstance
from backend.db_services.mysql.dumper.filters import DumperInstanceListFilter
from backend.db_services.mysql.dumper.serializers import DumperInstanceConfigSerializer

SWAGGER_TAG = "dumper"


class DumperInstanceViewSet(viewsets.AuditedModelViewSet):
    pagination_class = AuditedLimitOffsetPagination
    queryset = ExtraProcessInstance.objects.filter(proc_type=ExtraProcessType.TBINLOGDUMPER)
    serializer_class = DumperInstanceConfigSerializer
    filter_class = DumperInstanceListFilter

    @common_swagger_auto_schema(
        operation_summary=_("查询数据订阅实例列表"),
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        # 查询集群相关信息
        cluster_ids = [data["cluster_id"] for data in resp.data["results"]]
        id__cluster = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        # 查询dumper订阅配置相关信息
        dumper_config_ids = [data["extra_config"]["dumper_config_id"] for data in resp.data["results"]]
        id__dumper_config = {
            config.id: config for config in DumperSubscribeConfig.objects.filter(id__in=dumper_config_ids)
        }
        # 补充订阅实例的信息
        for data in resp.data["results"]:
            extra_config = data.pop("extra_config")
            # dumper是否已经不在集群master主机上 ---> 需要迁移
            source_cluster = id__cluster[data["cluster_id"]]
            master = source_cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
            data["need_transfer"] = data["ip"] != master.machine.ip
            # 补充集群信息和集群的master计信系
            data["source_cluster"] = source_cluster.simple_desc
            data["source_cluster"]["master_ip"] = master.machine.ip
            data["source_cluster"]["master_port"] = master.port
            # 补充订阅配置信息
            dumper_config_id = extra_config["dumper_config_id"]
            data["dumper_config"] = model_to_dict(id__dumper_config[dumper_config_id])
            data["dumper_id"] = data["area_name"] = extra_config["dumper_id"]

        return resp
