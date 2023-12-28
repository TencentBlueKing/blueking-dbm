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

import base64
import json
import logging

from django.utils.translation import ugettext as _
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
        logger.info(f"request data: {request.data}")
        # job传递过来的参数是包裹在key中的一堆字符串，T_T... TODO: 后续他们说会改为json格式
        validated_data = json.loads(list(dict(request.data).keys())[0])
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
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": "restart_nginx",
            "script_content": str(base64.b64encode(restart_nginx_tpl.encode("utf-8")), "utf-8"),
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
        validated_data = json.loads(list(dict(request.data).keys())[0])
        job_inst_id = validated_data["job_instance_id"]
        if validated_data["status"] not in SUCCESS_LIST:
            logger.error(_("[{}]nginx重启失败，请前往作业平台查看详情").format(job_inst_id))
        else:
            logger.info(_("[{}]nginx重启成功").format(job_inst_id))

        return Response()
