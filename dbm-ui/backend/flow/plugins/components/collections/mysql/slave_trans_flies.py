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
import json
import logging

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileService
from backend.ticket.constants import TicketType
from backend.utils.time import compare_time

logger = logging.getLogger("flow")


class SlaveTransFileService(TransFileService):
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

        # 获取备份文件,并找出最
        backup_time = "1999-01-01T11:11:11+08:00"
        backup_file = {}
        if global_data["ticket_type"] in (TicketType.MYSQL_RESTORE_LOCAL_SLAVE.value,):
            self.log_error(_("仅在主库查找备份源"))
            self.log_error(trans_data.master_backup_file["backups"])
            backup_infos = {**trans_data.master_backup_file["backups"]}
        else:
            self.log_error(_("在主、从库查找备份源"))
            self.log_info(trans_data.master_backup_file["backups"])
            if trans_data.slave_backup_file is None:
                backup_infos = {**trans_data.master_backup_file["backups"]}
            else:
                self.log_info(trans_data.slave_backup_file["backups"])
                backup_infos = {**trans_data.master_backup_file["backups"], **trans_data.slave_backup_file["backups"]}
        self.log_info(_("从备份源中筛选符合的备份"))
        self.log_info(json.dumps(backup_infos))
        for key, value in backup_infos.items():
            value["backup_time"] = value["backup_consistent_time"]
            if str(value["data_schema_grant"]).lower() == "all" or (
                "schema" in str(value["data_schema_grant"]).lower()
                and "data" in str(value["data_schema_grant"]).lower()
            ):
                if compare_time(value["backup_time"], backup_time):
                    if compare_time(value["backup_time"], backup_time):
                        backup_time = value["backup_time"]
                        backup_file = backup_infos[key]
                        backup_file["backup_time"] = backup_file["backup_consistent_time"]
                        self.log_info(f"backup_time: {backup_time}")
        if not backup_file:
            self.log_error(_("没有符合的备份文件提供定点恢复"))
            return False

        # 构造数据
        trans_data.backupinfo = backup_file
        source_ip_list = [trans_data.backupinfo["inst_host"]]
        backup_dir = trans_data.backupinfo["backup_dir"]
        file_list = ["%s/%s" % (backup_dir, file) for file in trans_data.backupinfo["file_list"]]
        file_list.append(trans_data.backupinfo["index_file"])

        kwargs["file_list"] = file_list
        kwargs["source_ip_list"] = source_ip_list
        kwargs["backupinfo"] = trans_data.backupinfo
        # 不需要这2个参数
        # kwargs["latest_backup_file"] = trans_data.latest_backup_file
        # kwargs["backup_role"] = trans_data.backup_role

        data.outputs["kwargs"] = kwargs
        data.outputs["trans_data"] = trans_data
        return super()._execute(data, parent_data)


class SlaveTransFileComponent(Component):
    name = __name__
    code = "mysql_slave_trans_file"
    bound_service = SlaveTransFileService
