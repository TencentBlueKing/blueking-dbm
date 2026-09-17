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

# 可用区全部，DBM 侧与海磊侧取值统一为 "all"：
# 1) subzone 传该值，表示不限定园区，由海磊跨园区调度分配资源
#    （海磊侧对应「可用区：全部 + 资源分布式方式：分 Campus（Camplus）生产」）
# 2) 提单时 spec.zones 传 [该值]，表示可用区全部
SUBZONE_ALL = "all"

# 海磊资源分布式方式（res_assign）取值：2 = 分 Campus（Camplus）生产
RES_ASSIGN_SPLIT_CAMPUS = 2

# 海磊反亲和级别（anti_affinity_level）取值：ANTI_CAMPUS = 分 Campus（Camplus）生产（跨 Campus 打散）
ANTI_AFFINITY_LEVEL_ANTI_CAMPUS = "ANTI_CAMPUS"
