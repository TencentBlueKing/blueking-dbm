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

import logging

from django.utils.translation import gettext as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend import env
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components import JobApi
from backend.db_proxy.constants import SWAGGER_TAG, ExtensionType
from backend.db_proxy.exceptions import ProxyPassBaseException
from backend.db_proxy.models import ClusterExtension, DBExtension
from backend.db_proxy.nginxconf_tpl import restart_nginx_tpl
from backend.db_proxy.views.job_callback.serialiers import JobCallBackSerializer
from backend.db_proxy.views.views import BaseProxyPassViewSet
from backend.flow.consts import SUCCESS_LIST
from backend.flow.utils.script_template import fast_execute_script_common_kwargs
from backend.utils.redis import RedisConn
from backend.utils.string import base64_encode

logger = logging.getLogger("root")


class JobCallBackViewSet(BaseProxyPassViewSet):
    """专门用于nginx文件下发回调的视图"""

    def get_permissions(self):
        # job回调无需鉴权
        return []

    @common_swagger_auto_schema(
        operation_summary=_("nginx文件下发job回调视图"),
        request_body=JobCallBackSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=JobCallBackSerializer, url_path="push_conf_callback")
    def push_conf_callback(self, request):
        logger.info(f"nginx push job callback: {request.data}")

        validated_data = self.params_validate(self.get_serializer_class())
        job_inst_id = validated_data["job_instance_id"]
        if validated_data["status"] not in SUCCESS_LIST:
            logger.error(_("[{}]nginx配置文件下发失败").format(job_inst_id))
            return Response()

        logger.info(_("[{}]nginx配置文件下发成功").format(job_inst_id))

        cache_ids = RedisConn.lrange(job_inst_id, 0, -1)
        if not cache_ids:
            logger.error(_("[{}]nginx文件下发job信息缓存已过期，请考虑是否下发时间过长").format(job_inst_id))
            return Response()

        bk_cloud_id, extension_ids = cache_ids[0], cache_ids[1:]
        # 更新extension表的状态
        nginx_extensions = DBExtension.get_extension_in_cloud(
            bk_cloud_id=bk_cloud_id, extension_type=ExtensionType.NGINX
        )
        ClusterExtension.objects.filter(id__in=extension_ids).update(is_flush=True)

        # 重启nginx进程
        job_payload = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": "restart_nginx",
            "script_content": base64_encode(restart_nginx_tpl),
            "script_language": 1,
            "target_server": {
                "ip_list": [
                    {"bk_cloud_id": nginx.details["bk_cloud_id"], "ip": nginx.details["ip"]}
                    for nginx in nginx_extensions
                ]
            },
            # 因为证书原因，让job请求http的地址
            "callback_url": f"{env.BK_SAAS_CALLBACK_URL}/apis/proxypass/restart_callback/",
        }
        logger.info(_("nginx重启参数：{}").format(job_payload))
        resp = JobApi.fast_execute_script(
            {**fast_execute_script_common_kwargs, **job_payload}, use_admin=True, raw=True
        )
        if not resp["result"]:
            raise ProxyPassBaseException(_("nginx重启失败，错误信息: {}").format(resp["message"]))

        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("nginx重启job回调视图"),
        request_body=JobCallBackSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=JobCallBackSerializer, url_path="restart_callback")
    def restart_callback(self, request):
        logger.info(f"nginx reload job callback: {request.data}")

        validated_data = self.params_validate(self.get_serializer_class())
        job_inst_id = validated_data["job_instance_id"]
        if validated_data["status"] not in SUCCESS_LIST:
            logger.error(_("[{}]nginx重启失败，请前往作业平台查看详情").format(job_inst_id))
        else:
            logger.info(_("[{}]nginx重启成功").format(job_inst_id))

        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("nginx配置文件删除job回调视图"),
        request_body=JobCallBackSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=JobCallBackSerializer, url_path="delete_conf_callback")
    def delete_conf_callback(self, request):
        logger.info(f"nginx delete conf job callback: {request.data}")

        validated_data = self.params_validate(self.get_serializer_class())
        job_inst_id = validated_data["job_instance_id"]
        if validated_data["status"] not in SUCCESS_LIST:
            logger.error(_("[{}]nginx配置文件删除失败，保留DB记录等待下次重试").format(job_inst_id))
            return Response()

        extension_ids = RedisConn.lrange(job_inst_id, 0, -1)
        if not extension_ids:
            logger.error(_("[{}]nginx配置文件删除job信息缓存已过期，请考虑是否删除时间过长").format(job_inst_id))
            return Response()

        deleted_count, __ = ClusterExtension.objects.filter(id__in=extension_ids, is_deleted=True).delete()
        RedisConn.delete(job_inst_id)
        logger.info(_("[{}]nginx配置文件删除成功，已删除{}条DB记录").format(job_inst_id, deleted_count))

        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("nginx配置文件巡检job回调视图"),
        request_body=JobCallBackSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=JobCallBackSerializer, url_path="inspect_conf_callback")
    def inspect_conf_callback(self, request):
        logger.info(f"nginx inspect conf job callback: {request.data}")

        validated_data = self.params_validate(self.get_serializer_class())
        job_inst_id = validated_data["job_instance_id"]
        if validated_data["status"] not in SUCCESS_LIST:
            logger.error(_("[{}]nginx子配置巡检失败，跳过本次巡检结果").format(job_inst_id))
            return Response()

        cache_infos = RedisConn.lrange(job_inst_id, 0, -1)
        if len(cache_infos) < 2:
            logger.error(_("[{}]nginx子配置巡检job信息缓存已过期，请考虑是否巡检时间过长").format(job_inst_id))
            return Response()

        bk_cloud_id, nginx_ip = cache_infos[0], cache_infos[1]
        step_instance_id = self._get_job_step_instance_id(job_inst_id)
        if not step_instance_id:
            return Response()

        log_content = self._get_job_ip_log(
            job_instance_id=job_inst_id,
            step_instance_id=step_instance_id,
            bk_cloud_id=bk_cloud_id,
            ip=nginx_ip,
        )
        missing_extension_ids = self._parse_missing_cluster_extension_ids(log_content)
        if not missing_extension_ids:
            RedisConn.delete(job_inst_id)
            logger.info(_("[{}]nginx子配置巡检未发现缺失配置文件").format(job_inst_id))
            return Response()

        updated_count = ClusterExtension.objects.filter(
            id__in=missing_extension_ids, is_flush=True, is_deleted=False
        ).update(is_flush=False)
        RedisConn.delete(job_inst_id)
        logger.info(_("[{}]nginx子配置巡检发现{}条记录缺失配置文件，已更新为待下发").format(job_inst_id, updated_count))

        return Response()

    def _get_job_step_instance_id(self, job_instance_id):
        status_payload = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "job_instance_id": job_instance_id,
            "return_ip_result": True,
        }
        resp = JobApi.get_job_instance_status(status_payload, raw=True)
        if not resp.get("result") or not resp.get("data") or not resp["data"].get("step_instance_list"):
            logger.error(_("获取job步骤实例失败，job_instance_id: {}, resp: {}").format(job_instance_id, resp))
            return None

        return resp["data"]["step_instance_list"][0]["step_instance_id"]

    def _get_job_ip_log(self, job_instance_id, step_instance_id, bk_cloud_id, ip):
        log_payload = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "job_instance_id": job_instance_id,
            "step_instance_id": step_instance_id,
            "bk_cloud_id": bk_cloud_id,
            "ip": ip,
        }
        resp = JobApi.get_job_instance_ip_log(log_payload, raw=True)
        if not resp.get("result"):
            logger.error(_("获取job执行日志失败，job_instance_id: {}, resp: {}").format(job_instance_id, resp))
            return ""

        return resp.get("data", {}).get("log_content", "")

    def _parse_missing_cluster_extension_ids(self, log_content):
        missing_extension_ids = []
        for line in log_content.splitlines():
            if not line.startswith("MISSING_CLUSTER_EXTENSION_ID="):
                continue
            try:
                missing_extension_ids.append(int(line.split("=", 1)[1]))
            except (TypeError, ValueError):
                logger.warning(_("解析缺失nginx子配置记录失败，日志行: {}").format(line))

        return missing_extension_ids
