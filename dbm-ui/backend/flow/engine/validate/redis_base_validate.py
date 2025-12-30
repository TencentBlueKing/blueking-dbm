"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from collections import defaultdict

from django.utils.translation import gettext as _

from backend.flow.engine.validate.base_validate import BaseValidator, validator_log_format
from backend.flow.engine.validate.exceptions import TicketDataException
from backend.flow.utils.redis.redis_util import version_ge


class RedisBaseValidator(BaseValidator):
    """
    redis相关架构的通用基础校验类
    """

    @classmethod
    @validator_log_format
    def check_version_allow(cls, version_list: list, target_version: str):
        """
        检查version_list中的版本是否允许变更到目标版本
        只允许从低版本到高版本
        """
        err_msg = ""
        for version in version_list:
            if not version_ge(target_version, version):
                err_msg += _("存在源版本{} 大于 目标版本{} \n".format(version, target_version))
        return err_msg

    def gen_error_msg(self, field, index, row_key, errors: str):
        """
        @param field: 字段名
        @param index: 索引
        @param row_key: 行键
        @param errors: 错误信息
        @return:
        """
        return {
            "field": field,
            "index": index,
            "row_key": row_key,
            "errors": errors,
        }

    def pre_check_duplicate_cluster_ids(self, check_cluster_ids_field_name: str):
        """
        检验是否有存在重复的ip信息，如果有则记录异常
        因为SaaS传给所有flow的ip信息都是固定格式，故可以做通用处理
        @param check_cluster_ids_field_name: 在info结构体获取ip的key名称
        """
        cluster_id_counts = defaultdict(int)
        for info in self.data["infos"]:
            if isinstance(info[check_cluster_ids_field_name], list):
                for c_id in info[check_cluster_ids_field_name]:
                    cluster_id_counts[c_id] += 1
            elif isinstance(info[check_cluster_ids_field_name], int):
                cluster_id_counts[info[check_cluster_ids_field_name]] += 1

            else:
                # 不是传入通用的ip表达方式，无法计算，退出异常
                raise TicketDataException(
                    f"run [pre_check_duplicate_cluster_ids] failed: No such type checking is supported:"
                    f"{info[check_cluster_ids_field_name]}"
                )

        # 找出统计数大于1的ip数量
        err_msg = ""
        for cluster_id, count in cluster_id_counts.items():
            if count > 1:
                err_msg += _("在单据中，存在重复集群ID信息填入 [{}]，请检查 \n".format(cluster_id))

        return err_msg
