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
from collections import OrderedDict

from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg.utils import swagger_auto_schema


class BothHttpAndHttpsSchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        schema.schemes = ["http", "https"]
        return schema


class ResponseSwaggerAutoSchema(SwaggerAutoSchema):
    """普通接口的Swagger响应格式"""

    def get_response_schemas(self, response_serializers):
        responses = super().get_response_schemas(response_serializers)
        new_responses = OrderedDict()
        for sc, response in responses.items():
            new_responses[sc] = openapi.Response(
                description=response.get("description", ""),
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties=OrderedDict(
                        (
                            ("code", openapi.Schema(type=openapi.TYPE_INTEGER)),
                            ("request_id", openapi.Schema(type=openapi.TYPE_STRING)),
                            ("data", response.get("schema")),
                        )
                    ),
                ),
            )
        return new_responses


class PaginatedResponseSwaggerAutoSchema(SwaggerAutoSchema):
    """分页接口的Swagger响应格式"""

    def get_response_schemas(self, response_serializers):
        responses = super().get_response_schemas(response_serializers)
        new_responses = OrderedDict()
        for sc, response in responses.items():
            new_responses[sc] = openapi.Response(
                description="",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties=OrderedDict(
                        (
                            ("code", openapi.Schema(type=openapi.TYPE_INTEGER)),
                            ("request_id", openapi.Schema(type=openapi.TYPE_STRING)),
                            (
                                "data",
                                openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties=OrderedDict(
                                        (
                                            ("count", openapi.Schema(type=openapi.TYPE_INTEGER)),
                                            ("next", openapi.Schema(type=openapi.TYPE_STRING)),
                                            ("previous", openapi.Schema(type=openapi.TYPE_STRING)),
                                            ("results", response.get("schema")),
                                        )
                                    ),
                                ),
                            ),
                        )
                    ),
                ),
            )
        return new_responses


def common_swagger_auto_schema(
    method=None,
    methods=None,
    auto_schema=None,
    request_body=None,
    query_serializer=None,
    manual_parameters=None,
    operation_id=None,
    operation_description=None,
    operation_summary=None,
    security=None,
    deprecated=None,
    responses=None,
    field_inspectors=None,
    filter_inspectors=None,
    paginator_inspectors=None,
    tags=None,
    **extra_overrides
):
    # 提供通用的 auto_schema，默认 auto_schema 为ResponseSwaggerAutoSchema
    return swagger_auto_schema(
        method=method,
        methods=methods,
        auto_schema=auto_schema or ResponseSwaggerAutoSchema,
        request_body=request_body,
        query_serializer=query_serializer,
        manual_parameters=manual_parameters,
        operation_id=operation_id,
        operation_description=operation_description,
        operation_summary=operation_summary,
        security=security,
        deprecated=deprecated,
        responses=responses,
        field_inspectors=field_inspectors,
        filter_inspectors=filter_inspectors,
        paginator_inspectors=paginator_inspectors,
        tags=tags,
        **extra_overrides
    )
