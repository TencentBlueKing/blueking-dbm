/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and limitations under the License.
 */

import type { MaxSize } from '../types';

// re-export excel utils
export type { ParseExcelOptions } from './excel';
export { isExcelAccept, parseExcelFile } from './excel';

// re-export bkrepo utils
export type { XhrUploadOptions } from './bkrepo';
export { BKREPO_DEFAULT_HEADERS, createBkrepoUploadUrl, createXhrUpload } from './bkrepo';

/** 格式化文件大小为带单位的可读字符串 */
export const formatFileSize = (size: number): string => {
  if (size === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const k = 1024;
  const i = Math.floor(Math.log(size) / Math.log(k));
  return `${parseFloat((size / k ** i).toFixed(2))} ${units[i]}`;
};

/** 根据文件类型与 size 配置获取最大文件大小限制（MB），无限制返回 undefined */
export const getMaxSize = (file: File, size?: number | MaxSize): number | undefined => {
  if (size === undefined) return undefined;
  if (typeof size === 'number') return size;
  return file.type.startsWith('image/') ? size.maxImgSize : size.maxFileSize;
};

/** 校验文件格式是否符合 accept 配置 */
export const validateAccept = (file: File, accept?: string): boolean => {
  if (!accept) return true;
  const extensions = accept
    .split(',')
    .map((ext) => ext.trim().toLowerCase())
    .filter(Boolean);
  if (extensions.length === 0) return true;

  const fileName = file.name.toLowerCase();
  const hasExtMatch = extensions.some((ext) => fileName.endsWith(ext));

  // 同时检查 MIME 类型
  const hasMimeMatch = extensions.some((ext) => {
    if (!ext.includes('/')) return false;
    return file.type === ext;
  });

  return hasExtMatch || hasMimeMatch;
};

/** 校验文件大小是否在限制内 */
export const validateSize = (file: File, size?: number | MaxSize): boolean => {
  const maxSize = getMaxSize(file, size);
  if (maxSize === undefined) return true;
  return file.size / 1024 / 1024 <= maxSize;
};

/** 解析 XMLHttpRequest 响应：优先 JSON.parse，失败回退原始文本 */
export const parseXhrResponse = (xhr: XMLHttpRequest): XMLHttpRequestResponseType => {
  const res = xhr.responseText || xhr.response;
  if (!res) return res;
  try {
    return JSON.parse(res);
  } catch {
    return res;
  }
};
