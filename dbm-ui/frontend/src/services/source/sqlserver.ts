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

import { useGlobalBizs } from '@stores';

import http from '../http';

const { currentBizId } = useGlobalBizs();

const path = `/apis/sqlserver/bizs/${currentBizId}`

/**
 * 判断库名是否在集群存在
 */
export function checkSqlserverDbExist(params: {
  cluster_id: number,
  db_list: string[]
}) {
  return http.post<Record<string, boolean>>(`${path}/cluster/check_sqlserver_db_exist/`, params);
}

/**
 * 通过库表匹配查询db
 */
export function getSqlserverDbs(params: {
  cluster_id: number,
  db_list: string[]
  ignore_db_list: string[]
}) {
  return http.post<string[]>(`${path}/cluster/get_sqlserver_dbs/`, params);
}


/**
 * 获取业务拓扑树
 */
export function geSqlserverResourceTree(params: { cluster_type: string }) {
  return http.get<BizConfTopoTreeModel[]>(`${path}/resource_tree/`, params);
}

