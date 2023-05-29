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

from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileService

logger = logging.getLogger("flow")


class RollBackLocalTransFileService(TransFileService):
    """
    下载介质文件包到目标机器
    """

    def _execute(self, data, parent_data) -> bool:
        """
        执行传输文件的原子任务。目前文件传输支持两个模式：1：第三方cos原文件传输 2：服务器之间文件传输
        kwargs.get('file_type') 参数用来控传输模式，如果等于1，则采用服务之间的文件传输。否则都作为第三方cos原文件传输
        """
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")
        one_cluster = kwargs.get("cluster", None)
        backup_info = one_cluster["total_backupinfo"]
        self.log_info(f"backup_info: {backup_info}")

        # 构造数据
        trans_data.latest_backup_file = backup_info["backup_id"]
        trans_data.backupinfo = backup_info
        source_ip_list = [trans_data.backupinfo["inst_host"]]
        backup_dir = trans_data.backupinfo["backup_dir"]
        file_list = ["%s/%s" % (backup_dir, file) for file in trans_data.backupinfo["file_list"]]
        file_list.append(trans_data.backupinfo["index_file"])
        # 修改传输文件
        kwargs["file_list"] = file_list
        kwargs["source_ip_list"] = source_ip_list
        kwargs["backupinfo"] = trans_data.backupinfo
        kwargs["latest_backup_file"] = trans_data.latest_backup_file
        kwargs["backup_role"] = trans_data.backup_role

        data.outputs["kwargs"] = kwargs
        data.outputs["trans_data"] = trans_data

        return super()._execute(data, parent_data)


class RollBackLocalTransFileComponent(Component):
    name = __name__
    code = "mysql_rollback_local_trans_file"
    bound_service = RollBackLocalTransFileService
