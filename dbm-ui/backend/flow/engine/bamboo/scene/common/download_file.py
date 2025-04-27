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
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend import env
from backend.configuration.constants import DBType
from backend.core.consts import BK_PKG_INSTALL_PATH
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.initiative_download_file import InitiativeDownloadFileComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, InitiativeDownloadFileKwargs

logger = logging.getLogger("flow")


class DownloadFileFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def download_file_flow(self):
        """
        下载指定文件到机器上
        """
        pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        print(self.data["files"])
        for file in self.data["files"]:
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            sub_pipeline.add_act(
                act_name=_("下发文件"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=file["bk_cloud_id"],
                        exec_ip=file["ip"],
                        file_target_path=os.path.join(BK_PKG_INSTALL_PATH, "partition"),
                        file_list=GetFileList(db_type=DBType.MySQL).mysql_import_sqlfile(
                            path=self.data["path"], filelist=[file["file_name"]]
                        ),
                    )
                ),
            )
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("ip[{}]下载文件").format(file["ip"])))
        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        logger.info(_("构建下载文件流程成功"))
        pipeline.run_pipeline()


def add_db_actuator_download_act(act_lists: list, bk_cloud_id: int, dest_ip_list: list):
    """
    Add db-actuator download action to act_lists based on initiative download setting

    Args:
        act_lists: List to store action dictionaries
        bk_cloud_id: Cloud area ID
        dest_ip_list: Target IP list
    """
    if env.INITIATIVE_DOWNLOAD:
        file_url, md5sum = GetFileList().get_db_actuator_download_info()
        act_lists.append(
            {
                "act_name": _("主动下载db-actuator介质]"),
                "act_component_code": InitiativeDownloadFileComponent.code,
                "kwargs": asdict(
                    InitiativeDownloadFileKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=dest_ip_list,
                        file_url=file_url,
                        md5sum=md5sum,
                    )
                ),
            }
        )
    else:
        act_lists.append(
            {
                "act_name": _("下发db-actuator介质[云区域ID: {}]".format(bk_cloud_id)),
                "act_component_code": TransFileComponent.code,
                "kwargs": asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=dest_ip_list,
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            }
        )


def add_db_actuator_download_to_pipeline(pipeline: Builder, bk_cloud_id: int, exec_ip: str) -> None:
    """
    Add db-actuator download action to pipeline based on initiative download setting

    Args:
        pipeline: Pipeline builder object
        bk_cloud_id: Cloud area ID
        exec_ip: Target IP
    """
    if env.INITIATIVE_DOWNLOAD:
        file_url, md5sum = GetFileList().get_db_actuator_download_info()
        pipeline.add_act(
            act_name=_("主动下载db-actuator介质"),
            act_component_code=InitiativeDownloadFileComponent.code,
            kwargs=asdict(
                InitiativeDownloadFileKwargs(
                    bk_cloud_id=bk_cloud_id,
                    exec_ip=exec_ip,
                    file_url=file_url,
                    md5sum=md5sum,
                )
            ),
        )
    else:
        pipeline.add_act(
            act_name=_("下发db-actuator介质[云区域ID:{}]".format(bk_cloud_id)),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=bk_cloud_id,
                    exec_ip=exec_ip,
                    file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                )
            ),
        )
