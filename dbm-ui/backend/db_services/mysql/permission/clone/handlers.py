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
import re
from typing import Any, Dict, Iterable, List

from django.core.cache import cache
from django.http.response import HttpResponse
from django.utils.translation import ugettext_lazy as _

from backend import env
from backend.components.mysql_priv_manager.client import MySQLPrivManagerApi
from backend.db_services.dbbase.instances.handlers import InstanceHandler
from backend.db_services.mysql.permission.clone.dataclass import CloneMeta
from backend.db_services.mysql.permission.clone.models import MySQLPermissionCloneRecord
from backend.db_services.mysql.permission.constants import (
    CLONE_DATA_EXPIRE_TIME,
    CLONE_EXCEL_ERROR_HEADER_MAP,
    CLONE_EXCEL_STYLE_HEADER_MAP,
    CloneType,
)
from backend.utils.cache import data_cache
from backend.utils.excel import ExcelHandler


class CloneHandler(object):
    """
    封装权限克隆相关的处理操作
    """

    def __init__(self, bk_biz_id: int, operator: str, clone_type: str, context: Dict = None):
        """
        :param bk_biz_id: 业务ID
        :param context: 上下文数据
        """

        self.bk_biz_id = bk_biz_id
        self.clone_type = clone_type
        self.context = context
        self.operator = operator

    def get_address__machine_map(self, clone_instance_list):
        """根据克隆数据得到address/ip_port与机器信息的字典关系"""
        # 如果不存在相应的数据和键，则直接返回
        if not clone_instance_list or "source" not in clone_instance_list[0]:
            return None

        address_list = []
        for clone_data in clone_instance_list:
            address_list.extend([clone_data["source"], clone_data["target"]])

        address__machine_map = InstanceHandler(self.bk_biz_id).get_machine_by_instances(address_list)
        return address__machine_map

    def _get_client_check_records(self, clone_data_list):
        clone_priv_records = [
            {
                "source_ip": data["source"],
                "target_ip": data["target"],
                "bk_cloud_id": data["bk_cloud_id"],
            }
            for data in clone_data_list
        ]
        return clone_priv_records

    def _get_instance_check_records(self, clone_data_list):
        address__machine_map = self.get_address__machine_map(clone_data_list)
        clone_priv_records = [
            {
                "source": {
                    "address": data["source"],
                    "machine_type": address__machine_map[data["source"]].machine_type,
                },
                "target": {
                    "address": data["target"],
                    "machine_type": address__machine_map[data["target"]].machine_type,
                },
                "bk_cloud_id": data["bk_cloud_id"],
            }
            for data in clone_data_list
        ]
        return clone_priv_records

    def pre_check_clone(self, clone: CloneMeta) -> Dict:
        """
        - 实例间权限克隆前置检查
        :param clone: 实例间权限克隆元数据
        """

        # 前置校验参数字段名格式化
        pre_check, message = True, "ok"
        if self.clone_type == CloneType.CLIENT:
            clone_priv_records = self._get_client_check_records(clone.clone_list)
        else:
            clone_priv_records = self._get_instance_check_records(clone.clone_list)

        # 对克隆参数进行前置校验
        clone_api_field = f"pre_check_clone_{self.clone_type}"
        clone_priv_records_field = f"clone_{self.clone_type}_priv_records"
        params = {"bk_biz_id": self.bk_biz_id, clone_priv_records_field: clone_priv_records}
        try:
            raw_resp = getattr(MySQLPrivManagerApi, clone_api_field)(params=params, raw=True)
            if raw_resp["message"]:
                # 捕获接口返回结果异常，更新克隆权限错误信息
                pre_check, message = False, raw_resp["message"]
                error_pattern = re.compile(r"line ([0-9]+):(.*)")
                error_msg_list = error_pattern.findall(message)
                for err_index, err_msg in error_msg_list:
                    clone.clone_list[int(err_index) - 1].update({"message": err_msg})

        except Exception as e:  # pylint: disable=broad-except
            # 捕获接口其他未知异常
            pre_check, message = False, _("「接口调用异常」{}").format(e)
            for clone_data in clone.clone_list:
                clone_data.update({"message": message})

        clone_uid = data_cache(key=None, data=clone.clone_list, cache_time=CLONE_DATA_EXPIRE_TIME)

        return {
            "pre_check": pre_check,
            "message": message,
            "clone_uid": clone_uid,
            "clone_data_list": clone.clone_list,
        }

    def pre_check_excel_clone(self, clone: CloneMeta) -> Dict:
        """
        - 实例间权限克隆excel前置检查(搁置，目前可用批量授权替换excel导入)
        :param clone: 实例间权限克隆元数据
        """

        clone_list = clone.clone_list
        clone.__post_init__()

        clone_keys = ["source", "target", "bk_cloud_id"]
        for index, clone_data in enumerate(clone_list):
            clone_list[index] = dict(zip(clone_keys, clone_data.values()))

        result = self.pre_check_clone(clone)
        excel_url = (
            f"{env.BK_SAAS_HOST}/apis/mysql/bizs/{self.bk_biz_id}/permission/clone"
            f"/get_clone_info_excel/?clone_uid={result['clone_uid']}&clone_type={self.clone_type}"
        )

        return {"pre_check": result["pre_check"], "excel_url": excel_url, "clone_uid": result["clone_uid"]}

    def get_clone_info_excel(self, clone: CloneMeta) -> HttpResponse:
        """
        根据id获取克隆信息的excel文件 (只会同时存在一种类型的id)
        - ticket_id: 获取授权克隆执行的excel文件
        - clone_uid: 获取授权克隆前置检查的excel文件
        """

        excel_data_dict__list: List[Dict[str, Any]] = []
        clone_data_iterator: Iterable = []
        excel_name = ""

        # 根据id类型获取授权信息的迭代数据
        if clone.ticket_id:
            excel_name = "clone_errors.xlsx"
            clone_data_iterator = MySQLPermissionCloneRecord.get_clone_records_by_ticket(
                clone.ticket_id, self.clone_type
            )
        if clone.clone_uid:
            excel_name = "pre_check_clone_errors.xlsx"
            clone_data_iterator = cache.get(clone.clone_uid)

        # 将克隆数据转换为excel序列化数据
        for clone_data in clone_data_iterator:
            if self.clone_type == CloneType.CLIENT and clone.clone_uid:
                clone_data["target"] = "\n".join(clone_data["target"])

            excel_data_dict__list.append(dict(zip(CLONE_EXCEL_ERROR_HEADER_MAP[self.clone_type], clone_data.values())))

        # 生成excel文件并返回
        wb = ExcelHandler.serialize(
            data_dict__list=excel_data_dict__list,
            header=CLONE_EXCEL_ERROR_HEADER_MAP[self.clone_type],
            header_style=CLONE_EXCEL_STYLE_HEADER_MAP[self.clone_type],
        )
        return ExcelHandler.response(wb, excel_name)
