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
import type { AxiosResponse } from 'axios';
import dayjs from 'dayjs';

/**
 * 解析 Content-Disposition 里的文件名：优先 RFC 5987 的 filename*=UTF-8''xxx（中文文件名），其次 filename="xxx"
 */
const parseDispositionFileName = (contentDisposition?: string) => {
  if (!contentDisposition) {
    return '';
  }
  const encodedMatch = contentDisposition.match(/filename\*\s*=\s*(?:UTF-8|utf-8)''([^;]+)/);
  if (encodedMatch) {
    try {
      return decodeURIComponent(encodedMatch[1]!.trim());
    } catch {
      return encodedMatch[1]!.trim();
    }
  }
  const plainMatch = contentDisposition.match(/filename\s*=\s*("?)([^";]+)\1/);
  return plainMatch ? plainMatch[2]!.trim() : '';
};

export const downloadFile = (response: AxiosResponse, options: { keepFileName?: boolean } = {}): void => {
  const contentDisposition = response.headers['content-disposition'];
  let fileName = '';
  if (options.keepFileName) {
    // 文件名由后端决定（如已含日期），原样使用
    fileName = parseDispositionFileName(contentDisposition) || 'download';
  } else {
    const fileBasename = contentDisposition ? contentDisposition.split('=')[1] : 'download';
    const utcTimeStamp = dayjs().format('YYYYMMDDHHmmss');
    // 将时间戳插入到文件名和扩展名之间，如 partition_strategy_20260415120555.xlsx
    fileName = fileBasename.replace(/(\.[^.]+)$/, `_${utcTimeStamp}$1`);
  }
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', fileName);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};
