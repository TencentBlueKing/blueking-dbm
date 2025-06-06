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

from django.http import JsonResponse
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_proxy.reverse_api.base_reverse_api_view import BaseReverseApiView
from backend.db_proxy.reverse_api.decorators import reverse_api
from backend.db_proxy.reverse_api.mysql.impl import list_instance_info
from backend.db_proxy.reverse_api.mysql.impl.checksum_config import checksum_config
from backend.db_proxy.reverse_api.mysql.impl.dbbackup_config import dbbackup_config
from backend.db_proxy.reverse_api.mysql.impl.expoter_config import exporter_config
from backend.db_proxy.reverse_api.mysql.impl.monitor_items_config import monitor_items_config
from backend.db_proxy.reverse_api.mysql.impl.monitor_runtime_config import monitor_runtime_config
from backend.db_proxy.reverse_api.mysql.impl.mysql_crond_config import mysql_crond_config
from backend.db_proxy.reverse_api.mysql.impl.roatebinlog_config import rotatebinlog_config

logger = logging.getLogger("root")


class MySQLReverseApiView(BaseReverseApiView):
    @common_swagger_auto_schema(operation_summary=_("获取实例基本信息"))
    @reverse_api(url_path="list_instance_info")
    def list_instance_info(self, request, *args, **kwargs):
        bk_cloud_id, ip, port_list = self.get_api_params()
        logger.info(f"bk_cloud_id: {bk_cloud_id}, ip: {ip}, port:{port_list}")
        res = list_instance_info(bk_cloud_id=bk_cloud_id, ip=ip, port_list=port_list)
        logger.info(f"instance info: {res}")
        return JsonResponse(
            {
                "result": True,
                "code": 0,
                "data": res,
                "message": "",
                "errors": None,
            }
        )

    @common_swagger_auto_schema(operation_summary=_("获取实例监控 runtime 配置"))
    @reverse_api(url_path="monitor_runtime_config")
    def monitor_runtime_config(self, request, *args, **kwargs):
        bk_cloud_id, ip, port_list = self.get_api_params()
        logger.info(f"bk_cloud_id: {bk_cloud_id}, ip: {ip}, port:{port_list}")
        res = monitor_runtime_config(bk_cloud_id=bk_cloud_id, ip=ip, port_list=port_list)
        logger.info(f"runtime config: {res}")
        return JsonResponse(
            {
                "result": True,
                "code": 0,
                "data": res,
                "message": "",
                "errors": None,
            }
        )

    @common_swagger_auto_schema(operation_summary=_("获取实例监控项配置"))
    @reverse_api(url_path="monitor_items_config")
    def monitor_items_config(self, request, *args, **kwargs):
        bk_cloud_id, ip, port_list = self.get_api_params()
        logger.info(f"bk_cloud_id: {bk_cloud_id}, ip: {ip}, port:{port_list}")
        res = monitor_items_config(bk_cloud_id=bk_cloud_id, ip=ip, port_list=port_list)
        logger.info(f"items config: {res}")
        return JsonResponse(
            {
                "result": True,
                "code": 0,
                "data": res,
                "message": "",
                "errors": None,
            }
        )

    @common_swagger_auto_schema(operation_summary=_("获取 mysql-crond 配置"))
    @reverse_api(url_path="mysql_crond_config")
    def mysql_crond_config(self, request, *args, **kwargs):
        bk_cloud_id, ip, port_list = self.get_api_params()
        logger.info(f"bk_cloud_id: {bk_cloud_id}, ip: {ip}, port:{port_list}")
        res = mysql_crond_config(bk_cloud_id=bk_cloud_id, ip=ip)
        logger.info(f"mysql-crond config: {res}")
        return JsonResponse(
            {
                "result": True,
                "code": 0,
                "data": res,
                "message": "",
                "errors": None,
            }
        )

    @common_swagger_auto_schema(operation_summary=_("获取备份配置"))
    @reverse_api(url_path="dbbackup_config")
    def dbbackup_config(self, request, *args, **kwargs):
        bk_cloud_id, ip, port_list = self.get_api_params()
        logger.info(f"bk_cloud_id: {bk_cloud_id}, ip: {ip}, port:{port_list}")
        res = dbbackup_config(bk_cloud_id=bk_cloud_id, ip=ip, port_list=port_list)
        logger.info(f"dbbackup config: {res}")
        return JsonResponse(
            {
                "result": True,
                "code": 0,
                "data": res,
                "message": "",
                "errors": None,
            }
        )

    @common_swagger_auto_schema(operation_summary=_("获取 rotatebinlog 配置"))
    @reverse_api(url_path="rotatebinlog_config")
    def rotatebinlog_config(self, request, *args, **kwargs):
        bk_cloud_id, ip, port_list = self.get_api_params()
        logger.info(f"bk_cloud_id: {bk_cloud_id}, ip: {ip}, port:{port_list}")
        res = rotatebinlog_config(bk_cloud_id=bk_cloud_id, ip=ip, port_list=port_list)
        logger.info(f"rotatebinlog config: {res}")
        return JsonResponse(
            {
                "result": True,
                "code": 0,
                "data": res,
                "message": "",
                "errors": None,
            }
        )

    @common_swagger_auto_schema(operation_summary=_("获取数据校验配置"))
    @reverse_api(url_path="checksum_config")
    def checksum_config(self, request, *args, **kwargs):
        bk_cloud_id, ip, port_list = self.get_api_params()
        logger.info(f"bk_cloud_id: {bk_cloud_id}, ip: {ip}, port:{port_list}")
        res = checksum_config(bk_cloud_id=bk_cloud_id, ip=ip, port_list=port_list)
        logger.info(f"checksum config: {res}")
        return JsonResponse(
            {
                "result": True,
                "code": 0,
                "data": res,
                "message": "",
                "errors": None,
            }
        )

    @common_swagger_auto_schema(operation_summary=_("获取 exporter 配置"))
    @reverse_api(url_path="exporter_config")
    def exporter_config(self, request, *args, **kwargs):
        bk_cloud_id, ip, port_list = self.get_api_params()
        logger.info(f"bk_cloud_id: {bk_cloud_id}, ip: {ip}, port:{port_list}")
        res = exporter_config(bk_cloud_id=bk_cloud_id, ip=ip, port_list=port_list)
        logger.info(f"exporter config: {res}")
        return JsonResponse(
            {
                "result": True,
                "code": 0,
                "data": res,
                "message": "",
                "errors": None,
            }
        )

    # @common_swagger_auto_schema(operation_summary=_("获取实例管理账号密码"))
    # @reverse_api(url_path="admin_password")
    # def admin_password(self, request, *args, **kwargs):
    #     bk_cloud_id, ip, port_list = self.get_api_params()
    #     logger.info(f"bk_cloud_id: {bk_cloud_id}, ip: {ip}, port:{port_list}")
    #     res = admin_password(bk_cloud_id=bk_cloud_id, ip=ip, port_list=port_list)
    #     logger.info(f"admin password: {res}")
    #     return JsonResponse(
    #         {
    #             "result": True,
    #             "code": 0,
    #             "data": res,
    #             "message": "",
    #             "errors": None,
    #         }
    #     )
