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

export enum STATUS {
  CREATED = '等待执行',
  READY = '等待执行',
  RUNNING = '执行中',
  SUSPENDED = '执行中',
  BLOCKED = '执行中',
  FINISHED = '执行成功',
  FAILED = '执行失败',
  REVOKED = '已终止'
}
export type STATUS_STRING = keyof typeof STATUS;
