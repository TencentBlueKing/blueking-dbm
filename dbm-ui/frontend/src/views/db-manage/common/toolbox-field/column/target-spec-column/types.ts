/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */

export interface TargetSpecItem {
  /** 该角色主机数 */
  count: number;
  /** 角色展示名，如 Proxy、Backend、orhan、Spider Master、Remote */
  role: string;
  /** 角色下存在多种规格时展示的源现状 */
  sourceSpecs?: {
    count: number;
    name: string;
  }[];
  /** 将申领规格的规格名，取不到时为空 */
  specName: string;
}
