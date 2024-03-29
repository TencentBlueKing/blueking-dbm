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

import SqlServerHaClusterModel from '@services/model/sqlserver/sqlserver-ha-cluster';
import SqlServerSingleClusterModel from '@services/model/sqlserver/sqlserver-single-cluster';

import type { ClusterTypes } from '@common/const';
import { ClusterTypes } from '@common/const';

import http from '../http';

const path = '/apis/dbbase';

/**
 * 查询集群名字是否重复
 */
export function verifyDuplicatedClusterName(params: { cluster_type: string; name: string; bk_biz_id: number }) {
  return http.get<boolean>(`${path}/verify_duplicated_cluster_name/`, params);
}

/**
 * 根据过滤条件查询集群详细信息
 */
export function filterClusters(params: { bk_biz_id: number; exact_domain: string }) {
  return http.get<any[]>(`${path}/filter_clusters/`, params).then((data: { cluster_type: string }[]) => {
    const ModelMap: Record<string, any> = {
      [ClusterTypes.SQLSERVER_SINGLE]: SqlServerSingleClusterModel,
      [ClusterTypes.SQLSERVER_HA]: SqlServerHaClusterModel,
    };
    return data.map((item) => new ModelMap[data[0].cluster_type](item));
  });
}

/*
 * 查询业务下集群的属性字段
 * 集群通用接口，用于查询/操作集群公共的属性
 */
export function queryBizClusterAttrs(params: {
  bk_biz_id: number;
  cluster_type: ClusterTypes;
  cluster_attrs?: string;
  instances_attrs?: string;
  limit?: number;
  offset?: number;
}) {
  return http.get<
    Record<
      string,
      {
        value: string;
        text: string;
      }[]
    >
  >(`${path}/query_biz_cluster_attrs/`, params);
}
