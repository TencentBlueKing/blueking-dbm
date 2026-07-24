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
import os
from dataclasses import dataclass

from django.conf import settings
from django.utils.translation import gettext as _

from backend.core.encrypt.handlers import AsymmetricCipherConfigType, AsymmetricHandler
from backend.flow.consts import MONGODB_DATA_EXPORT_PATH, MongoDBActuatorActionEnum
from backend.flow.engine.bamboo.scene.common.atom_jobs.set_dns_sub_job import set_dns_atom_job
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mongodb.sub_task.base_subtask import BaseSubTask
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job2 import ExecJobComponent2
from backend.flow.utils.base.bkrepo import get_bk_repo_url
from backend.flow.utils.common_act_dataclass import DNSContext
from backend.flow.utils.mongodb.mongodb_dataclass import CommonContext
from backend.flow.utils.mongodb.mongodb_repo import MongoDBCluster, MongoDBNsFilter, MongoNode, MongoNodeWithLabel
from backend.flow.utils.mongodb.mongodb_util import MongoUtil
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs as RedisActKwargs

logger = logging.getLogger("flow")


@dataclass
class ExportConfig:
    """Configuration for MongoDB data export operations."""

    access_node: MongoNode  # Selected node of MongoDB for access
    export_center_ip: str  # A machine to execute the exporting task
    ns_filter: dict
    export_options: dict
    filename: str
    file_path: str  # Execute path of act, e.g. /data
    pkg_name: str  # mongo-linux-xxx


class DataExportSubTask(BaseSubTask):
    """
    MongoDB数据导出子任务
    """

    @classmethod
    def make_kwargs(cls, cluster: MongoDBCluster, config: ExportConfig) -> dict:
        """
        Create kwargs for the MongoDB data export actuator job.
        """
        node: MongoNode = config.access_node
        bk_dbm_instance = MongoNodeWithLabel.from_node(node, clu=cluster)
        dba_user, dba_pwd = MongoUtil().get_dba_user_password(node.ip, node.port, node.bk_cloud_id)
        is_partial = MongoDBNsFilter.is_partial(config.ns_filter)
        is_dumping = config.export_options["format"] == "bson"
        sudo_account = MongoUtil().get_mongodb_os_conf()["user"]
        db_cloud_token = AsymmetricHandler.encrypt(
            name=AsymmetricCipherConfigType.PROXYPASS, content=f"{node.bk_cloud_id}_dbactuator_token"
        )

        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": node.bk_cloud_id,
            "exec_ip": config.export_center_ip,
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.DataExport,
                "file_path": config.file_path,
                "exec_account": "root",
                "sudo_account": sudo_account,
                "payload": {
                    "bk_dbm_instance": bk_dbm_instance.__json__(),
                    "ip": node.ip,
                    "port": int(node.port),
                    "adminUsername": dba_user,
                    "adminPassword": dba_pwd,
                    "args": {
                        "is_dumping": is_dumping,
                        "is_partial": is_partial,
                        "ns_filter": config.ns_filter,
                        "query": config.export_options.get("query"),
                        "fields": config.export_options.get("fields"),
                        "format": config.export_options.get("format"),
                    },
                    "upload_detail": {
                        "bk_cloud_id": node.bk_cloud_id,
                        "db_cloud_token": db_cloud_token,
                        "fileserver": {
                            "url": get_bk_repo_url(node.bk_cloud_id),
                            "bucket": settings.BKREPO_BUCKET,
                            "username": settings.BKREPO_USERNAME,
                            "password": settings.BKREPO_PASSWORD,
                            "project": settings.BKREPO_PROJECT,
                            "upload_path": MONGODB_DATA_EXPORT_PATH.format(biz=cluster.bk_biz_id),
                        },
                    },
                    "filename": config.filename,
                    "package_path": os.path.join(config.file_path, "install", config.pkg_name),
                },
            },
        }

    @classmethod
    def export_cluster_sub_flow(cls, root_id, data, cluster: MongoDBCluster, task_info: dict, file_path: str):
        """
        Create a cluster export sub flow.
        """
        builder = SubBuilder(root_id=root_id, data=data)
        config = ExportConfig(
            access_node=task_info["access_node"],
            export_center_ip=task_info["export_center_ip"],
            ns_filter=task_info["ns_filter"],
            export_options=task_info["export_options"],
            filename=task_info["filename"],
            file_path=file_path,
            pkg_name=task_info["mongodb_package_name"],
        )

        # 导出中心配置 DNS，保证能解析制品库域名；上传失败时可重试本节点
        redis_actkwargs = RedisActKwargs()
        redis_actkwargs.cluster = {}
        redis_actkwargs.set_trans_data_dataclass = DNSContext.__name__
        redis_actkwargs.is_update_trans_data = True
        redis_actkwargs.bk_cloud_id = cluster.bk_cloud_id
        dns_param = {
            "force": True,
            "ip": config.export_center_ip,
            "bk_biz_id": str(cluster.bk_biz_id),
            "bk_cloud_id": str(cluster.bk_cloud_id),
            # DNS DBExtension 常按城市匹配；空 region 时用 default
            "bk_city": cluster.region or "default",
        }
        builder.add_sub_pipeline(
            set_dns_atom_job(
                root_id=root_id,
                ticket_data=data,
                act_kwargs=redis_actkwargs,
                param=dns_param,
            )
        )

        kwargs = cls.make_kwargs(cluster, config)
        builder.add_act(
            act_name=_("访问节点： {}".format(config.access_node.addr())),
            act_component_code=ExecJobComponent2.code,
            kwargs=kwargs,
            retryable=True,
        )
        return builder.build_sub_process(_("{}-数据导出".format(cluster.immute_domain)))
