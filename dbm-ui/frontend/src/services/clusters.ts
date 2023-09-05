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

import http from './http';
import type {
  ClusterPassword,
  ClusterPasswordParams,
  GetClusterHostNodesRequestParam,
  GetResourcesParams,
  InstanceDetails,
  InstanceDetailsParams,
  InstanceInfos,
  MySQLClusterInfos,
  ResourceInstance,
  ResourceItem, ResourceParams,
  ResourcesResult,
  ResourceTopo,
  ResourceTopoParams,
  TableFieldsItem,
  TableFieldsParams,
} from './types/clusters';
import type { HostNode, ListBase } from './types/common';

/**
 * 查询表格信息
 */
export const getTableFields = (params: TableFieldsParams): Promise<TableFieldsItem[]> => http.get(`/apis/mysql/bizs/${params.bk_biz_id}/${params.type}_resources/get_table_fields/`);

/**
 * 查询资源列表
 */
export const getResources = <T>(dbType: string, params: GetResourcesParams): Promise<ResourcesResult<T>> => http.get(`/apis/${dbType}/bizs/${params.bk_biz_id}/${params.type}_resources/`, params);

/**
 * 获取集群详情
 */
export const getResourceDetails = <T>(dbType: string, params: ResourceParams): Promise<T> => http.get(`/apis/${dbType}/bizs/${params.bk_biz_id}/${params.type}_resources/${params.id}/`);

/**
 * 获取集群实例列表
 */
export const getResourceInstances = (params: { db_type: string, type?: string, bk_biz_id: number } & Record<string, any>): Promise<ListBase<ResourceInstance[]>> => http.get(`/apis/${params.db_type}/bizs/${params.bk_biz_id}/${params.type}_resources/list_instances/`, params);

/**
 * 获取集群实例详情
 */
export const getResourceInstanceDetails = (params: InstanceDetailsParams, dbType: string): Promise<InstanceDetails> => http.get(`/apis/${dbType}/bizs/${params.bk_biz_id}/${params.type}_resources/retrieve_instance/`, params);

/**
 * 获取集群拓扑
 */
export const getResourceTopo = (params: ResourceTopoParams, dbType: string) => http.get<ResourceTopo>(`/apis/${dbType}/bizs/${params.bk_biz_id}/${params.type}_resources/${params.resource_id}/get_topo_graph/`);

/**
 * 获取大数据集群拓扑
 */
export const getBigdataResourceTopo = (params: ResourceTopoParams) => http.get<ResourceTopo>(`/apis/bigdata/bizs/${params.bk_biz_id}/${params.type}/${params.type}_resources/${params.resource_id}/get_topo_graph/`);

/**
 * 查询集群主机列表
 */
export const getClusterHostNodes = (params: GetClusterHostNodesRequestParam): Promise<HostNode[]> => http.get(`/apis/${params.db_type}/bizs/${params.bk_biz_id}/${params.db_type}_resources/${params.cluster_id}/get_nodes/`, params);

/**
 * 获取集群密码
 */
export const getClusterPassword = (params: ClusterPasswordParams): Promise<ClusterPassword> => http.get(`/apis/${params.db_type}/bizs/${params.bk_biz_id}/${params.type}_resources/${params.cluster_id}/get_password/`);

/**
 * 判断实例是否存在
 */
export const checkInstances = (
  bizId: number,
  params: Record<'instance_addresses', Array<string>>,
): Promise<Array<InstanceInfos>> => http.post(`/apis/mysql/bizs/${bizId}/instance/check_instances/`, params);


/**
 * 通过集群域名获取集群详情
 */
export const getClusterInfoByDomains = (
  bizId: number,
  params: Record<'cluster_filters', Array<{ immute_domain: string }>>,
) => http.post<ResourceItem[]>(`/apis/mysql/bizs/${bizId}/cluster/query_clusters/`, params);

/**
 * 通过集群查询同机关联集群
 */
export const findRelatedClustersByClusterIds = (
  bizId: number,
  params: Record<'cluster_ids', Array<number>>,
): Promise<Array<{
  cluster_id: number,
  cluster_info: MySQLClusterInfos,
  related_clusters: Array<MySQLClusterInfos>
}>> => http.post(`/apis/mysql/bizs/${bizId}/cluster/find_related_clusters_by_cluster_ids/`, params);


/**
 * 查询所有数据库的版本列表
 */
export const getClusterTypeToVersions = () => http.get<Record<string, string[]>>('/apis/version/cluster_type_to_versions/');
