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

import copy
import logging
import shlex
import time
from collections import defaultdict
from typing import Dict, List

from django.utils.translation import gettext as _
from jinja2.sandbox import SandboxedEnvironment as Environment

from backend import env
from backend.components import JobApi
from backend.configuration.constants import DBType
from backend.core.consts import BK_PUSH_CONFIG_PAYLOAD
from backend.db_meta.models import Machine
from backend.db_proxy import nginxconf_tpl
from backend.db_proxy.constants import (
    CLEAN_DELETED_NGINX_CONF_BATCH_SIZE,
    CLEAN_DELETED_NGINX_CONF_JOB_REQUEST_INTERVAL,
    JOB_INSTANCE_EXPIRE_TIME,
    NGINX_PUSH_TARGET_PATH,
    ExtensionType,
)
from backend.db_proxy.exceptions import ProxyPassBaseException
from backend.db_proxy.models import ClusterExtension, DBCloudProxy, DBExtension
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.flow.utils.script_template import fast_execute_script_common_kwargs
from backend.utils.redis import RedisConn
from backend.utils.string import base64_encode

logger = logging.getLogger("celery")


def _get_nginx_conf_file_name(extension: ClusterExtension):
    return f"{extension.bk_biz_id}_{extension.db_type}_{extension.cluster_name}_nginx.conf"


def fill_cluster_service_nginx_conf():
    """填充集群额外服务的配置信息"""

    # 容器化场景不走job下发
    if env.CLOUD_CONTAINER_ENABLE:
        return

    def _job_push_config_file(_cloud_id, _file_list, _nginx_list):
        # 如果当前nginx的机器agent异常，则抛出日志且不下发。避免阻塞job
        nginx_ip_list = [
            {
                "bk_cloud_id": _cloud_id,
                "bk_agent_id": _nginx["bk_agent_id"],
                "bk_host_id": _nginx["bk_host_id"],
                "ip": _nginx["ip"],
                "bk_host_innerip": _nginx["ip"],
            }
            for _nginx in _nginx_list
        ]
        ResourceQueryHelper.fill_agent_status(nginx_ip_list)
        status_code = sum([nginx["status"] for nginx in nginx_ip_list])
        if status_code != len(nginx_ip_list):
            logger.error(_("nginx机器{}当前agent异常，跳过文件下发。请管理员检查机器运行状态").format(nginx_ip_list))
            return None

        job_payload = copy.deepcopy(BK_PUSH_CONFIG_PAYLOAD)
        job_payload["task_name"] = f"cloud_id({_cloud_id})_push_nginx_conf"
        job_payload["file_target_path"] = NGINX_PUSH_TARGET_PATH
        job_payload["file_list"] = _file_list
        job_payload["target_server"]["ip_list"] = nginx_ip_list
        job_payload["callback_url"] = f"{env.BK_SAAS_CALLBACK_URL}/apis/proxypass/push_conf_callback/"

        logger.info(_("nginx配置文件下发参数：{}").format(job_payload))
        _resp = JobApi.push_config_file(job_payload, raw=True, use_admin=True)
        if not _resp["result"]:
            raise ProxyPassBaseException(_("下发文件job启动失败，错误信息: {}").format(_resp["message"]))

        return _resp

    flush_extension = ClusterExtension.get_extension_by_flush(is_flush=False, is_deleted=False)
    cloud__db_type__extension: Dict[int, Dict[DBType, List[ClusterExtension]]] = defaultdict(lambda: defaultdict(list))
    # 通过cloud_id和db_type进行聚合
    for extension in flush_extension:
        cloud__db_type__extension[extension.bk_cloud_id][extension.db_type].append(extension)

    for cloud_id in cloud__db_type__extension.keys():
        # 获取下发nginx conf的机器 TODO: 后续要改为clb的地址进行转发
        try:
            proxy_external_address = DBCloudProxy.get_cloud_proxy_external_address(bk_cloud_id=cloud_id)
        except ProxyPassBaseException as e:
            logger.error(_("cloud_id: {} 获取云区域代理地址失败: {}").format(cloud_id, e))
            continue

        nginx_extensions = DBExtension.get_extension_in_cloud(bk_cloud_id=cloud_id, extension_type=ExtensionType.NGINX)
        # 获取nginx的bk_agent_id(兼容gse2.0的agent查询)
        for nginx_extension in nginx_extensions:
            if "bk_agent_id" not in nginx_extension.details:
                host_info = Machine.get_host_info_from_cmdb(bk_host_id=nginx_extension.details["bk_host_id"])
                nginx_extension.details["bk_agent_id"] = host_info.get("bk_agent_id", "")
                nginx_extension.save(update_fields=["details"])

        manage_port = nginx_extensions.first().details["manage_port"]
        file_list: List[Dict[str, str]] = []
        extension_ids: List[int] = []
        for db_type in cloud__db_type__extension[cloud_id].keys():
            conf_tpl = getattr(nginxconf_tpl, f"{db_type}_conf_tpl", None)

            # 如果没有模板，则打印日志并跳过
            if not conf_tpl:
                logger.warning(_("集群类型：{} 的nginx配置文件不存在，跳过对该nginx配置的下发").format(db_type))
                continue

            jinja_env = Environment()
            template = jinja_env.from_string(conf_tpl)

            for extension in cloud__db_type__extension[cloud_id][db_type]:
                # 渲染配置
                file_list.append(nginxconf_tpl.render_nginx_tpl(extension=extension, template=template, encode=True))
                # 这里先提前写入access url，至于是否执行成功根据is_flush
                extension.save_access_url(nginx_url=f"{proxy_external_address}:{manage_port}")
                extension_ids.append(extension.id)

        # 下发nginx服务配置
        nginx_list = [nginx.details for nginx in nginx_extensions]
        resp = _job_push_config_file(_cloud_id=cloud_id, _nginx_list=nginx_list, _file_list=file_list)
        if resp:
            # 缓存inst_id和nginx id，用于回调job，默认缓存时间和定时周期一致
            RedisConn.lpush(resp["data"]["job_instance_id"], *extension_ids, cloud_id)
            RedisConn.expire(resp["data"]["job_instance_id"], JOB_INSTANCE_EXPIRE_TIME)


def clean_deleted_cluster_service_nginx_conf():
    """清理已软删除的大数据管理端nginx子配置文件"""

    if env.CLOUD_CONTAINER_ENABLE:
        return

    deleted_extensions = list(
        ClusterExtension.objects.filter(is_deleted=True).order_by("id")[:CLEAN_DELETED_NGINX_CONF_BATCH_SIZE]
    )
    if not deleted_extensions:
        return

    cloud__extensions: Dict[int, List[ClusterExtension]] = defaultdict(list)
    for extension in deleted_extensions:
        cloud__extensions[extension.bk_cloud_id].append(extension)

    handled_count = 0
    for cloud_id, extensions in cloud__extensions.items():
        nginx_extensions = DBExtension.get_extension_in_cloud(bk_cloud_id=cloud_id, extension_type=ExtensionType.NGINX)
        if not nginx_extensions.exists():
            logger.error(_("cloud_id: {} 没有可用的nginx机器，跳过nginx配置清理").format(cloud_id))
            continue

        delete_cmds = []
        extension_ids = []
        for extension in extensions:
            conf_path = f"{NGINX_PUSH_TARGET_PATH.rstrip('/')}/{_get_nginx_conf_file_name(extension)}"
            delete_cmds.append(f"rm -f -- {shlex.quote(conf_path)}")
            extension_ids.append(extension.id)

        job_payload = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": f"cloud_id({cloud_id})_delete_nginx_conf",
            "script_content": base64_encode("\n".join(delete_cmds)),
            "script_language": 1,
            "target_server": {
                "ip_list": [
                    {"bk_cloud_id": nginx.details["bk_cloud_id"], "ip": nginx.details["ip"]}
                    for nginx in nginx_extensions
                ]
            },
            "callback_url": f"{env.BK_SAAS_CALLBACK_URL}/apis/proxypass/delete_conf_callback/",
        }
        logger.info(_("nginx子配置清理job参数: {}").format(job_payload))

        # 每次请求只处理同一云区域的数据，避免单个云区域失败影响其他云区域的清理
        resp = JobApi.fast_execute_script(
            {**fast_execute_script_common_kwargs, **job_payload}, use_admin=True, raw=True
        )
        time.sleep(CLEAN_DELETED_NGINX_CONF_JOB_REQUEST_INTERVAL)
        if not resp["result"]:
            logger.error(_("nginx子配置清理job启动失败: {}").format(resp["message"]))
            continue

        job_instance_id = resp["data"]["job_instance_id"]
        RedisConn.lpush(job_instance_id, *extension_ids)
        RedisConn.expire(job_instance_id, JOB_INSTANCE_EXPIRE_TIME)
        logger.info(
            "nginx子配置删除job启动成功，等待回调删除ClusterExtension记录， job_instance_id: %s, extension_ids: %s",
            job_instance_id,
            extension_ids,
        )
        handled_count += len(extension_ids)

    if not handled_count:
        logger.warning(_("本次没有成功启动nginx子配置清理job，结束本次清理任务"))


def inspect_cluster_service_nginx_conf():
    """巡检已下发的大数据管理端nginx子配置文件"""

    if env.CLOUD_CONTAINER_ENABLE:
        return

    flush_extensions = list(ClusterExtension.objects.filter(is_flush=True, is_deleted=False).order_by("id"))
    if not flush_extensions:
        return

    cloud__extensions: Dict[int, List[ClusterExtension]] = defaultdict(list)
    for extension in flush_extensions:
        cloud__extensions[extension.bk_cloud_id].append(extension)

    for cloud_id, extensions in cloud__extensions.items():
        nginx_extensions = DBExtension.get_extension_in_cloud(bk_cloud_id=cloud_id, extension_type=ExtensionType.NGINX)
        if not nginx_extensions.exists():
            logger.error(_("cloud_id: {} 没有可用的nginx机器，跳过nginx配置巡检").format(cloud_id))
            continue

        check_cmds = []
        for extension in extensions:
            conf_path = f"{NGINX_PUSH_TARGET_PATH.rstrip('/')}/{_get_nginx_conf_file_name(extension)}"
            check_cmds.append(f"test -f {shlex.quote(conf_path)} || echo MISSING_CLUSTER_EXTENSION_ID={extension.id}")

        for nginx_extension in nginx_extensions:
            nginx_ip = nginx_extension.details["ip"]
            nginx_bk_cloud_id = nginx_extension.details["bk_cloud_id"]
            job_payload = {
                "bk_scope_type": "biz_set",
                "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
                "task_name": f"cloud_id({cloud_id})_{nginx_ip}_inspect_nginx_conf",
                "script_content": base64_encode("\n".join(check_cmds)),
                "script_language": 1,
                "target_server": {"ip_list": [{"bk_cloud_id": nginx_bk_cloud_id, "ip": nginx_ip}]},
                "callback_url": f"{env.BK_SAAS_CALLBACK_URL}/apis/proxypass/inspect_conf_callback/",
            }
            logger.info(_("nginx子配置巡检job参数: {}").format(job_payload))
            resp = JobApi.fast_execute_script(
                {**fast_execute_script_common_kwargs, **job_payload}, use_admin=True, raw=True
            )
            time.sleep(CLEAN_DELETED_NGINX_CONF_JOB_REQUEST_INTERVAL)
            if not resp["result"]:
                logger.error(_("nginx子配置巡检job启动失败: {}").format(resp["message"]))
                continue

            job_instance_id = resp["data"]["job_instance_id"]
            RedisConn.lpush(job_instance_id, nginx_ip, nginx_bk_cloud_id)
            RedisConn.expire(job_instance_id, JOB_INSTANCE_EXPIRE_TIME)
            logger.info(
                "nginx子配置巡检job启动成功，等待回调处理巡检结果，job_instance_id: %s, bk_cloud_id: %s, ip: %s",
                job_instance_id,
                nginx_bk_cloud_id,
                nginx_ip,
            )
