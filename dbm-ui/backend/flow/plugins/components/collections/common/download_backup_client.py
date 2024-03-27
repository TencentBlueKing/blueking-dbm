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

from pipeline.component_framework.component import Component

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType
from backend.components.mysql_backup.client import MysqlBackupApi
from backend.flow.consts import BACKUP_TAG
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class DownloadBackupClientService(BaseService):
    """
    下载并安装backup_client,kwargs参数结构如下:
    kwargs:{
       "bk_cloud_id":0,
       "bk_biz_id":0,
       "download_host_list": [ip,ip.ip]
    }
    """

    @staticmethod
    def _get_download_config(bk_biz_id: int, bk_cloud_id: int) -> dict:
        """
        获取安装backup_client获取配置
        """

        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(bk_biz_id),
                "level_name": "bk_cloud_id",
                "level_value": str(bk_cloud_id),
                "conf_file": "backup_client",
                "conf_type": "backup",
                "namespace": "tendbcomm",
                "format": FormatType.MAP_LEVEL,
            }
        )["content"]

        return data

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        backup_config = self._get_download_config(
            bk_cloud_id=int(kwargs["bk_cloud_id"]), bk_biz_id=int(kwargs["bk_biz_id"])
        )

        self.log_info("download and install backup_client receive ips: {}".format(kwargs["download_host_list"]))
        params = {
            "host_list": [
                {"bk_cloud_id": int(kwargs["bk_cloud_id"]), "bk_biz_id": int(kwargs["bk_biz_id"]), "ip": ip}
                for ip in kwargs["download_host_list"]
            ],
            "file_tag": BACKUP_TAG,
            "cos_info_render": {
                "auth_path": f"/home/{kwargs['backup_os_user']}/.cosinfo.toml",
                "os_user": kwargs["backup_os_user"],
                "auth_path_overwrite": True,
            },
            "default_storage_type": backup_config["default_storage_type"],
        }

        MysqlBackupApi.download_backup_client(params=params)
        self.log_info(f"Download and install backup_client successfully {params['host_list']}")
        return True


class DownloadBackupClientComponent(Component):
    name = __name__
    code = "download_backup_client"
    bound_service = DownloadBackupClientService
