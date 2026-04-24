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

/** 上传状态 */
export enum UploadStatus {
  FAIL = 'fail',
  NEW = 'new',
  SUCCESS = 'success',
  UPLOADING = 'uploading',
}

/** 上传文件类型 */
export interface UploadFile {
  /** 文件名 */
  name: string;
  /** 上传进度百分比 0-100 */
  percentage?: number;
  /** 原始文件对象 */
  raw: UploadRawFile;
  /** 服务端响应 */
  response?: unknown;
  /** 文件大小（字节） */
  size: number;
  /** 上传状态 */
  status: UploadStatus;
  /** 状态文本 */
  statusText?: string;
  /** 唯一标识 */
  uid: number;
  /** 文件 URL */
  url?: string;
}

/** 扩展了 uid 的 File 对象 */
export interface UploadRawFile extends File {
  uid: number;
}

/** 大小限制配置 */
export interface MaxSize {
  /** 普通文件最大大小（MB） */
  maxFileSize: number;
  /** 图片文件最大大小（MB） */
  maxImgSize: number;
}

/** 上传请求选项 */
export interface UploadRequestOptions {
  /** 上传地址 */
  action: string;
  /** 额外 FormData 数据 */
  data?: Record<string, string | Blob>;
  /** 文件对象 */
  file: File;
  /** 文件字段名 */
  filename: string;
  /** 请求头 */
  headers?: Record<string, string>;
  /** HTTP 方法 */
  method: string;
  /** 错误回调 */
  onError: (error: Error) => void;
  /** 进度回调 */
  onProgress: (event: ProgressEvent) => void;
  /** 成功回调 */
  onSuccess: (res: unknown) => void;
  /** 是否携带凭证 */
  withCredentials: boolean;
}

/** 自定义上传处理函数 */
export type UploadRequestHandler = (options: UploadRequestOptions) => XMLHttpRequest | void;

/** beforeUpload 钩子 */
export type BeforeUploadHook = (file: UploadRawFile, uploadFiles: UploadFile[]) => boolean | Promise<boolean>;

/** beforeRemove 钩子 */
export type BeforeRemoveHook = (file: UploadFile, uploadFiles: UploadFile[]) => boolean | Promise<boolean>;
