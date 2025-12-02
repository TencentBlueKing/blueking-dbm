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
from dataclasses import dataclass, field
from typing import List

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.db_meta.models import Machine
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.resource import write_recycle_hosts_into_ticket
from backend.flow.utils.base.validate_handler import ValidateHandler, validate_int, validate_list

logger = logging.getLogger("flow")


@dataclass()
class CopyAppSettingKwargs(ValidateHandler):
    """
    定义执行sqlserver_copy_app_setting活动节点的私有变量结构体
    @attributes ticket_id 单据id
    @attributes calc_host_list 待检查的host列表
    """

    ticket_id: int = field(metadata={"validate": validate_int})
    calc_host_list: List = field(metadata={"validate": validate_list})


class CalcHostIsWriteRecycleListService(BaseService):
    """
    这个一个通用的活动节点（component）
    判断传入的主机列表，单据正常执行完成之后，是否可以退回到资源池里
    判断的依据是： 主机是否还存在Machine表里面，如果不存在，则认为单据对主机进行清理干净，可以进入资源池， 反之则不能
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        calc_host_list = kwargs["calc_host_list"]
        ticket_id = kwargs["ticket_id"]
        recycle_host_list = []
        for host in calc_host_list:
            if Machine.objects.filter(ip=host["ip"], bk_cloud_id=host["bk_cloud_id"]).exists():
                self.log_info(_("机器在DBM系统的Machine【{}】表还存在，不能退回资源池处理".format(host)))
                continue
            # 不存在则说明清理干净，进入退回资源池列表
            recycle_host_list.append(host)
        if recycle_host_list:
            try:
                write_recycle_hosts_into_ticket(ticket_id=ticket_id, hosts=recycle_host_list)
                self.log_info(_("执行write_recycle_hosts_into_ticket方法成功：{}".format(recycle_host_list)))
                return True

            except Exception as err:
                self.log_error(_("执行write_recycle_hosts_into_ticket方法失败：{}").format(err))
                return False

        self.log_info(_("暂无机器回收"))
        return True


class CalcHostIsWriteRecycleListComponent(Component):
    name = __name__
    code = "common_calc_host_is_write_recycle_host_list"
    bound_service = CalcHostIsWriteRecycleListService
    kwargs = CopyAppSettingKwargs
