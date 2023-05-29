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
import logging.config
from dataclasses import asdict
from typing import Dict

from django.utils.translation import ugettext as _

from backend.db_meta.enums.cluster_type import ClusterType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.redis.common.exceptions import TendisGetBinlogFailedException
from backend.flow.plugins.components.collections.redis.redis_download_backup_files import (
    RedisDownloadBackupfileComponent,
)
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.redis.redis_context_dataclass import DownloadBackupFileKwargs

logger = logging.getLogger("flow")


def redis_backupfile_download(root_id: str, ticket_data: dict, cluster_info: dict, param: Dict) -> SubBuilder:
    """
    redis  指定时间拉取远程备份文件用于后续的数据构造
    @param root_id: flow 流程root_id
    @param ticket_data: 关联单据 ticket对象
    @param cluster_info: 关联的cluster对象
    """

    sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(ticket_data))
    redis_os_account = PayloadHandler.redis_get_os_account()
    logger.info("+==redis_backupfile_download download_kwargs redis_os_account:{} +++ ".format(redis_os_account))

    # 全备份文件下载
    task_ids = [file_info["task_id"] for file_info in param["full_file_list"]]
    download_kwargs = DownloadBackupFileKwargs(
        bk_cloud_id=cluster_info["bk_cloud_id"],
        task_ids=task_ids,
        dest_ip=param["new_temp_ip"],
        dest_dir=param["dest_dir"],
        reason="redis data structure full backup file download",
        login_user=redis_os_account["os_user"],
        login_passwd=redis_os_account["os_password"],
    )
    logger.info("+==redis_backupfile_download download_kwargs download_kwargs:{} +++ ".format(download_kwargs))
    sub_pipeline.add_act(
        act_name=_("下载{}全备文件到{}").format(param["source_ip"], param["new_temp_ip"]),
        act_component_code=RedisDownloadBackupfileComponent.code,
        kwargs=asdict(download_kwargs),
    )

    # cache类型的情况，只有全备份文件,ssd和tendisplus 必须有binlog文件
    if param["tendis_type"] in [ClusterType.TendisplusInstance.value, ClusterType.TendisSSDInstance.value]:

        if len(param["binlog_file_list"]) == 0:
            raise TendisGetBinlogFailedException(
                message=_("集群类型为:{},但是下载的binlog备份信息为0，不符合预期，最少有2个binlog".format(param["tendis_type"]))
            )
        # binlog文件下载
        task_ids = [file_info["task_id"] for file_info in param["binlog_file_list"]]
        download_kwargs = DownloadBackupFileKwargs(
            bk_cloud_id=cluster_info["bk_cloud_id"],
            task_ids=task_ids,
            dest_ip=param["new_temp_ip"],
            dest_dir=param["dest_dir"],
            reason="redis data structure binlog backup file download",
            login_user=redis_os_account["os_user"],
            login_passwd=redis_os_account["os_password"],
        )
        logger.info("+==redis_backupfile_download download_kwargs download_kwargs:{} +++ ".format(download_kwargs))
        sub_pipeline.add_act(
            act_name=_("下载{}binlog文件到{}").format(param["source_ip"], param["new_temp_ip"]),
            act_component_code=RedisDownloadBackupfileComponent.code,
            kwargs=asdict(download_kwargs),
        )

    return sub_pipeline.build_sub_process(sub_name=_("下载备份文件到{}".format(param["new_temp_ip"])))
