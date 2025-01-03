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

from django.utils.translation import gettext as _

# 待审批，待确认，待补货通知模板
TODO_TEMPLATE = _(
    """\
    申请人:  {{creator}}
    申请时间: {{submit_time}}
    业务: {{biz_name}}
    域名: {{cluster_domains}}
    备注: {{remark}}
    当前处理人:  {{operators}}
    查看详情: {{detail_address}}\
    """
)

# 成功通知模板
FINISHED_TEMPLATE = _(
    """\
    申请人:  {{creator}}
    申请时间: {{submit_time}}
    业务: {{biz_name}}
    域名: {{cluster_domains}}
    完成时间: {{update_time}}
    查看详情: {{detail_address}}\
    """
)

# 失败通知模板
FAILED_TEMPLATE = _(
    """\
    申请人:  {{creator}}
    申请时间: {{submit_time}}
    业务: {{biz_name}}
    域名: {{cluster_domains}}
    失败时间: {{update_time}}
    当前当前处理人:  {{operators}}
    查看详情: {{detail_address}}\
    """
)

# 终止通知模板
TERMINATE_TEMPLATE = _(
    """\
    申请人:  {{creator}}
    申请时间: {{submit_time}}
    业务: {{biz_name}}
    域名: {{cluster_domains}}
    终止时间: {{update_time}}
    终止原因:  {{terminate_reason}}
    查看详情: {{detail_address}}\
    """
)
