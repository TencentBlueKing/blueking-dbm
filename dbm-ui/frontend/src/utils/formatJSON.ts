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
 * 格式化json字符串，补充缩进
 * @param {String} str 数据源
 */
export function formatJSON(str: string): string {
  try {
    const obj = JSON.parse(str);
    return JSON.stringify(obj, null, 2); // 2 空格缩进
  } catch {
    return str; // 解析失败则返回原字符串
  }
}

/**
 * 格式化json字符串，补充缩进
 * @param {String} obj 数据源
 */
export function objectToJSON(obj: Record<string, any>): string {
  try {
    return JSON.stringify(obj, null, 2);
  } catch (error) {
    console.error('对象转 JSON 字符串失败:', error);
    return '{}'; // 返回空对象作为降级方案
  }
}
