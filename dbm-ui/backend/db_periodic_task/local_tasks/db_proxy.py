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
import copy
import logging
from collections import defaultdict
from typing import Dict, List

from celery.schedules import crontab
from django.utils.translation import ugettext as _
from jinja2 import Environment

from backend import env
from backend.components import JobApi
from backend.configuration.constants import DBType
from backend.core.consts import BK_PUSH_CONFIG_PAYLOAD
from backend.db_meta.models import Machine
from backend.db_periodic_task.local_tasks import register_periodic_task
from backend.db_proxy import nginxconf_tpl
from backend.db_proxy.constants import JOB_INSTANCE_EXPIRE_TIME, NGINX_PUSH_TARGET_PATH, ExtensionType
from backend.db_proxy.exceptions import ProxyPassBaseException
from backend.db_proxy.models import ClusterExtension, DBCloudProxy, DBExtension
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.utils.redis import RedisConn

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(minute="*/1"))
def fill_cluster_service_nginx_conf():
    """填充集群额外服务的配置信息"""

    def _job_push_config_file(_cloud_id, _agent_id, _file_list, _nginx):
        # 如果当前nginx的机器agent异常，则抛出日志且不下发。避免阻塞job
        nginx_ip_list = [
            {
                "bk_cloud_id": _cloud_id,
                "bk_agent_id": _agent_id,
                "ip": _nginx.internal_address,
                "bk_host_innerip": _nginx.internal_address,
            }
        ]
        ResourceQueryHelper.fill_agent_status(nginx_ip_list)
        if not nginx_ip_list[0]["status"]:
            logger.error(_("nginx机器{}当前agent异常，跳过文件下发。请管理员检查机器运行状态").format(_nginx.internal_address))
            return None

        job_payload = copy.deepcopy(BK_PUSH_CONFIG_PAYLOAD)
        job_payload["task_name"] = f"cloud_id({_cloud_id})_push_nginx_conf"
        job_payload["file_target_path"] = NGINX_PUSH_TARGET_PATH
        job_payload["file_list"] = _file_list
        job_payload["target_server"]["ip_list"] = nginx_ip_list
        job_payload["callback_url"] = f"{env.BK_SAAS_CALLBACK_URL}/apis/proxypass/push_conf_callback/"

        logger.info(_("[{}] nginx配置文件下发参数：{}").format(nginx.internal_address, job_payload))
        _resp = JobApi.push_config_file(job_payload, raw=True)
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
        nginx = DBCloudProxy.objects.filter(bk_cloud_id=cloud_id).last()
        nginx_extension = DBExtension.get_latest_extension(bk_cloud_id=cloud_id, extension_type=ExtensionType.NGINX)
        # 获取nginx的bk_agent_id(兼容gse2.0的agent查询)
        if "bk_agent_id" not in nginx_extension.details:
            host_info = Machine.get_host_info_from_cmdb(bk_host_id=nginx_extension.details["bk_host_id"])
            nginx_extension.details["bk_agent_id"] = host_info.get("bk_agent_id", "")
            nginx_extension.save(update_fields=["details"])

        nginx_detail = nginx_extension.details

        file_list: List[Dict[str, str]] = []
        extension_ids: List[int] = []
        for db_type in cloud__db_type__extension[cloud_id].keys():
            conf_tpl = getattr(nginxconf_tpl, f"{db_type}_conf_tpl", None)
            if not conf_tpl:
                # 如果没有模板，则打印日志并跳过
                logger.warning(_("集群类型：{} 的nginx配置文件不存在，跳过对该nginx配置的下发").format(db_type))
                continue

            jinja_env = Environment()
            template = jinja_env.from_string(conf_tpl)

            for extension in cloud__db_type__extension[cloud_id][db_type]:
                conf_payload = {
                    "bk_biz_id": extension.bk_biz_id,
                    "bk_cloud_id": extension.bk_cloud_id,
                    "db_type": extension.db_type,
                    "cluster_name": extension.cluster_name,
                    "service_type": extension.service_type,
                    "service_url": f"http://{extension.ip}:{extension.port}",
                }
                file_name = f"{extension.bk_biz_id}_{extension.db_type}_{extension.cluster_name}_nginx.conf"
                file_content = str(base64.b64encode(template.render(conf_payload).encode("utf-8")), "utf-8")
                file_list.append({"file_name": file_name, "content": file_content})

                # 这里先提前写入access url，至于是否执行成功根据is_flush
                extension.save_access_url(nginx_url=f"{nginx.external_address}:{nginx_detail['manage_port']}")
                extension_ids.append(extension.id)

        # 下发nginx服务配置
        resp = _job_push_config_file(
            _cloud_id=cloud_id, _agent_id=nginx_detail["bk_agent_id"], _file_list=file_list, _nginx=nginx
        )
        if resp:
            # 缓存inst_id和nginx id，用于回调job，默认缓存时间和定时周期一致
            RedisConn.lpush(resp["data"]["job_instance_id"], *extension_ids, nginx.id)
            RedisConn.expire(resp["data"]["job_instance_id"], JOB_INSTANCE_EXPIRE_TIME)
