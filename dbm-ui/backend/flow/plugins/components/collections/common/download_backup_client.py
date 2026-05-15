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
from collections import defaultdict

from django.utils.translation import gettext_lazy as _
from pipeline.component_framework.component import Component

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType
from backend.components.mysql_backup.client import MysqlBackupApi
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class BackupClientInstaller:
    def __init__(self, bk_biz_id: int, backup_os_user: str):
        self.bk_biz_id = bk_biz_id
        self.backup_os_user = backup_os_user

    def _get_download_config(self, bk_cloud_id: int) -> dict:
        """
        获取安装backup_client获取配置

        :returns: {
        "cos_auth": {
            "bucket_name": "xxx",
            "storage_type": "cos",
            "region": "ap-guangzhou",
            "secret_id": "xxx",
            "secret_key": "xxx",
            "endpoint": "xxx",
        },
        "app_attr": { // 用不到，将来删除
            "bk_biz_id": 1,
            "bk_cloud_id": 1,
        }
        """

        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(self.bk_biz_id),
                "level_name": "bk_cloud_id",
                "level_value": str(bk_cloud_id),
                "conf_file": "cosinfo.toml",
                "conf_type": "backup_client",
                "namespace": "common",
                "format": FormatType.MAP_LEVEL,
            }
        )["content"]

        return data

    def install_one_cloud(self, bk_cloud_id: int, ip_list: list) -> bool:
        backup_config = self._get_download_config(bk_cloud_id=bk_cloud_id)

        params = {
            "host_list": [{"bk_cloud_id": bk_cloud_id, "bk_biz_id": self.bk_biz_id, "ip": ip} for ip in ip_list],
            "file_tag": "",  # not set tag by client
            "cos_info_render": {
                "auth_path": f"/home/{self.backup_os_user}/.cosinfo.toml",
                "os_user": self.backup_os_user,
                "auth_path_overwrite": True,
            },
        }
        bucket_name = backup_config["cos_auth"]["bucket_name"]
        if backup_config["cos_auth"]["storage_type"] in ["cos", "s3", "bkrepo"]:
            if bucket_name == "" or "{{" in bucket_name:
                err_msg = _("请先为 bk_biz_id={bk_biz_id},bk_cloud_id={bk_cloud_id} 设置备份 bucket 信息").format(
                    bk_biz_id=self.bk_biz_id, bk_cloud_id=bk_cloud_id
                )
                raise Exception(err_msg)
            params["cos_info"] = {
                "cos_auth": backup_config["cos_auth"],
                "app_attr": {"bk_biz_id": self.bk_biz_id, "bk_cloud_id": bk_cloud_id},
            }

        MysqlBackupApi.download_backup_client(params=params)
        return True

    def install(self, ip_list) -> bool:
        """
        安装backup_client，可外部调用
        :param ip_list: ip列表，格式为[{"ip": "127.0.0.1", "bk_cloud_id": 0 }]
        """
        # 先按 bk_cloud_id 分组
        # bk_biz_id,backup_os_user 在初始化时已经设置
        grouped_ips = defaultdict(list)
        for ip_info in ip_list:
            grouped_ips[ip_info["bk_cloud_id"]].append(ip_info["ip"])
        for bk_cloud_id, ips in grouped_ips.items():
            self.install_one_cloud(bk_cloud_id=bk_cloud_id, ip_list=ips)
        return True


class InstallBackupClientService(BaseService):
    """
    下载并安装backup_client,kwargs参数结构如下:
    kwargs:{
       "bk_cloud_id":0,
       "bk_biz_id":0,
       "ip_list": [ip,ip.ip]
    }
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        bk_biz_id = int(kwargs["bk_biz_id"])
        bk_cloud_id = int(kwargs["bk_cloud_id"])
        ip_list = kwargs["ip_list"]

        self.log_info("download and install backup_client receive ips: {}".format(ip_list))
        installer = BackupClientInstaller(bk_biz_id=bk_biz_id, backup_os_user=kwargs["backup_os_user"])
        installer.install_one_cloud(bk_cloud_id=bk_cloud_id, ip_list=ip_list)
        self.log_info(f"Download and install backup_client successfully {ip_list}")
        return True


class DownloadBackupClientComponent(Component):
    name = __name__
    code = "download_backup_client"
    bound_service = InstallBackupClientService
