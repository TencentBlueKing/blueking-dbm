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

import type { IPagination } from '@hooks';

/**
 * 版本文件类型
 */
export type VersionFileType = {
  label: string;
  name: string;
  children?: VersionFileType[];
};

/**
 * 列表基础 state
 */
export interface IState {
  active: string;
  isAnomalies: boolean;
  isLoading: boolean;
  pagination: IPagination;
  data: {
    allow_biz_ids: number[];
    create_at: string;
    creator: string;
    enable: boolean;
    id: number;
    md5: string;
    mode: string;
    name: string;
    path: string;
    pkg_type: string;
    priority: number;
    size: number;
    update_at: string;
    updater: string;
    version: string;
  }[];
  search: string;
}

/**
 * 类型参数
 */
export type TypeParams = {
  db_type: string;
  pkg_type: string;
};
