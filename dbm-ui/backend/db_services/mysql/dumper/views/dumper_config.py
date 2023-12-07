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
from collections import Counter

from django.utils.translation import ugettext as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_meta.enums.extra_process_type import ExtraProcessType
from backend.db_meta.models.dumper import DumperSubscribeConfig
from backend.db_meta.models.extra_process import ExtraProcessInstance
from backend.db_services.mysql.dumper.serializers import DumperSubscribeConfigSerializer, VerifyDuplicateNamsSerializer

SWAGGER_TAG = "dumper"


class DumperConfigViewSet(viewsets.AuditedModelViewSet):
    pagination_class = AuditedLimitOffsetPagination
    queryset = DumperSubscribeConfig.objects.all()
    serializer_class = DumperSubscribeConfigSerializer
    filter_fields = {
        "update_at": ["gte", "lte"],
        "name": ["icontains"],
        "receiver_type": ["exact"],
        "receiver": ["icontains"],
    }

    @common_swagger_auto_schema(
        operation_summary=_("新建数据订阅配置"),
        tags=[SWAGGER_TAG],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("更新数据订阅配置"),
        tags=[SWAGGER_TAG],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("更新部分数据订阅配置"),
        tags=[SWAGGER_TAG],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("查询数据订阅配置列表"),
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        # 更新每个配置的相关dumper实例
        config_ids = [data["id"] for data in resp.data["results"]]
        dumper_extra_configs = ExtraProcessInstance.objects.filter(
            proc_type=ExtraProcessType.TBINLOGDUMPER, extra_config__dumper_config_id__in=config_ids
        ).values_list("extra_config", flat=True)

        config_counter = Counter([int(extra_config["dumper_config_id"]) for extra_config in dumper_extra_configs])
        for data in resp.data["results"]:
            data["dumper_instance_count"] = config_counter.get(data["id"], 0)

        return resp

    @common_swagger_auto_schema(
        operation_summary=_("数据订阅配置详情"),
        tags=[SWAGGER_TAG],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("删除数据订阅配置"),
        tags=[SWAGGER_TAG],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("校验订阅配置是否重名"),
        query_serializer=VerifyDuplicateNamsSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=VerifyDuplicateNamsSerializer, filter_fields=None)
    def verify_duplicate_name(self, request, *args, **kwargs):
        name = self.params_validate(self.get_serializer_class())["name"]
        is_duplicate = self.queryset.filter(bk_biz_id=kwargs["bk_biz_id"], name=name).count() != 0
        return Response(is_duplicate)
