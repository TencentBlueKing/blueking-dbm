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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class EsReadonlyApiInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_domain = serializers.CharField(help_text=_("ES 集群域名"))
    path = serializers.CharField(
        help_text=_(
            "ES 只读 API 相对路径，只允许 GET 类查询接口。支持："
            "/、/_license、/_remote/info；"
            "/_cat、/_cat/*，例如 /_cat/health、/_cat/indices、/_cat/nodes；"
            "/_cluster/stats、/_cluster/stats/*、/_cluster/health、/_cluster/state、"
            "/_cluster/settings、/_cluster/pending_tasks、/_cluster/allocation/explain；"
            "/_stats、/_stats/*、/{index}/_stats、/{index}/_stats/*；"
            "/_nodes、/_nodes/*，例如 /_nodes/stats、/_nodes/http；"
            "/_tasks、/_tasks/{task_id}；"
            "/_recovery、/{index}/_recovery、/_segments、/{index}/_segments；"
            "/_shard_stores、/{index}/_shard_stores；"
            "/_settings、/{index}/_settings、/_mapping、/{index}/_mapping、/_alias、/{index}/_alias。"
            "不允许传入完整 URL，不允许访问 POST/PUT/DELETE 类接口，不支持 _search/_msearch/_count/_doc/_source。"
            "ES 鉴权信息必须由 bkjob 进程环境变量 ES_USERNAME/ES_PASSWORD 提供，缺失时会直接报错；调用方无需也不能传入用户名密码。"
        )
    )
    query_params = serializers.JSONField(
        help_text=_("可选 query 参数字典。同名 key 会覆盖 path 中自带的 query string；_cat 接口未指定 format 时默认追加 format=json"),
        required=False,
        default=dict,
    )
    scheme = serializers.ChoiceField(
        choices=[("http", "http"), ("https", "https")],
        help_text=_("访问 ES 使用的协议，默认 http"),
        required=False,
        default="http",
    )
    execute_role = serializers.ChoiceField(
        choices=[
            ("auto", "自动选择 running 节点"),
            ("es_client", "Client 节点"),
            ("es_datanode_hot", "热节点"),
            ("es_datanode_cold", "冷节点"),
            ("es_master", "Master 节点"),
        ],
        help_text=_("用于下发 bkjob curl 的 ES 节点角色，默认 auto，按 client/hot/cold/master 顺序选择 running 实例"),
        required=False,
        default="auto",
    )
    timeout = serializers.IntegerField(
        help_text=_("curl 最大执行超时时间，单位秒，默认30，范围1-120"),
        required=False,
        default=30,
        min_value=1,
        max_value=120,
    )
    connect_timeout = serializers.IntegerField(
        help_text=_("curl 连接超时时间，单位秒，默认5，范围1-30"),
        required=False,
        default=5,
        min_value=1,
        max_value=30,
    )
    max_response_bytes = serializers.IntegerField(
        help_text=_("最大返回内容字节数，默认1MB，范围1024-5242880；超过会截断并标记 response_truncated=true"),
        required=False,
        default=1024 * 1024,
        min_value=1024,
        max_value=5 * 1024 * 1024,
    )

    def validate_query_params(self, value):
        # default=dict 保证 value 不为 None；
        if not isinstance(value, dict):
            raise serializers.ValidationError(_("query_params 必须是 JSON 对象"))
        return value


class EsReadonlyApiOutputSerializer(serializers.Serializer):
    error = serializers.CharField(
        help_text=_(
            "错误信息：success=False 时必定存在。涵盖场景："
            "参数校验失败、鉴权失败、集群/实例不存在、bkjob 执行异常、无法解析 bkjob 日志、"
            "curl 非 0 退出或 ES 返回非 2xx 。"
        ),
        required=False,
    )
    success = serializers.BooleanField(
        help_text=_("是否查询成功，始终返回；"),
        required=True,
    )
    cluster_domain = serializers.CharField(help_text=_("ES 集群域名"), required=False)
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=False)
    cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=False)
    method = serializers.CharField(help_text=_("固定为 GET"), required=False)
    path = serializers.CharField(help_text=_("实际请求的 ES API path"), required=False)
    query_params = serializers.JSONField(help_text=_("实际请求 query 参数"), required=False)
    request_url = serializers.CharField(help_text=_("实际在目标机器上请求的 ES URL"), required=False)
    execute_host = serializers.JSONField(help_text=_("执行 bkjob 的目标 ES 主机信息"), required=False)
    job_instance_id = serializers.IntegerField(help_text=_("bkjob 作业实例ID"), required=False)
    http_status = serializers.IntegerField(help_text=_("ES HTTP 状态码"), required=False, allow_null=True)
    curl_exit_code = serializers.IntegerField(help_text=_("curl 退出码"), required=False, allow_null=True)
    response_size = serializers.IntegerField(help_text=_("ES 原始响应大小，单位字节"), required=False)
    response_truncated = serializers.BooleanField(help_text=_("响应是否因超过 max_response_bytes 被截断"), required=False)
    data = serializers.JSONField(help_text=_("ES 响应 JSON 解析结果；非 JSON 响应时为空"), required=False, allow_null=True)
    raw_response = serializers.CharField(help_text=_("ES 原始响应文本，可能被截断"), required=False, allow_blank=True)
    stderr = serializers.CharField(help_text=_("curl 标准错误输出"), required=False, allow_blank=True)
    json_parse_error = serializers.CharField(
        help_text=_("响应 JSON 解析错误，非 JSON 响应时返回"), required=False, allow_blank=True
    )
