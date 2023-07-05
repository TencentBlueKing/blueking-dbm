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

const ipv4Regex = '(?:25[0-5]|2[0-4]\\d|1\\d\\d|[1-9]\\d|\\d)(?:\\.(?:25[0-5]|2[0-4]\\d|1\\d\\d|[1-9]\\d|\\d)){3}';
const portRegex = '([1-9][0-9]{0,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])';

/**
 * 以小写英文字符开头，且只能包含英文字母、数字、连字符-
 */
export const nameRegx = /^[a-z][a-z0-9-]*$/;

/**
 * ipv4 正则
 */
export const ipv4 = new RegExp(`^${ipv4Regex}$`);

/**
 * ip:port 正则
 */
export const ipPort = new RegExp(`^${ipv4Regex}:${portRegex}$`);

/**
 * 正整数 正则
 */
export const integerRegx = /^[1-9]+$/;
