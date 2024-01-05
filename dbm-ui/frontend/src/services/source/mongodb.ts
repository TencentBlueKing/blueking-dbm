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
import MongoModel from '@services/model/mongo/mongo';
import MongoDetailModel from '@services/model/mongo/mongo-detail';

import { useGlobalBizs } from '@stores';

import http from '../http';
import type { ListBase } from '../types';

const { currentBizId } = useGlobalBizs();

const path = `/apis/mongodb/bizs/${currentBizId}/mongodb_resources`;

/**
 * 获取Mongo集群
 */
export function getMongoList(params: {
  id?: number,
  name?: string,
  ip?: string,
  domain?: string,
  creator?: string,
  cluster_type?: string,
  version?: string,
  region?: string,
  db_module_id?: number,
  cluster_ids?: number,
  limit?: number,
  offset?: number,
}) {
  return http.get<ListBase<MongoModel[]>>(`${path}/`, params).then(data => ({
    ...data,
    results: data.results.map(item => new MongoModel(item)),
  }));
}

/**
 * 查询Mongo集群详情
 */
export function getMongoClusterDetails(params: {
  cluster_id: number
}) {
  return http.get<MongoDetailModel>(`${path}/${params.cluster_id}/`);
}

/**
 * 查询Mongo拓扑图
 */
export function getMongoClustersTopoGraph(params: {
  cluster_id: number
}) {
  return http.get(`${path}/${params.cluster_id}/get_topo_graph/`);
}

/**
 * 获取Mongo集群 table 信息
 */
export function getMongoTableFields(params: {
  limit?: number,
  offset?: number,
}) {
  return http.get(`${path}/get_table_fields/`, params);
}

/**
 * 查询Mongo集群实例列表
 */
export function getMongoInstancesList(params: {
  cluster_id?: number,
  ip?: string,
  cluster_type?: string,
  domain?: string,
  instance_address?: string,
  port?: string,
  status?: string,
  role?: string,
  limit?: number,
  offset?: number,
}) {
  return http.get(`${path}/list_instances/`, params);
}

/**
 * 查询Mongo集群实例详情
 */
export function getMongoInstanceDetails(params: {
  instance_address: string,
  cluster_id?: number,
  ip?: string,
  port?: string,
  limit?: number,
  offset?: number,
}) {
  return http.get(`${path}/retrieve_instance/`, params);
}
