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
 * 操作类型
 */
export const dbOperations = {
  dml: ['select', 'insert', 'update', 'delete'],
  ddl: ['create', 'alter', 'drop', 'index', 'execute'],
  glob: ['replication client', 'replication slave', 'file'],
};

/**
 * 密码策略
 */
export enum PASSWORD_POLICY {
  lowercase = '包含小写字母',
  uppercase = '包含大写字母',
  numbers = '包含数字',
  symbols = '包含特殊字符_除空格外',
  follow_keyboards = '键盘序',
  follow_letters = '字母序',
  follow_numbers = '数字序',
  follow_symbols = '特殊符号序',
}
export type PasswordPolicyKeys = keyof typeof PASSWORD_POLICY;
