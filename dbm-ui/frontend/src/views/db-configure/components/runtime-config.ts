/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */

// 前端展示模型，一致性结论只消费后台 flag_difference。
export type RuntimeComparison = 'consistent' | 'inconsistent' | 'unknown';

export interface RuntimeInstance {
  address: string;
  comparison: RuntimeComparison;
  fetchedAt: string | null;
  role: string;
  value: string | null;
}

export interface RuntimeConfig {
  comparison: RuntimeComparison;
  equivalentExpressions: boolean;
  error?: string;
  fetchedAt: string | null;
  hasFailedInstances: boolean;
  instances: RuntimeInstance[];
  values: string[];
}
