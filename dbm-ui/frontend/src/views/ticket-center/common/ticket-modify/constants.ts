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

/**
 * 改单与内容版本校验的后端错误码
 */
export const TICKET_MODIFY_ERROR_CODE = {
  // 单据已被审批，无法重新编辑
  APPROVED: 8704015,
  // 单据内容已被修改（内容版本不一致）
  CONTENT_CHANGED: 8704011,
  // 无权修改该单据
  NO_PERMISSION: 8704012,
  // 当前单据状态不支持改
  STATUS_UNSUPPORTED: 8704013,
} as const;

/**
 * catchError 请求被拒绝时的返回体
 */
export interface RequestErrorBody {
  code?: number;
  message?: string;
}

/**
 * 单据详情直达打开确认修改抽屉的 open 参数值
 */
export const OPEN_CONFIRM_MODIFY = 'confirm_modify';
