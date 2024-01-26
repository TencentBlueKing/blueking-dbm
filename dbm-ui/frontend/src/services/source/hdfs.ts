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
import HdfsNodeModel from '@services/model/hdfs/hdfs-node';
import HdfsPasswordModel from '@services/model/hdfs/hdfs-password';

import { useGlobalBizs } from '@stores';

import http from '../http';
import type { ListBase } from '../types';

const { currentBizId } = useGlobalBizs();

const path = `/apis/bigdata/bizs/${currentBizId}/hdfs/hdfs_resources`;

/**
 * 获取集群列表
 */
export function getHdfsList(params: Record<string, any> & { bk_biz_id: number }) {
  return http.get<ListBase<HdfsModel[]>>(`${path}/`, params)
    .then(data => ({
      ...data,
      results: data.results.map((item: HdfsModel) => new HdfsModel(Object.assign(item, {
        permission: Object.assign({}, item.permission, data.permission),
      }))),
    }));
}

/**
 * 获取查询返回字段
 */
export function getHdfsTableFields() {
  return http.get<ListBase<HdfsModel[]>>(`${path}/get_table_fields/`);
}

/**
 * 获取实例列表
 */
export function getHdfsInstanceList(params: Record<string, any> & { bk_biz_id: number }) {
  return http.get<ListBase<HdfsInstanceModel[]>>(`${path}/list_instances/`, params)
    .then(data => ({
      ...data,
      results: data.results.map((item: HdfsInstanceModel) => new HdfsInstanceModel(item)),
    }));
}

/**
 * 获取实例详情
 */
export function retrieveHdfsInstance(params: { bk_biz_id: number }) {
  return http.get<ListBase<HdfsModel[]>>(`${path}/retrieve_instance/`, params);
}
/**
 * 获取集群详情
 */
export function getHdfsDetail(params: { id: number }) {
  return http.get<HdfsModel>(`${path}/${params.id}/`)
    .then(data => new HdfsModel(data));
}

/**
 * 获取集群拓扑
 */
export function getHdfsTopoGraph(params: { cluster_id: number }) {
  return http.get<ListBase<HdfsModel[]>>(`${path}/${params.cluster_id}/get_topo_graph/`);
}

/**
 * 获取集群访问xml配置
 */
export function getHdfsXmls(params: { cluster_id: number }) {
  return http.get<ClusterConfigXmlsModel>(`${path}/${params.cluster_id}/get_xmls/`);
}

/**
 * 获取 Hdfs 集群访问密码
 */
export function getHdfsPassword(params: { cluster_id: number }) {
  return http.get<HdfsPasswordModel>(`${path}/${params.cluster_id}/get_password/`)
    .then(data => new HdfsPasswordModel(data));
}

/**
 * 获取 Hdfs 集群节点列表信息
 */
export function getHdfsNodeList(params: Record<string, any> & {
  bk_biz_id: number,
  cluster_id: number
}) {
  return http.get<ListBase<Array<HdfsNodeModel>>>(`${path}/${params.cluster_id}/list_nodes/`, params)
    .then(data => ({
      ...data,
      results: data.results.map((item: HdfsNodeModel) => new HdfsNodeModel(item)),
    }));
}

/**
 * 导出集群数据为 excel 文件
 */
export function exportHdfsClusterToExcel(params: { cluster_ids?: number[] }) {
  return http.post<string>(`${path}/export_cluster/`, params, { responseType: 'blob' });
}

/**
 * 导出实例数据为 excel 文件
 */
export function exportHdfsInstanceToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${path}/export_instance/`, params, { responseType: 'blob' });
}

