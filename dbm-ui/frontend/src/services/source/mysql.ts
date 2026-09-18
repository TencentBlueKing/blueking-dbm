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

import BizConfTopoTreeModel from '@services/model/config/biz-conf-topo-tree';

import type { ClusterTypes } from '@common/const';

import http from '../http';

/**
 * 获取业务拓扑树
 */
export function getMysqlResourceTree(params: { cluster_type: ClusterTypes }) {
  return http.get<BizConfTopoTreeModel[]>(`/apis/mysql/bizs/${window.PROJECT_CONFIG.BIZ_ID}/resource_tree/`, params);
}

/**
 * 批量查询集群默认存储引擎
 */
export function getDefaultStorageEngines(params: { cluster_ids: number[] }) {
  return http.post<
    {
      cluster_id: number;
      default_storage_engine: string;
    }[]
  >(`/apis/mysql/bizs/${window.PROJECT_CONFIG.BIZ_ID}/resources/default_storage_engines/`, params);
}
