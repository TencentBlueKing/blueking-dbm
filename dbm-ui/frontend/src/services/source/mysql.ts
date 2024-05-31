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
import TendbhaModel from '@services/model/mysql/tendbha';

import { useGlobalBizs } from '@stores';

import http from '../http';
import type { ListBase } from '../types';

const { currentBizId } = useGlobalBizs();

/**
 * 获取业务拓扑树
 */
export function getMysqlResourceTree(params: { cluster_type: string }) {
  return http.get<BizConfTopoTreeModel[]>(`/apis/mysql/bizs/${currentBizId}/resource_tree/`, params);
}

/**
 * 根据业务id、模块id、及筛选条件获取集群列表
 */
export function getClusterList(params: {
  bk_biz_id?: number;
  db_module_id?: number;
  limit?: number;
  offset?: number;
  type?: string;
  dbType?: string;
  cluster_ids?: number[] | number;
  domain?: string;
}) {
  return http.post<ListBase<TendbhaModel[]>>(`/apis/mysql/query_clusters/`, params);
}

/**
 * 根据用户手动输入的域名列表查询
 */
export function checkDomains(params: { domains: Array<string> }) {
  return http.post<Array<TendbhaModel>>(`/apis/mysql/check_domains/`, params);
}
