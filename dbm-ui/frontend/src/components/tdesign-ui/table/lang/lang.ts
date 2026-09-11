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
export const lang = {
  中: 'Medium',
  偏大: 'Large',
  全选: 'Select All',
  取消: 'Cancel',
  外观设置: 'Appearance Settings',
  大: 'Large',
  字体大小: 'Font Size',
  字段设置: 'Field Settings',
  小: 'Small',
  标准: 'Standard',
  确定: 'Confirm',
  表格行高: 'Row Height',
  输入关键词: 'Enter keyword',
  迷你: 'Mini',
} as const;

/** 获取 cookie */
export const getCookie = (name: string) => {
  const reg = new RegExp(`(^| )${name}=([^;]*)(;|$)`);
  const arr = document.cookie.match(reg);
  if (arr) return unescape(arr[2]);
  return null;
};

const language = getCookie('blueking_language') || 'zhCN';

export const t = (key: keyof typeof lang) => {
  if (language === 'en') {
    return lang[key] || key;
  }
  return key;
};
