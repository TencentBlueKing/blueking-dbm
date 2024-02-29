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

import http from '../http';

const path = '/apis/core/storage';

/**
 * 批量获取文件内容
 */
export function batchFetchFile(params: { file_path_list: string[] }) {
  return http.post<
    Array<{
      content: string;
      path: string;
      url: string;
    }>
  >(`${path}/batch_fetch_file_content/`, params);
}

/**
 * 获取文件内容
 */
export function getFileContent(params: { file_path: string }) {
  return http.get<{
    content: string;
    path: string;
    url: string;
  }>(`${path}/fetch_file_content/`, params);
}
