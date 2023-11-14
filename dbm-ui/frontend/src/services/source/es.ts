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

import EsModel from '@services/model/es/es';
import EsInstanceModel from '@services/model/es/es-instance';

import { useGlobalBizs } from '@stores';

import http from '../http';
import type { ListBase } from '../types/common';

const { currentBizId } = useGlobalBizs();

const path = `/apis/bigdata/bizs/${currentBizId}/es/es_resources`;

/**
 * 获取集群列表
 */
export const getList = (params: Record<string, any> & { bk_biz_id: number }) => http.get<ListBase<EsModel[]>>(`${path}/`, params)
  .then(data => ({
    ...data,
    results: data.results.map((item: EsModel) => new EsModel(item)),
  }));

/**
 * 获取查询返回字段
 */
export const getTableFields = () => http.get<ListBase<EsModel[]>>(`${path}/get_table_fields/`);

/**
 * 获取实例列表
 */
export const getListInstance = (params: Record<string, any> & { bk_biz_id: number }) => http.get<ListBase<EsInstanceModel[]>>(`${path}/list_instances/`, params)
  .then(data => ({
    ...data,
    results: data.results.map((item: EsInstanceModel) => new EsInstanceModel(item)),
  }));

/**
 * 获取实例详情
 */
export const getRetrieveInstance = (params: { bk_biz_id: number }) => http.get<ListBase<EsModel[]>>(`${path}/retrieve_instance/`, params);

/**
 * 获取集群详情
 */
export const getClusterDetail = (params: { id: number }) => http.get<EsModel>(`${path}/${params.id}/`).then(data => new EsModel(data));

/**
 * 获取集群节点
 */
export const getNodes = (params: {
  bk_biz_id: number,
  cluster_id: number
}) => http.get<ListBase<EsModel[]>>(`${path}/${params.cluster_id}/get_nodes/`);

/**
 * 获取集群拓扑
 */
export const getTopoGraph = (params: {
  bk_biz_id: number,
  cluster_id: number
}) => http.get<ListBase<EsModel[]>>(`${path}/${params.cluster_id}/get_topo_graph/`);

