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
  /** 错误原因（失败态） */
  errMsg?: string;
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

/** 重名检查函数：返回 true 表示重名，或返回被忽略的文件名数组 */
export type DuplicateChecker = (file: File, fileList: UploadFile[]) => boolean | string[];

/** 文件列表相对触发区的位置 */
export type ListPosition = 'bottom' | 'top';

/** 上传模式 */
export type UploadMode = 'bkrepo' | 'custom';

/** 上传组件静态配置项 */
export interface DbUploadOptions {
  /** 接受的文件类型 */
  accept?: string;
  /** bkrepo 模式：上传目录前缀（如 /mysql/pkg/1.0），组件自动拼接 /<file.name> */
  basePath?: string;
  /** 是否禁用 */
  disabled?: boolean;
  /** 是否启用拖拽上传模式 */
  draggable?: boolean;
  /** 文件列表中的文件图标类型 */
  fileIcon?: string;
  /** 最大文件数量限制 */
  limit?: number;
  /** 文件列表相对触发区的位置，默认 bottom */
  listPosition?: ListPosition;
  /** 上传模式：bkrepo / custom，默认 custom */
  mode?: UploadMode;
  /** 是否支持多选 */
  multiple?: boolean;
  /** 是否展示文件列表，默认 true */
  showFileList?: boolean;
  /** 文件大小限制（MB），可传数字或对象 */
  size?: number | MaxSize;
  /** 提示文本 */
  tip?: string;
}
