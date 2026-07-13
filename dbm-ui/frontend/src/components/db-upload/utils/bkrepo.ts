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

import Cookies from 'js-cookie';

import { createBkrepoAccessToken } from '@services/source/storage';

/** 解析 XMLHttpRequest 响应：优先 JSON.parse，失败回退原始文本 */
const parseXhrResponse = (xhr: XMLHttpRequest): XMLHttpRequestResponseType => {
  const res = xhr.responseText || xhr.response;
  if (!res) return res;
  try {
    return JSON.parse(res);
  } catch {
    return res;
  }
};

/** bkrepo 直传默认请求头 */
export const BKREPO_DEFAULT_HEADERS: Record<string, string> = {
  'Content-Type': 'application/octet-stream',
  'X-BKREPO-OVERWRITE': 'true',
  'X-CSRFToken': Cookies.get('dbm_csrftoken') || '',
};

/**
 * 获取 bkrepo 临时凭证并拼装上传地址
 * @param filePath bkrepo 中的目标路径，如 `/mysql/mysql-proxy/1.0/file.tar.gz`
 * @returns 完整的上传 URL（含 token 查询参数）
 */
export const createBkrepoUploadUrl = async (filePath: string): Promise<string> => {
  const tokenResult = await createBkrepoAccessToken({ file_path: filePath });
  // const uploadDomain = import.meta.env.MODE === 'production' ? tokenResult.url : '/bkrepo_upload';
  return `${tokenResult.url}/generic/temporary/upload/${tokenResult.project}/${tokenResult.repo}${tokenResult.path}?token=${tokenResult.token}`;
};

/** XMLHttpRequest 上传请求的配置项 */
export interface XhrUploadOptions {
  /** 请求头 */
  headers?: Record<string, string>;
  /** HTTP 方法，默认 PUT */
  method?: string;
  /** 错误回调 */
  onError: (error: Error) => void;
  /** 进度回调 */
  onProgress: (event: ProgressEvent) => void;
  /** 成功回调，参数为解析后的响应体 */
  onSuccess: (res: XMLHttpRequestResponseType) => void;
  /** 待上传的文件 */
  rawFile: File;
  /** 目标 URL */
  url: string;
}

/**
 * 通用 XMLHttpRequest 上传请求（PUT 直传，适配 bkrepo 等场景）
 * @returns XMLHttpRequest 实例，可用于中断
 */
export const createXhrUpload = (options: XhrUploadOptions): XMLHttpRequest => {
  if (typeof XMLHttpRequest === 'undefined') {
    throw new Error('XMLHttpRequest is undefined');
  }

  const xhr = new XMLHttpRequest();
  const { headers = {}, method = 'PUT', onError, onProgress, onSuccess, rawFile, url } = options;

  if (xhr.upload) {
    xhr.upload.addEventListener('progress', (event) => {
      onProgress(event);
    });
  }

  xhr.addEventListener('error', () => {
    onError(new Error('An error occurred during upload'));
  });

  xhr.addEventListener('load', () => {
    if (xhr.status < 200 || xhr.status >= 300) {
      return onError(new Error('An error occurred during upload'));
    }
    onSuccess(parseXhrResponse(xhr));
  });

  xhr.open(method, url, true);

  Object.entries(headers).forEach(([key, value]) => {
    xhr.setRequestHeader(key, value);
  });

  xhr.send(rawFile);
  return xhr;
};
