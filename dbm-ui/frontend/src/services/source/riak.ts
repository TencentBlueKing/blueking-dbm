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

import RiakModel from '@services/model/riak/riak';
import RiakNodeModel from '@services/model/riak/riak-node';

import { useGlobalBizs } from '@stores';

import http from '../http';
import type {
  ListBase,
  ResourceInstance,
  ResourceTopo,
} from '../types';

const { currentBizId } = useGlobalBizs();

const path = `/apis/bigdata/bizs/${currentBizId}/riak/riak_resources`;

/**
 * 查询资源列表
 */
export function getRiakList(params: {
  bk_biz_id: number,
  limit: number,
  offset: number,
  type: string,
  cluster_ids?: number[] | number,
 }) {
  return http.get<ListBase<RiakModel[]>>(`${path}/`, params)
    .then(res => ({
      ...res,
      results: res.results.map(item => new RiakModel(item)),
    }));
}

/**
 * 获取集群实例列表
 */
export function getRiakInstanceList(params: {
  offset?: number
  limit?: number
  bk_biz_id: number
  cluster_id: number
  role: string
}) {
  return http.get<ListBase<ResourceInstance[]>>(`${path}/list_instances/`, params);
}

/**
 * 集群实例详情
 */
interface InstanceDetails {
  bk_cloud_id: number,
  bk_cpu: number,
  bk_disk: number,
  bk_host_id: number,
  bk_host_innerip: string,
  bk_mem: number,
  bk_os_name: string,
  cluster_id: number,
  cluster_type: string,
  create_at: string,
  idc_city_id: string,
  idc_city_name: string,
  idc_id: number,
  instance_address: string,
  master_domain: string,
  net_device_id: string,
  rack: string,
  rack_id: number,
  role: string,
  slave_domain: string,
  status: string,
  sub_zone: string,
  db_module_id: number,
  cluster_type_display: string,
  bk_idc_name: string,
  bk_cloud_name: string,
  db_version: string,
  version?: string
}

/**
 * 获取集群实例详情
 */
export function retrieveRiakInstance(params: {
  bk_biz_id: number,
  type: string,
  instance_address: string,
  cluster_id?: number
}) {
  return http.get<InstanceDetails>(`${path}/retrieve_instance/`, params);
}

/**
 * 获取集群详情
 */
export function getRiakDetail(params: { id: number }) {
  return http.get<RiakModel>(`${path}/${params.id}/`)
    .then(res => new RiakModel(res));
}

/**
 * 获取集群拓扑
 */
export function getRiakTopoGraph(params: { cluster_id: number }) {
  return http.get<ResourceTopo>(`${path}/${params.cluster_id}/get_topo_graph/`);
}

/**
 * 获取 Riak 集群节点列表信息
 */
export function getRiakNodeList(params: Record<string, any> & {
  bk_biz_id: number,
  cluster_id: number
}) {
  return http.get<ListBase<Array<RiakNodeModel>>>(`${path}/${params.cluster_id}/list_nodes/`, params).then(data => ({
    ...data,
    results: data.results.map((item: RiakNodeModel) => new RiakNodeModel(item)),
  }));
}

/**
 * 导出集群数据为 excel 文件
 */
export function exportRiakClusterToExcel(params: { cluster_ids?: number[] }) {
  return http.post<string>(`${path}/export_cluster/`, params, { responseType: 'blob' });
}

/**
 * 导出实例数据为 excel 文件
 */
export function exportRiakInstanceToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${path}/export_instance/`, params, { responseType: 'blob' });
}
