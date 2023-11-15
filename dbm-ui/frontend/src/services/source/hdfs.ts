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

import HdfsModel from '@services/model/hdfs/hdfs';
import ClusterConfigXmlsModel from '@services/model/hdfs/hdfs-cluster-config-xmls';
import HdfsInstanceModel from '@services/model/hdfs/hdfs-instance';

import { useGlobalBizs } from '@stores';

import http from '../http';
import type { ListBase } from '../types/common';

const { currentBizId } = useGlobalBizs();

const path = `/apis/bigdata/bizs/${currentBizId}/hdfs/hdfs_resources`;

/**
 * 获取集群列表
 */
export const getList = (params: Record<string, any> & { bk_biz_id: number }) => http.get<ListBase<HdfsModel[]>>(`${path}/`, params)
  .then(data => ({
    ...data,
    results: data.results.map((item: HdfsModel) => new HdfsModel(item)),
  }));

/**
 * 获取查询返回字段
 */
export const getTableFields = () => http.get<ListBase<HdfsModel[]>>(`${path}/get_table_fields/`);

/**
 * 获取实例列表
 */
export const getListInstance = (params: Record<string, any> & { bk_biz_id: number }) => http.get<ListBase<HdfsInstanceModel[]>>(`${path}/list_instances/`, params)
  .then(data => ({
    ...data,
    results: data.results.map((item: HdfsInstanceModel) => new HdfsInstanceModel(item)),
  }));

/**
 * 获取实例详情
 */
export const getRetrieveInstance = (params: { bk_biz_id: number }) => http.get<ListBase<HdfsModel[]>>(`${path}/retrieve_instance/`, params);

/**
 * 获取集群详情
 */
export const getClusterDetail = (params: { id: number }) => http.get<HdfsModel>(`${path}/${params.id}/`).then(data => new HdfsModel(data));

/**
 * 获取集群拓扑
 */
export const getTopoGraph = (params: {
  bk_biz_id: number,
  cluster_id: number
}) => http.get<ListBase<HdfsModel[]>>(`${path}/${params.cluster_id}/get_topo_graph/`);

/**
 * 获取集群访问xml配置
 */
export const getClusterXmls = (params: {
  bk_biz_id: number,
  cluster_id: number
}) => http.get<ClusterConfigXmlsModel>(`${path}/${params.cluster_id}/get_xmls/`);
