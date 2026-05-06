"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.utils.translation import gettext as _

from backend.flow.engine.validate.redis_base_validate import RedisBaseValidator


class RedisKeyStatFlowValidator(RedisBaseValidator):
    """
    RedisKeystatFlow类(keystat)对应的validate类
    每行校验：
    1、传入的实例是否合法
    2、传入的实例是否重复

    """

    def __call__(self):
        """
        被外部调用
        """
        error_msgs = []
        # 检查每一行的合法性. 如果合法，则返回空列表，否则返回错误信息列表
        for index, info in enumerate(self.data["infos"]):
            error_msgs.extend(self.__run_check_for_info(info, index))
        return error_msgs

    def __run_check_for_info(self, info: dict, index: int) -> list:
        """
        @param info：
        @param index： 每个元素体的编号
        info:
            immute_domain: 域名
            ins: 实例列表
        """

        too_many_keys_msg = _("key数量超过2000万，且选了多个Redis实例，这会导致分析时间过长，目前无法支持。请减少Redis实例数量。")

        cluster_key_num = 0
        cluster_domain = info["immute_domain"]
        ins_list = info["ins"]
        for ins in ins_list:
            cluster_key_num += ins["key_num"]
        if len(ins_list) > 1 and (cluster_key_num > 2000000):
            msg = _("{cluster_domain} {too_many_keys_msg}").format(
                cluster_domain=cluster_domain,
                too_many_keys_msg=too_many_keys_msg,
            )
            return [
                self.gen_error_msg(index=index, row_key=info.get("row_key", ""), field="immute_domain", errors=msg)
            ]

        return []
